#!/usr/bin/env python3
"""Late-scene tests using RAM-only mGBA function dispatch, not a playthrough."""
import ctypes as C,json,struct,hashlib,re
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/scene_checks';OUT.mkdir(exist_ok=True)
c=C.CDLL(str(ROOT/'build/runtime_bridge.dylib'));c.anguna_open.argtypes=[C.c_char_p];c.anguna_pixels.restype=C.c_void_p
c.anguna_read.argtypes=[C.c_uint,C.c_uint];c.anguna_read.restype=C.c_uint
c.anguna_call.argtypes=[C.c_uint]*4;c.anguna_call.restype=C.c_int
rom=ROOT/'output/anguna_zh.gba'
def run(n,k=0):c.anguna_frame(k,n)
def press(k,delay=90):run(1,k);run(delay)
def shot(name):
    im=Image.frombytes('RGB',(240,160),C.string_at(c.anguna_pixels(),76800),'raw','BGR;16',0)
    im.save(OUT/(name+'.png'));im.resize((720,480),Image.Resampling.NEAREST).save(OUT/(name+'_3x.png'))
def boot(which=rom):
    assert c.anguna_open(str(which).encode());run(1100)
    for _ in range(4):press(1)
def jump(addr,r0=0,r1=0,r2=0):c.anguna_jump(addr,r0,r1,r2)
def call(addr,r0=0,r1=0,r2=0):assert c.anguna_call(addr,r0,r1,r2)>=0,hex(addr)
def read(addr,size=4):return c.anguna_read(addr,size)
def write(addr,value,size=4):c.anguna_write(addr,value,size)
boot();jump(0x08001a24);run(450);shot('gameover');press(16);shot('gameover_other_choice');c.anguna_close()
for shop in range(4):
    boot();jump(0x080053ec,shop);run(100);shot(f'shop{shop}_intro');press(1);shot(f'shop{shop}_items')
    for i in range(3):press(128,30);shot(f'shop{shop}_item{i+1}')
    c.anguna_close()
boot();jump(0x080023c4);run(500);shot('ending');run(1000);shot('credits');run(2500);shot('completion');c.anguna_close()
# Legal database definitions are identified by their ROM text pointers. In the
# game these pointers are placed in the discovered-enemy list after a defeat.
boot();data=(ROOT/'original/Anguna-Warriors-of-Virtue.gba').read_bytes();definitions=[]
for off in range(0,len(data)-32,4):
    name=struct.unpack_from('<I',data,off+12)[0]
    desc=struct.unpack_from('<I',data,off+16)[0]
    if 0x081ac96c<=name<=0x081ad040 and 0x081ac96c<=desc<=0x081ad040:
        # First three fields are portrait ROM pointers.
        ptrs=struct.unpack_from('<3I',data,off)
        if all(0x0801a700<p<0x081abd00 for p in ptrs):definitions.append(0x08000000+off)
print('database definitions',len(definitions))
# EnemyType->db is the final pointer to one of these definitions. Inspect the
# actual stats renderer to derive its field offset before using its callers.
write(0x03003edc,0)
# showEnemyStatsFromDatabase at 0x0800387c loads [EnemyType + 40].
enemy_types=[]
for definition in definitions:
    refs=[m.start() for m in re.finditer(re.escape(struct.pack('<I',definition)),data) if m.start()%4==0]
    for ref in refs:
        candidate=0x08000000+ref-40
        if read(candidate+40)==definition:enemy_types.append(candidate);break
if enemy_types:
    for i,t in enumerate(enemy_types[:31]):write(0x03003ee4+i*4,t)
    write(0x03003ee0,min(len(enemy_types),31)-1)
    jump(0x08003fd4);run(100);shot('enemy_portrait')
    for i in range(min(len(enemy_types),31)-1):press(32,20);shot(f'enemy_{i+1:02}')
c.anguna_close()
boot();write(0x03001094,0);jump(0x08002cc8);run(100);shot('save_menu');press(1);shot('save_success')
c.anguna_close()
# Direct SRAM round-trip dispatch is inconclusive in this harness: the original
# ROM also times out in saveGame and returns 0 from loadGame. Do not claim pass.
report={'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'fixtures':['gameover with both choices','four shops intro and item selection','ending, rolling credits, collection rate','enemy database portraits','save menu'],'save_roundtrip':'not verified; direct-call harness also fails on original ROM','fixture_note':'Scene entrances and discovery list set only in emulator RAM. Shipped ROM and user saves are untouched.','database_definitions':len(definitions),'enemy_types':len(enemy_types)}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
