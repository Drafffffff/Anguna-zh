#!/usr/bin/env python3
"""Deterministic indexed-pixel Chinese title assets; original fixed resource sizes.
No engine, map dimensions, palette indices or selection-arrow coordinates change.
"""
from pathlib import Path
import struct, json
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
FONTROOT=ROOT/'assets/fonts'
SPECS={
 'title':dict(map=0x2d828,tiles=0x2dda8,pal=0x34fa8,count=456,new=254,cont=255),
 'gameover':dict(map=0x3a648,tiles=0x3abc8,pal=0x41908,count=437,new=16,cont=33),
}
def decode(rom,s):
 pal=struct.unpack_from('<256H',rom,s['pal']);rgb=[((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31) for v in pal]
 im=Image.new('P',(256,176)); im.putpalette([c for col in rgb for c in col]);p=im.load()
 for i,v in enumerate(struct.unpack_from('<704H',rom,s['map'])):
  for y in range(8):
   for x in range(8):
    p[(i%32)*8+x,(i//32)*8+y]=rom[s['tiles']+(v&1023)*64+(7-y if v&2048 else y)*8+(7-x if v&1024 else x)]
 return im,rgb

def font(size):
 p=FONTROOT/f'fusion-pixel-{size}px-monospaced-zh_hans.bdf'
 result={}
 for block in p.read_text().split('STARTCHAR ')[1:]:
  lines=block.splitlines(); cp=int(next(x for x in lines if x.startswith('ENCODING ')).split()[1]);w,h,xo,yo=map(int,next(x for x in lines if x.startswith('BBX ')).split()[1:]);start=lines.index('BITMAP')+1
  points=[]
  for y,row in enumerate(lines[start:start+h]):
   bits=int(row,16)
   for x in range(w):
    if bits & (1<<(len(row)*4-x-1)):points.append((x+xo,y+(9 if size==10 else 10)-h-yo))
  result[chr(cp)]=points
 return result
FONTS={}
def text(im,txt,x,y,size,color,scale=1):
 if size not in FONTS:FONTS[size]=font(size)
 p=im.load()
 for ch in txt:
  assert ch in FONTS[size],ch
  for gx,gy in FONTS[size][ch]:
   for dy in range(scale):
    for dx in range(scale):p[x+gx*scale+dx,y+gy*scale+dy]=color
  x+=size*scale

def encode(im,count):
 tiles=[];lookup={};maps=[]
 for ty in range(22):
  for tx in range(32):
   raw=bytes(im.getpixel((tx*8+x,ty*8+y)) for y in range(8) for x in range(8))
   if raw not in lookup:
    index=len(tiles);tiles.append(raw)
    for fy in range(2):
     for fx in range(2):
      variant=bytes(raw[(7-y if fy else y)*8+(7-x if fx else x)] for y in range(8) for x in range(8))
      lookup.setdefault(variant,index|(fx<<10)|(fy<<11))
   maps.append(lookup[raw])
 assert len(tiles)<=count,(len(tiles),count)
 return b''.join(tiles)+bytes((count-len(tiles))*64),struct.pack('<704H',*maps),len(tiles)

def apply_graphics(rom,preview=True):
 results={}
 for name,s in SPECS.items():
  original,rgb=decode(rom,s); im=original.copy();draw=ImageDraw.Draw(im)
  # Both menu labels occupy the original selection color indices; palette cycling works unchanged.
  draw.rectangle((57,128,111,143),fill=0); draw.rectangle((140,128,188,143),fill=0)
  text(im,'新游戏',69,130,12,s['new']);text(im,'继续游戏',141,130,12,s['cont'])
  # Opaque, pixel-aligned plaque removes all English pixels while retaining the brand and scene.
  def nearest(target):
   return min((i for i in range(1,254) if i not in (s['new'],s['cont'])), key=lambda i:sum((rgb[i][j]-target[j])**2 for j in range(3)))
  dark=nearest((16,35,16) if name=='title' else (43,20,8));gold=nearest((208,186,110));ink=nearest((255,241,194))
  box=(65,75,193,118) if name=='title' else (44,70,195,104)
  draw.rectangle(box,fill=dark,outline=gold)
  # Fine inset corners and a one-pixel shadow retain an old handheld pixel-art treatment.
  txt='美德勇士' if name=='title' else '游戏结束';x=82 if name=='title' else 72;y=84 if name=='title' else 76
  text(im,txt,x+1,y+1,12,0,2);text(im,txt,x,y,12,ink,2)
  tiles,maps,n=encode(im,s['count'])
  # Arrow frames and all otherwise untouched indexed pixels must survive exactly, including palette selection.
  for y in list(range(128,144))+list(range(160,176)):
   for x in range(112,136):assert im.getpixel((x,y))==original.getpixel((x,y))
  rom[s['tiles']:s['tiles']+len(tiles)]=tiles;rom[s['map']:s['map']+len(maps)]=maps
  decoded,_=decode(rom,s);assert decoded.tobytes()==im.tobytes()
  results[name]={'tiles_used':n,'tiles_capacity':s['count'],'map_offset':hex(s['map']),'tiles_offset':hex(s['tiles']),'palette_unchanged':True,'selection_indices':[s['new'],s['cont']]}
  if preview:
   out=ROOT/'analysis';out.mkdir(exist_ok=True)
   for variant,pic in [('original',original),('zh',decoded)]:pic.convert('RGB').resize((768,528),Image.Resampling.NEAREST).save(out/f'graphics_{name}_{variant}.png')
 return results
if __name__=='__main__':
 r=bytearray((ROOT/'original/Anguna-Warriors-of-Virtue.gba').read_bytes());results=apply_graphics(r)
 (ROOT/'analysis/graphics_report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(json.dumps(results,ensure_ascii=False,indent=2))
