#!/usr/bin/env python3
"""mGBA checks, including explicitly labelled RAM-only scene fixtures."""
from pathlib import Path
import ctypes as C, json,hashlib,struct,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_checks';OUT.mkdir(exist_ok=True)
core=C.CDLL(str(ROOT/'build/runtime_bridge.dylib'))
core.anguna_open.argtypes=[C.c_char_p];core.anguna_open.restype=C.c_int
core.anguna_pixels.restype=C.c_void_p
core.anguna_call.argtypes=[C.c_uint]*4;core.anguna_call.restype=C.c_int
core.anguna_read.argtypes=[C.c_uint,C.c_uint];core.anguna_read.restype=C.c_uint
core.anguna_write.argtypes=[C.c_uint]*3
rom=ROOT/'output/anguna_zh.gba'
assert core.anguna_open(str(rom).encode())
read=lambda a,n=4:core.anguna_read(a,n)
write=lambda a,v,n=4:core.anguna_write(a,v,n)
def run(n,keys=0):core.anguna_frame(keys,n)
def press(key,delay=90):run(1,key);run(delay)
def shot(name):
    im=Image.frombytes('RGB',(240,160),C.string_at(core.anguna_pixels(),240*160*2),'raw','BGR;16',0)
    im.save(OUT/(name+'.png'));im.resize((720,480),Image.Resampling.NEAREST).save(OUT/(name+'_3x.png'))
def call(addr,r0=0,r1=0,r2=0):
    count=core.anguna_call(addr,r0,r1,r2)
    assert count>=0,(hex(addr),hex(core.anguna_pc()))
    return count
run(1100);shot('title');press(16);shot('title_continue');press(32);press(1);shot('intro1')
press(1);shot('intro2');press(1);shot('intro3');press(1);shot('game')
press(8);shot('inventory');press(256);shot('map');press(256);shot('enemy_empty')
press(8);press(4);shot('save_blocked');press(2)
registers=[read(0x04000008+i*2,2) for i in range(4)]
print('BG registers',list(map(hex,registers)))
# All text / glyphs use the same ROM and engine as normal game playback.
# Clear the text map only in emulator RAM and render every translated record.
records=json.loads((ROOT/'translations/text_zh.json').read_text())
header=(ROOT/'build/zh_data.h').read_text()
expected=[list(map(int,m.split(','))) for m in re.findall(r'text_\d+\[\]=\{([^}]+)\}',header)]
glyphs=[list(map(lambda x:int(x,16),m.split(','))) for m in re.search(r'zh_glyphs\[\]\[8\]=\{(.*?)\};',header,re.S)[1].strip('{}').split('},{')]
bg=read(0x03001168);tiles=read(bg);textmap=read(bg+4)
maxinstructions=0
for rec,seq in zip(records,expected):
    if rec['category']=='ending' and int(rec['offset'],16)!=0x1abd48:continue
    if 0x1ac648<=int(rec['offset'],16)<=0x1ac7cc:continue # 12px page checked below
    for i in range(1024):write(textmap+i*2,0,2)
    count=call(0x0800085c,1,2,0x08000000+int(rec['offset'],16));maxinstructions=max(maxinstructions,count)
    for i,char in enumerate(seq):
        tile=read(textmap+(65+i)*2,2)&1023
        if char<256:assert tile==char,(rec,i,tile,char)
        else:assert [read(tiles+tile*32+k*4) for k in range(8)]==glyphs[char-256],(rec,i,tile,char)
for pi,address in enumerate([0x1ac78c,0x1ac700,0x1ac648]):
    expected_map=list(map(int,re.search(fr'story_map_{pi}\[\]=\{{([^}}]+)',header)[1].split(',')))
    call(0x0800085c,1,3,0x08000000+address)
    assert expected_map==[read(textmap+i*2,2) for i in range(1024)]
# Ending two-row maps and circular row 31 -> 0 clearing.
ending_records=[r for r in records if r['category']=='ending' and int(r['offset'],16)!=0x1abd48]
for i,rec in enumerate(ending_records):
    expected_map=list(map(int,re.search(fr'ending_map_{i}\[\]=\{{([^}}]+)',header)[1].split(',')))
    for y in (2,31):
        call(0x0800085c,2,y,0x08000000+int(rec['offset'],16))
        assert expected_map==[read(textmap+(((y+row)&31)*32+col)*2,2) for row in range(2) for col in range(32)]
import subprocess
nm=subprocess.check_output([str(ROOT.parent/'POWDER/toolchain/xpack-arm-none-eabi-gcc-15.2.1-1.1/bin/arm-none-eabi-nm'),str(ROOT/'build/patch.elf')],text=True)
clear_address=int(re.search(r'([0-9a-f]+) T zh_credit_clear',nm)[1],16)
call(clear_address,2,31,0)
assert all(read(textmap+(row*32+col)*2,2)==0xc000 for row in (31,0) for col in range(32))
# Cache safety with original portrait loads: writes never touch 320..463 or maps.
for i in range(144*8):write(tiles+320*32+i*4,0xa55aa55a)
sentinel=[read(tiles+320*32+i*4) for i in range(144*8)]
for i in range(1024):write(textmap+i*2,0,2)
for row,rec in enumerate(records[-10:]):call(0x0800085c,1,row,0x08000000+int(rec['offset'],16))
assert sentinel==[read(tiles+320*32+i*4) for i in range(144*8)]
# Hide other layers solely for the font proof sheet (not a gameplay screenshot).
write(0x04000000,0x100,2);write(0x04000050,0,2);run(2);shot('font_fixture')
report={'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'translated_records_checked':len(records),'opening_12px_pages_checked':3,'ending_12px_lines_checked':7,'credit_row_wrap_checked':True,'glyphs_checked':len(glyphs),'max_text_hook_instructions':maxinstructions,'portrait_vram_preserved':True,'bg_registers':list(map(hex,registers)),'checks':'title selection, opening, inventory, map, empty enemy list, blocked save; all text via RAM-only renderer fixtures','limits':'Does not represent a full playthrough or real hardware test.'}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2));core.anguna_close()
