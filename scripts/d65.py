#!/usr/bin/env python3
"""Minimal 65816 disassembler (enough for reading SNES text-renderer code)."""
import sys

# addressing mode table: opcode -> (mnemonic, mode)
# modes: imp, acc, imm8, imm16, dp, dpx, dpy, abs, absx, absy, ind, indx, indy,
#        indl, indly, sr, sr_y, dpind, dpindl, dpxind, absl, abslx
OPS = {}
def op(code, name, mode):
    OPS[code] = (name, mode)

for c in range(256):
    op(c, "???", "imp")

# build from a compact table: (opcode, mnemonic, mode)
T = [
(0x00,"BRK","imm8"),(0x01,"ORA","dpxind"),(0x02,"COP","imm8"),(0x03,"ORA","sr"),
(0x04,"TSB","dp"),(0x05,"ORA","dp"),(0x06,"ASL","dp"),(0x07,"ORA","dpindl"),
(0x08,"PHP","imp"),(0x09,"ORA","imm8"),(0x0A,"ASL","acc"),(0x0B,"PHD","imp"),
(0x0C,"TSB","abs"),(0x0D,"ORA","abs"),(0x0E,"ASL","abs"),(0x0F,"ORA","absl"),
(0x10,"BPL","rel"),(0x11,"ORA","indy"),(0x12,"ORA","dpind"),(0x13,"ORA","sr_y"),
(0x14,"TRB","dp"),(0x15,"ORA","dpx"),(0x16,"ASL","dpx"),(0x17,"ORA","dpindl"),
(0x18,"CLC","imp"),(0x19,"ORA","absy"),(0x1A,"INC","acc"),(0x1B,"TCS","imp"),
(0x1C,"TRB","abs"),(0x1D,"ORA","absx"),(0x1E,"ASL","absx"),(0x1F,"ORA","abslx"),
(0x20,"JSR","abs"),(0x21,"AND","dpxind"),(0x22,"JSL","absl"),(0x23,"AND","sr"),
(0x24,"BIT","dp"),(0x25,"AND","dp"),(0x26,"ROL","dp"),(0x27,"AND","dpindl"),
(0x28,"PLP","imp"),(0x29,"AND","imm8"),(0x2A,"ROL","acc"),(0x2B,"PLD","imp"),
(0x2C,"BIT","abs"),(0x2D,"AND","abs"),(0x2E,"ROL","abs"),(0x2F,"AND","absl"),
(0x30,"BMI","rel"),(0x31,"AND","indy"),(0x32,"AND","dpind"),(0x33,"AND","sr_y"),
(0x34,"BIT","dpx"),(0x35,"AND","dpx"),(0x36,"ROL","dpx"),(0x37,"AND","dpindl"),
(0x38,"SEC","imp"),(0x39,"AND","absy"),(0x3A,"DEC","acc"),(0x3B,"TSC","imp"),
(0x3C,"BIT","absx"),(0x3D,"AND","absx"),(0x3E,"ROL","absx"),(0x3F,"AND","abslx"),
(0x40,"RTI","imp"),(0x41,"EOR","dpxind"),(0x42,"WDM","imm8"),(0x43,"EOR","sr"),
(0x44,"MVP","mv"),(0x45,"EOR","dp"),(0x46,"LSR","dp"),(0x47,"EOR","dpindl"),
(0x48,"PHA","imp"),(0x49,"EOR","imm8"),(0x4A,"LSR","acc"),(0x4B,"PHK","imp"),
(0x4C,"JMP","abs"),(0x4D,"EOR","abs"),(0x4E,"LSR","abs"),(0x4F,"EOR","absl"),
(0x50,"BVC","rel"),(0x51,"EOR","indy"),(0x52,"EOR","dpind"),(0x53,"EOR","sr_y"),
(0x54,"MVN","mv"),(0x55,"EOR","dpx"),(0x56,"LSR","dpx"),(0x57,"EOR","dpindl"),
(0x58,"CLI","imp"),(0x59,"EOR","absy"),(0x5A,"PHY","imp"),(0x5B,"TCD","imp"),
(0x5C,"JML","absl"),(0x5D,"EOR","absx"),(0x5E,"LSR","absx"),(0x5F,"EOR","abslx"),
(0x60,"RTS","imp"),(0x61,"ADC","dpxind"),(0x62,"PER","rel16"),(0x63,"ADC","sr"),
(0x64,"STZ","dp"),(0x65,"ADC","dp"),(0x66,"ROR","dp"),(0x67,"ADC","dpindl"),
(0x68,"PLA","imp"),(0x69,"ADC","imm8"),(0x6A,"ROR","acc"),(0x6B,"RTL","imp"),
(0x6C,"JMP","ind"),(0x6D,"ADC","abs"),(0x6E,"ROR","abs"),(0x6F,"ADC","absl"),
(0x70,"BVS","rel"),(0x71,"ADC","indy"),(0x72,"ADC","dpind"),(0x73,"ADC","sr_y"),
(0x74,"STZ","dpx"),(0x75,"ADC","dpx"),(0x76,"ROR","dpx"),(0x77,"ADC","dpindl"),
(0x78,"SEI","imp"),(0x79,"ADC","absy"),(0x7A,"PLY","imp"),(0x7B,"TDC","imp"),
(0x7C,"JMP","indx"),(0x7D,"ADC","absx"),(0x7E,"ROR","absx"),(0x7F,"ADC","abslx"),
(0x80,"BRA","rel"),(0x81,"STA","dpxind"),(0x82,"BRL","rel16"),(0x83,"STA","sr"),
(0x84,"STY","dp"),(0x85,"STA","dp"),(0x86,"STX","dp"),(0x87,"STA","dpindl"),
(0x88,"DEY","imp"),(0x89,"BIT","imm8"),(0x8A,"TXA","imp"),(0x8B,"PHB","imp"),
(0x8C,"STY","abs"),(0x8D,"STA","abs"),(0x8E,"STX","abs"),(0x8F,"STA","absl"),
(0x90,"BCC","rel"),(0x91,"STA","indy"),(0x92,"STA","dpind"),(0x93,"STA","sr_y"),
(0x94,"STY","dpx"),(0x95,"STA","dpx"),(0x96,"STX","dpy"),(0x97,"STA","dpindl"),
(0x98,"TYA","imp"),(0x99,"STA","absy"),(0x9A,"TXS","imp"),(0x9B,"TXY","imp"),
(0x9C,"STZ","abs"),(0x9D,"STA","absx"),(0x9E,"STZ","absx"),(0x9F,"STA","abslx"),
(0xA0,"LDY","imm8"),(0xA1,"LDA","dpxind"),(0xA2,"LDX","imm8"),(0xA3,"LDA","sr"),
(0xA4,"LDY","dp"),(0xA5,"LDA","dp"),(0xA6,"LDX","dp"),(0xA7,"LDA","dpindl"),
(0xA8,"TAY","imp"),(0xA9,"LDA","imm8"),(0xAA,"TAX","imp"),(0xAB,"PLB","imp"),
(0xAC,"LDY","abs"),(0xAD,"LDA","abs"),(0xAE,"LDX","abs"),(0xAF,"LDA","absl"),
(0xB0,"BCS","rel"),(0xB1,"LDA","indy"),(0xB2,"LDA","dpind"),(0xB3,"LDA","sr_y"),
(0xB4,"LDY","dpx"),(0xB5,"LDA","dpx"),(0xB6,"LDX","dpy"),(0xB7,"LDA","dpindl"),
(0xB8,"CLV","imp"),(0xB9,"LDA","absy"),(0xBA,"TSX","imp"),(0xBB,"TYX","imp"),
(0xBC,"LDY","absx"),(0xBD,"LDA","absx"),(0xBE,"LDX","absy"),(0xBF,"LDA","abslx"),
(0xC0,"CPY","imm8"),(0xC1,"CMP","dpxind"),(0xC2,"REP","imm8"),(0xC3,"CMP","sr"),
(0xC4,"CPY","dp"),(0xC5,"CMP","dp"),(0xC6,"DEC","dp"),(0xC7,"CMP","dpindl"),
(0xC8,"INY","imp"),(0xC9,"CMP","imm8"),(0xCA,"DEX","imp"),(0xCB,"WAI","imp"),
(0xCC,"CPY","abs"),(0xCD,"CMP","abs"),(0xCE,"DEC","abs"),(0xCF,"CMP","absl"),
(0xD0,"BNE","rel"),(0xD1,"CMP","indy"),(0xD2,"CMP","dpind"),(0xD3,"CMP","sr_y"),
(0xD4,"PEI","dpind"),(0xD5,"CMP","dpx"),(0xD6,"DEC","dpx"),(0xD7,"CMP","dpindl"),
(0xD8,"CLD","imp"),(0xD9,"CMP","absy"),(0xDA,"PHX","imp"),(0xDB,"STP","imp"),
(0xDC,"JML","indl"),(0xDD,"CMP","absx"),(0xDE,"DEC","absx"),(0xDF,"CMP","abslx"),
(0xE0,"CPX","imm8"),(0xE1,"SBC","dpxind"),(0xE2,"SEP","imm8"),(0xE3,"SBC","sr"),
(0xE4,"CPX","dp"),(0xE5,"SBC","dp"),(0xE6,"INC","dp"),(0xE7,"SBC","dpindl"),
(0xE8,"INX","imp"),(0xE9,"SBC","imm8"),(0xEA,"NOP","imp"),(0xEB,"XBA","imp"),
(0xEC,"CPX","abs"),(0xED,"SBC","abs"),(0xEE,"INC","abs"),(0xEF,"SBC","absl"),
(0xF0,"BEQ","rel"),(0xF1,"SBC","indy"),(0xF2,"SBC","dpind"),(0xF3,"SBC","sr_y"),
(0xF4,"PEA","abs"),(0xF5,"SBC","dpx"),(0xF6,"INC","dpx"),(0xF7,"SBC","dpindl"),
(0xF8,"SED","imp"),(0xF9,"SBC","absy"),(0xFA,"PLX","imp"),(0xFB,"XCE","imp"),
(0xFC,"JSR","indx"),(0xFD,"SBC","absx"),(0xFE,"INC","absx"),(0xFF,"SBC","abslx"),
]
for c,n,m in T: OPS[c]=(n,m)

MODES = {
 "imp":0,"acc":0,"imm8":1,"imm16":2,"dp":1,"dpx":1,"dpy":1,"abs":2,"absx":2,"absy":2,
 "ind":2,"indx":2,"indy":1,"indl":2,"indly":1,"sr":1,"sr_y":1,"dpind":1,"dpindl":1,
 "dpxind":1,"absl":3,"abslx":3,"rel":1,"rel16":2,"mv":2,"dpind":1,
}

def dis(rom, base_cpu, length, m=1, x=1):
    out=[]
    OP_SIZE={"imp":0,"acc":0,"imm8":1,"imm16":2,"dp":1,"dpx":1,"dpy":1,"abs":2,"absx":2,
      "absy":2,"ind":2,"indx":2,"indy":1,"indl":2,"indly":1,"sr":1,"sr_y":1,"dpind":1,
      "dpindl":1,"dpxind":1,"absl":3,"abslx":3,"rel":1,"rel16":2,"mv":2}
    A_MOPS={0xA9,0x29,0x09,0x49,0x69,0xE9,0xC9,0x89}
    X_MOPS={0xA2,0xA0,0xE0,0xC0}
    i=0
    while i < length:
        cpu = base_cpu + i
        b = rom[i]
        name, mode = OPS[b]
        osz = OP_SIZE.get(mode,1)
        if b in A_MOPS: osz = 1 if m else 2
        if b in X_MOPS: osz = 1 if x else 2
        raw = rom[i:i+1+osz]
        if len(raw)<1+osz: break
        hexb=' '.join(f'{xx:02X}' for xx in raw)
        def a16(lo,hi): return (hi<<8)|lo
        arg=""
        if mode=="imp": arg=""
        elif mode=="acc": arg="A"
        elif mode=="imm8": arg=f"#${raw[1]:02X}"
        elif mode=="imm16": arg=f"#${a16(raw[1],raw[2]):04X}"
        elif mode=="dp": arg=f"${raw[1]:02X}"
        elif mode=="dpx": arg=f"${raw[1]:02X},X"
        elif mode=="dpy": arg=f"${raw[1]:02X},Y"
        elif mode=="dpxind": arg=f"(${raw[1]:02X},X)"
        elif mode=="indy": arg=f"(${raw[1]:02X}),Y"
        elif mode=="dpind": arg=f"(${raw[1]:02X})"
        elif mode=="dpindl": arg=f"[${raw[1]:02X}]"
        elif mode=="sr": arg=f"${raw[1]:02X},S"
        elif mode=="sr_y": arg=f"${raw[1]:02X},S,Y"
        elif mode=="abs": arg=f"${a16(raw[1],raw[2]):04X}"
        elif mode=="absx": arg=f"${a16(raw[1],raw[2]):04X},X"
        elif mode=="absy": arg=f"${a16(raw[1],raw[2]):04X},Y"
        elif mode=="ind": arg=f"(${a16(raw[1],raw[2]):04X})"
        elif mode=="indx": arg=f"(${a16(raw[1],raw[2]):04X},X)"
        elif mode=="indl": arg=f"[${a16(raw[1],raw[2]):04X}]"
        elif mode=="indly": arg=f"[${raw[1]:02X}],Y"
        elif mode=="absl": arg=f"${raw[3]:02X}{raw[2]:02X}{raw[1]:02X}"
        elif mode=="abslx": arg=f"${raw[3]:02X}{raw[2]:02X}{raw[1]:02X},X"
        elif mode=="rel":
            d=raw[1]; d=d-256 if d>127 else d
            arg=f"${(cpu+2+d)&0xFFFF:04X}"
        elif mode=="rel16":
            d=a16(raw[1],raw[2]); d=d-65536 if d>32767 else d
            arg=f"${(cpu+3+d)&0xFFFF:04X}"
        elif mode=="mv": arg=f"${raw[2]:02X},${raw[1]:02X}"
        out.append(f"{cpu:06X}: {hexb:<12}{name} {arg}".rstrip())
        if b==0xC2: # REP
            if raw[1]&0x20: m=0
            if raw[1]&0x10: x=0
        elif b==0xE2: # SEP
            if raw[1]&0x20: m=1
            if raw[1]&0x10: x=1
        elif b==0x28: pass
        i += 1+osz
    return out

if __name__=="__main__":
    import sys
    rom=open(sys.argv[1],'rb').read()
    base=int(sys.argv[2],16)
    start=int(sys.argv[3],16)
    end=int(sys.argv[4],16)
    for line in dis(rom[start:end], base, end-start, 1, 1):
        print(line)
