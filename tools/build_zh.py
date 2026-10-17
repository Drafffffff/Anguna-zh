#!/usr/bin/env python3
"""Reproducible, original-hash-guarded Anguna GBA Chinese ROM patch."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'ANGUNA'
BUILD=GAME/'build';BUILD.mkdir(exist_ok=True)
ORIGINAL=GAME/'original/Anguna-Warriors-of-Virtue.gba'
EXPECTED='1df5a07fef92a526768333d041eec42d4efabfba1ad50e347b8146954ed07ff5'
TOOLCHAIN=ROOT/'POWDER/toolchain/xpack-arm-none-eabi-gcc-15.2.1-1.1/bin'
FONT=GAME/'assets/fonts/fusion-pixel-8px-monospaced-zh_hans.bdf'

def font_bitmaps(path,size=8,baseline=7):
    result={}
    for block in path.read_text().split('STARTCHAR ')[1:]:
        l=block.splitlines();cp=int(next(x for x in l if x.startswith('ENCODING ')).split()[1])
        w,h,xo,yo=map(int,next(x for x in l if x.startswith('BBX ')).split()[1:])
        pos=l.index('BITMAP')+1;rows=[[0]*size for _ in range(size)]
        for y,row in enumerate(l[pos:pos+h]):
            bits=int(row,16)
            for x in range(w):
                xx=x+xo;yy=y+baseline-h-yo
                if bits&(1<<(len(row)*4-x-1)) and 0<=xx<size and 0<=yy<size:rows[yy][xx]=1
        result[chr(cp)]=rows
    return result

def ascii_tile(c):
    if 'A'<=c<='Z':return ord(c)-64
    if 'a'<=c<='z':return ord(c)-ord('a')+27
    if '0'<=c<='9':return ord(c)-ord('0')+53
    return {'!':63,'#':65,'$':66,'%':67,'&':68,'(':70,')':71,'*':72,'+':73,',':74,'-':75,'.':76,'/':77,':':78,';':79,'<':80,'=':81,'>':82,'?':83}.get(c,0)

def main():
    original=ORIGINAL.read_bytes();assert hashlib.sha256(original).hexdigest()==EXPECTED
    records=json.loads((GAME/'translations/text_zh.json').read_text())
    records.sort(key=lambda x:int(x['offset'],16))
    chars=sorted(set(''.join(r['zh'] for r in records))-set(chr(i) for i in range(128)))
    # Original CRT EWRAM range ends at 0x02002fd4; the cache is a separate
    # <1KiB block at 0x0203e000. This game avoids malloc/free.
    assert struct.unpack_from('<I',original,0x1cc)[0]==0x02002fd4
    assert 4+len(chars)*2<1024
    glyphs=font_bitmaps(FONT);assert not set(chars)-glyphs.keys(),set(chars)-glyphs.keys()
    charids={c:i+256 for i,c in enumerate(chars)}
    h=['typedef struct {u32 address; const u16 *text; u16 length,english_length,category;} Translation;']
    h.append('static const u8 ascii_tiles[128]={'+','.join(str(ascii_tile(chr(c))) for c in range(128))+'};')
    bitmaps=[]
    for c in chars:
        pixels=glyphs[c]
        # White 1px ink, 1px black shadow to the right/below, transparent paper.
        data=bytearray()
        for y in range(8):
            for x in range(0,8,2):
                vals=[]
                for xx in (x,x+1):
                    ink=pixels[y][xx]
                    shadow=(xx>0 and pixels[y][xx-1]) or (y>0 and pixels[y-1][xx])
                    vals.append(4 if ink else 15 if shadow else 0)
                data.append(vals[0]|vals[1]<<4)
        bitmaps.append('{'+','.join(hex(x) for x in struct.unpack('<8I',data))+'}')
    h.append('static const u32 zh_glyphs[][8]={'+','.join(bitmaps)+'};')
    h.append(f'#define ZH_GLYPH_COUNT {len(chars)}')
    # Story pages are typeset together at native 12px; repeated 8px line calls
    # are suppressed by the engine. Prebuilt 4bpp tiles avoid runtime raster work.
    story_pages=[
        ([0x1ac78c,0x1ac7ac,0x1ac7c0,0x1ac7cc],[(24,'真倒霉，你竟然被怪物抓住了。'),(64,'又一次。')]),
        ([0x1ac700,0x1ac71c,0x1ac734,0x1ac74c,0x1ac758,0x1ac774],[(24,'你原本肩负使命，'),(40,'去寻找并击败怪物的首领——'),(56,'巨龙。'),(84,'可你偏偏被抓住了……')]),
        ([0x1ac648,0x1ac668,0x1ac688,0x1ac6a4,0x1ac6c0,0x1ac6dc,0x1ac6f4],[(24,'所幸，和往常一样，'),(40,'他们没有拿走你的剑。'),(64,'现在，干掉这些丑陋的小守卫，'),(80,'逃出去，继续你的任务吧……')]),
    ]
    largefont=font_bitmaps(FONT.parent/'fusion-pixel-12px-monospaced-zh_hans.bdf',12,10)
    h.append('typedef struct {const u32 *tiles;const u16 *map;unsigned count;} StoryPage;')
    page_entries=[];page_report=[]
    for pi,(addresses,lines) in enumerate(story_pages):
        ink=[[False]*240 for _ in range(160)]
        for y0,line in lines:
            assert 16+len(line)*12<=224,line
            for i,c in enumerate(line):
                assert c in largefont,c
                for y,row in enumerate(largefont[c]):
                    for x,v in enumerate(row):
                        if v:ink[y0+y][16+i*12+x]=True
        pixels=[[0]*256 for _ in range(256)]
        for y in range(160):
            for x in range(240):
                if ink[y][x]:
                    pixels[y][x]=4
                    if pixels[y][x+1]!=4:pixels[y][x+1]=15
                    if pixels[y+1][x]!=4:pixels[y+1][x]=15
        tiles12=[];tileids={};mapping=[]
        for ty in range(32):
            for tx in range(32):
                data=bytes(pixels[ty*8+y][tx*8+x]|pixels[ty*8+y][tx*8+x+1]<<4 for y in range(8) for x in range(0,8,2))
                if not any(data):mapping.append(0);continue
                if data not in tileids:
                    idx=len(tiles12);assert idx<320
                    tileids[data]=320+idx if idx<192 else 896+idx-192
                    tiles12.append(data)
                mapping.append(tileids[data]|0xc000)
        h.append(f'static const u32 story_tiles_{pi}[]={{'+','.join(hex(x) for data in tiles12 for x in struct.unpack('<8I',data))+'};')
        h.append(f'static const u16 story_map_{pi}[]={{'+','.join(map(str,mapping))+'};')
        page_entries.append(f'{{story_tiles_{pi},story_map_{pi},{len(tiles12)}}}')
        page_report.append({'page':pi+1,'font_px':12,'tiles':len(tiles12),'lines':lines})
    h.append('static const StoryPage story_pages[]={'+','.join(page_entries)+'};')
    story_index=[]
    for pi,(addresses,lines) in enumerate(story_pages):
        story_index.extend(f'{{0x{0x08000000+addr:x},{pi},{int(ai==0)}}}' for ai,addr in enumerate(addresses))
    h.append('static const struct {u32 address;u16 page,first;} story_addresses[]={'+','.join(story_index)+'};')
    h.append(f'#define STORY_ADDRESS_COUNT {sum(len(x[0]) for x in story_pages)}')
    # Ending narration uses two tile rows per line; its scroll cadence already
    # reserves 16px. Fixed atlas slots preserve preceding lines as they scroll.
    ending_tiles=[]; ending_ids={}; ending_entries=[]; ending_report=[]
    for r in records:
        if r['category']!='ending' or int(r['offset'],16)==0x1abd48:continue
        line=r['zh'].strip();ink=[[0]*240 for _ in range(16)]
        assert 24+len(line)*12<240
        for i,c in enumerate(line):
            for y,row in enumerate(largefont[c]):
                for x,v in enumerate(row):
                    if v:ink[y][24+i*12+x]=1
        pixels=[[0]*256 for _ in range(16)]
        for y in range(15):
            for x in range(239):
                if ink[y][x]:
                    pixels[y][x]=4
                    if pixels[y][x+1]!=4:pixels[y][x+1]=15
                    if pixels[y+1][x]!=4:pixels[y+1][x]=15
        mapping=[]
        for ty in range(2):
            for tx in range(32):
                data=bytes(pixels[ty*8+y][tx*8+x]|pixels[ty*8+y][tx*8+x+1]<<4 for y in range(8) for x in range(0,8,2))
                if not any(data):mapping.append(0xc000);continue
                if data not in ending_ids:
                    idx=len(ending_tiles);assert idx<144, 'Ending atlas must stay outside compact font cache'
                    ending_ids[data]=320+idx;ending_tiles.append(data)
                mapping.append(0xc000|ending_ids[data])
        idx=len(ending_entries)
        h.append(f'static const u16 ending_map_{idx}[]={{'+','.join(map(str,mapping))+'};')
        ending_entries.append(f'{{0x{0x08000000+int(r["offset"],16):x},ending_map_{idx}}}')
        ending_report.append({'address':r['offset'],'text':line,'font_px':12})
    h.append('static const u32 ending_tiles[]={' + ','.join(hex(x) for data in ending_tiles for x in struct.unpack('<8I',data))+'};')
    h.append('static const struct {u32 address;const u16 *map;} ending_lines[]={'+','.join(ending_entries)+'};')
    h.append(f'#define ENDING_LINE_COUNT {len(ending_entries)}')
    h.append(f'#define ENDING_TILE_COUNT {len(ending_tiles)}')
    entries=[]
    for i,r in enumerate(records):
        off=int(r['offset'],16);en=r['en'].encode('ascii');assert original[off:off+len(en)+1]==en+b'\0',r
        assert len(r['zh'])<=len(en),r
        seq=[charids[c] if ord(c)>=128 else ascii_tile(c) for c in r['zh']]
        h.append(f'static const u16 text_{i}[]={{'+','.join(map(str,seq))+'};')
        entries.append(f'{{0x{0x08000000+off:x},text_{i},{len(seq)},{len(en)},{int(r["category"]=="enemies")}}}')
    h.append('static const Translation translations[]={'+','.join(entries)+'};')
    h.append(f'#define TRANSLATION_COUNT {len(records)}')
    (BUILD/'zh_data.h').write_text('\n'.join(h)+'\n')
    base=(len(original)+0xfff)&~0xfff
    (BUILD/'patch.ld').write_text(f'SECTIONS {{ . = 0x{0x08000000+base:x}; .patch : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.comment*) *(.ARM.attributes*) *(.ARM.exidx*) }} }}')
    gcc=str(TOOLCHAIN/'arm-none-eabi-gcc')
    subprocess.run([gcc,'-mcpu=arm7tdmi','-mthumb','-Os','-std=c99','-fno-builtin','-fno-unwind-tables','-ffreestanding','-nostdlib','-I'+str(BUILD),'-Wl,-T,'+str(BUILD/'patch.ld'),'-Wl,-Map,'+str(BUILD/'patch.map'),'-o',str(BUILD/'patch.elf'),str(GAME/'tools/text_engine.c')],check=True)
    subprocess.run([str(TOOLCHAIN/'arm-none-eabi-objcopy'),'-O','binary',str(BUILD/'patch.elf'),str(BUILD/'patch.bin')],check=True)
    syms=subprocess.check_output([str(TOOLCHAIN/'arm-none-eabi-nm'),str(BUILD/'patch.elf')],text=True)
    symbols={m[2]:int(m[0],16) for l in syms.splitlines() if len(m:=l.split())==3}
    target=bytearray(original);target.extend(b'\xff'*(base-len(target)));target.extend((BUILD/'patch.bin').read_bytes())
    for off,symbol,expected in [(0x85c,'zh_write','f0b54446'),(0x440,'zh_status_text','fe22f0b5')]:
        assert original[off:off+4].hex()==expected
        target[off:off+8]=struct.pack('<HHI',0x4b00,0x4718,symbols[symbol]|1)
    # Only the credits' row-clear call changes; other text clearing stays 8px.
    assert original[0x2192:0x2196].hex()=='fef763fb'
    delta=symbols['zh_credit_clear']-(0x08002192+4)
    assert -(1<<22)<=delta<(1<<22) and delta%2==0
    target[0x2192:0x2196]=struct.pack('<HH',0xf000|((delta>>12)&0x7ff),0xf800|((delta>>1)&0x7ff))
    gfx={}
    if (GAME/'tools/graphics_zh.py').exists():
        sys.path.insert(0,str(GAME/'tools'))
        from graphics_zh import apply_graphics
        gfx=apply_graphics(target)
    # The input's title/gamecode are empty; keep its identity and correct checksum.
    target[0xbd]=(-sum(target[0xa0:0xbd])-0x19)&255
    out=GAME/'output/anguna_zh.gba';out.write_bytes(target)
    info={'original_sha256':EXPECTED,'sha256':hashlib.sha256(target).hexdigest(),'bytes':len(target),'translations':len(records),'glyphs':len(chars),'font':'Fusion Pixel zh_Hans: opening and ending narration 12px, compact UI 8px (SIL OFL 1.1)','opening_pages':page_report,'ending_lines':ending_report,'ending_tiles':len(ending_tiles),'text_hook':hex(symbols['zh_write']),'status_hook':hex(symbols['zh_status_text']),'cache_slots':176,'graphics':gfx}
    (BUILD/'build.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
