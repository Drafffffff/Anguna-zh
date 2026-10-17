/* Test-only mGBA access. Never linked into the distributed ROM. */
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <mgba/internal/arm/arm.h>
#include <mgba/internal/arm/isa-inlines.h>
#include <mgba-util/vfs.h>
#include <string.h>
struct mCore *GBACoreCreate(void);
static struct mCore *core;
static color_t pixels[240*160];
static unsigned last_result;
static void quiet(struct mLogger*l,int cat,enum mLogLevel level,const char*fmt,va_list args) {
    (void)l;(void)cat;(void)level;(void)fmt;(void)args;
}
static struct mLogger logger={quiet,0};
int anguna_open(const char *rom) {
    mLogSetDefaultLogger(&logger);
    core=GBACoreCreate();if(!core->init(core))return 0;
    mCoreInitConfig(core,0);core->setVideoBuffer(core,pixels,240);
    if(!core->loadROM(core,VFileOpen(rom,0)))return 0;
    core->reset(core);return 1;
}
void anguna_frame(unsigned keys,unsigned frames) {
    core->setKeys(core,keys);for(unsigned i=0;i<frames;i++)core->runFrame(core);
}
const void *anguna_pixels(void) {return pixels;}
unsigned anguna_read(unsigned addr,unsigned size) {
    return size==1?core->busRead8(core,addr):size==2?core->busRead16(core,addr):core->busRead32(core,addr);
}
void anguna_write(unsigned addr,unsigned value,unsigned size) {
    if(size==1)core->busWrite8(core,addr,value);else if(size==2)core->busWrite16(core,addr,value);else core->busWrite32(core,addr,value);
}
void anguna_jump(unsigned addr,unsigned r0,unsigned r1,unsigned r2) {
    struct ARMCore *a=core->cpu;
    _ARMSetMode(a,MODE_THUMB);a->gprs[0]=r0;a->gprs[1]=r1;a->gprs[2]=r2;
    a->gprs[14]=0x0203f001;
    core->busWrite16(core,0x0203f000,0xe7fe);
    a->gprs[15]=addr&~1;ThumbWritePC(a);
}
/* Execute a nonblocking ROM routine and resume the original game context. */
int anguna_call(unsigned addr,unsigned r0,unsigned r1,unsigned r2) {
    struct ARMCore *a=core->cpu;
    int regs[16];memcpy(regs,a->gprs,sizeof(regs));
    unsigned cpsr=a->cpsr.packed;unsigned prefetch[2];memcpy(prefetch,a->prefetch,sizeof(prefetch));
    enum ExecutionMode mode=a->executionMode;
    anguna_jump(addr,r0,r1,r2);
    unsigned i;
    for(i=0;i<2000000;i++) {
        if(a->gprs[15]==0x0203f002)break;
        core->step(core);
    }
    last_result=a->gprs[0];
    memcpy(a->gprs,regs,sizeof(regs));a->cpsr.packed=cpsr;
    _ARMSetMode(a,mode);a->memory.setActiveRegion(a,regs[15]);
    memcpy(a->prefetch,prefetch,sizeof(prefetch));
    return i<2000000 ? (int)i : -1;
}
unsigned anguna_pc(void){struct ARMCore*a=core->cpu;return a->gprs[15];}
unsigned anguna_result(void){return last_result;}
void anguna_close(void){core->deinit(core);}
