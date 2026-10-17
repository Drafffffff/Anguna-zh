/* ROM-local text hook, ARM7TDMI Thumb. Fixed bounded cache in unused EWRAM.
 * The original text strings stay intact: pointer tables, strlen, game logic and
 * saves retain their original layout. Only presentation uses translated tiles.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#include "zh_data.h"

static const Translation *lookup(const char *s) {
    u32 p=(u32)s;
    int lo=0, hi=TRANSLATION_COUNT;
    while(lo<hi) {
        int mid=(lo+hi)>>1;
        if(translations[mid].address<p) lo=mid+1; else hi=mid;
    }
    return lo<TRANSLATION_COUNT && translations[lo].address==p ? translations+lo : 0;
}

static u16 ascii_tile(unsigned c) {
    return c<128 ? ascii_tiles[c] : 0;
}

/* 320..463 belongs to enemy portraits; 512..895 belongs to screen maps.
 * 464..511 and 896..1023 are unused by the original GBA game. Never evict
 * tiles referenced by the text map, including the off-screen credit rows.
 * Compare actual VRAM data so splash screens/portrait loads cannot stale a
 * software glyph cache. All VRAM accesses are at least 16 bits wide.
 */
static unsigned cache_slot(unsigned i) {return i<48 ? 464+i : 896+i-48;}
static unsigned glyph_tile(unsigned glyph, volatile u16 *map, volatile u32 *tiles, u8 *used) {
    const u32 *src=zh_glyphs[glyph];
    volatile u32 *magic=(volatile u32 *)0x0203e000;
    volatile u16 *cache=(volatile u16 *)0x0203e004;
    if(*magic!=0x5a48414e) {
        for(unsigned i=0;i<ZH_GLYPH_COUNT;i++)cache[i]=0xffff;
        *magic=0x5a48414e;
    }
    unsigned old=cache[glyph];
    if(old<176) {
        volatile u32 *dst=tiles+cache_slot(old)*8;
        unsigned k=0;
        while(k<8 && dst[k]==src[k])k++;
        if(k==8){used[old]=1;return cache_slot(old);}
    }
    int spare=-1;
    for(unsigned i=0;i<176;i++) {
        if(!used[i]){spare=i;break;}
    }
    if(spare<0) return 83; /* visible '?' instead of corrupting a live tile */
    unsigned slot=cache_slot(spare);
    for(unsigned k=0;k<8;k++) tiles[slot*8+k]=src[k];
    cache[glyph]=spare;
    used[spare]=1;
    return slot;
}

__attribute__((used,noinline,section(".text.entry")))
void zh_write(int x,int y,const char *s) {
    if(!s || x<0 || x>=32 || y<0 || y>=32) return;
    volatile u32 *bg=*(volatile u32 **)0x03001168;
    volatile u32 *tiles=(volatile u32 *)bg[0];
    volatile u16 *map=(volatile u16 *)bg[1];
    volatile u16 *pal=*(volatile u16 **)0x03004760;
    pal[254]=0;pal[255]=0x7fff;
    for(unsigned i=0;i<STORY_ADDRESS_COUNT;i++) {
        if(story_addresses[i].address!=(u32)s)continue;
        if(story_addresses[i].first) {
            const StoryPage *p=story_pages+story_addresses[i].page;
            for(unsigned j=0;j<p->count;j++) {
                unsigned slot=j<192 ? 320+j : 896+j-192;
                for(unsigned k=0;k<8;k++)tiles[slot*8+k]=p->tiles[j*8+k];
            }
            for(unsigned j=0;j<1024;j++)map[j]=p->map[j];
        }
        return;
    }
    for(unsigned i=0;i<ENDING_LINE_COUNT;i++) {
        if(ending_lines[i].address!=(u32)s)continue;
        for(unsigned j=0;j<ENDING_TILE_COUNT*8;j++)tiles[320*8+j]=ending_tiles[j];
        for(unsigned row=0;row<2;row++)
            for(unsigned col=0;col<32;col++)
                map[((y+row)&31)*32+col]=ending_lines[i].map[row*32+col];
        return;
    }
    unsigned at=y*32+x;
    const Translation *t=lookup(s);
    if(!t) {
        /* The enemy discovery popup constructs a padded name in RAM. */
        unsigned pad=0;
        while(s[pad]==' ' && pad<31) pad++;
        if((u32)s<0x08000000) {
            for(unsigned i=0;i<TRANSLATION_COUNT;i++) {
                const char *en=(const char *)translations[i].address;
                if(*en==' ' || translations[i].category!=1) continue;
                unsigned j=0;
                while(j<31-pad && en[j] && en[j]==s[pad+j]) j++;
                if(!en[j] && (!s[pad+j] || s[pad+j]==' ')) {
                    t=translations+i;at+=pad;break;
                }
            }
        }
    }
    if(!t) {
        for(unsigned i=0;at<1024;i++,at++) {
            unsigned c=(u8)s[i];
            map[at]=0xc000|ascii_tile(c);
            if(!c)break;
        }
        return;
    }
    unsigned end=at+t->english_length+1;
    if(end>1024)end=1024;
    for(unsigned p=at;p<end;p++)map[p]=0xc000;
    u8 used[176];
    for(volatile unsigned i=0;i<176;i++)used[i]=0;
    for(unsigned i=0;i<1024;i++) {
        unsigned slot=map[i]&1023;
        if(slot>=464 && slot<512)used[slot-464]=1;
        if(slot>=896)used[slot-896+48]=1;
    }
    for(unsigned i=0;i<t->length && at<1024;i++,at++) {
        unsigned c=t->text[i];
        unsigned tile=c>=256 ? glyph_tile(c-256,map,tiles,used) : c;
        map[at]=0xc000|tile;
    }
}

/* The GBA build has a second inlined renderer for status messages. */
__attribute__((used,noinline)) void zh_status_text(const char *s) {zh_write(2,18,s);}

/* Credit lines advance every 16px. Clear both rows, including row 31 wrap. */
__attribute__((used,noinline)) void zh_credit_clear(int x,int y,const char *s) {
    volatile u32 *bg=*(volatile u32 **)0x03001168;
    volatile u16 *map=(volatile u16 *)bg[1];
    for(unsigned row=0;row<2;row++)
        for(unsigned col=0;col<32;col++)map[((y+row)&31)*32+col]=0xc000;
}
