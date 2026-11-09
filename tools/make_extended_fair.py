"""Derive blobs/extended-fair/libnam_hook.so from the Extended hook: turn the calls to sched_setscheduler / setpriority / nice
(lower_background_thread_priority) into `mov r0,#0`. Usage: make_extended_fair.py IN.so OUT.so   (needs pyelftools, capstone)."""
import struct,sys,capstone
from elftools.elf.elffile import ELFFile
src,dst=sys.argv[1:3]
d=bytearray(open(src,'rb').read()); e=ELFFile(open(src,'rb'))
dyn=e.get_section_by_name('.dynsym'); rel=e.get_section_by_name('.rel.plt')
got={r['r_offset']:dyn.get_symbol(r['r_info_sym']).name for r in rel.iter_relocations()}
plt=e.get_section_by_name('.plt'); base=plt['sh_addr']; off=plt['sh_offset']
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM); md.detail=True
stubs={}
for a in range(base+20, base+plt['sh_size'], 12):       # skip PLT0 (20 bytes)
    i=list(md.disasm(bytes(d[off+a-base:off+a-base+12]),a))
    if len(i)<3: continue
    # add ip,pc,#x ; add ip,ip,#y ; ldr pc,[ip,#z]!
    try:
        x=i[0].operands[2].imm; y=i[1].operands[2].imm; z=i[2].operands[1].mem.disp
    except Exception: continue
    g=(a+8+x)+y+z
    if g in got: stubs[a]=got[g]
BAD={'sched_setscheduler','setpriority','nice'}
tgt={a for a,n in stubs.items() if n in BAD}|{0xa609c}; stubs[0xa609c]='nice'
print('stubs',{hex(a):stubs[a] for a in tgt})
txt=e.get_section_by_name('.text'); t0=txt['sh_offset']; ta=txt['sh_addr']
n=0
for o in range(0,txt['sh_size'],4):
    w=struct.unpack_from('<I',d,t0+o)[0]
    if (w>>24)&0xF==0xB and (w>>28)==0xE:                # BL always
        imm=w&0xFFFFFF
        if imm&0x800000: imm-=1<<24
        dest=ta+o+8+imm*4
        if dest in tgt:
            struct.pack_into('<I',d,t0+o,0xE3A00000)       # mov r0,#0
            print('patched call at',hex(ta+o),stubs[dest]); n+=1
print(n,'calls patched')
open(dst,'wb').write(d)
