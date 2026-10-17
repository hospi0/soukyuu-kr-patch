# -*- coding: utf-8 -*-
r"""0SSSOQ.BIN 정적 훑기: 파일 읽기(0x060121FC)·폴더 이동(0x060124A8) 호출부 → (폴더, 파일, 적재 주소) 목록 (2026-10-17)
  python tools/loadcalls.py [파일(work/disc 기준) 적재주소hex]   — 기본 0SSSOQ.BIN 0x06004000 · 오버레이 STG_?/STG_?.BIN = 0x060E0000
  SH-2: MOV.L @(disp,PC),Rn = 0xDnmm (주소 = (PC&~3)+4+mm*4) · JSR @Rm = 0x4m0B · MOV #imm,Rn = 0xEnii
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
EXE = os.path.join(ROOT, 'work', 'disc', '0SSSOQ.BIN')
BASE = 0x06004000
F_READ, F_CD = 0x060121FC, 0x060124A8


def main():
    global BASE
    exe = EXE
    if len(sys.argv) > 2:
        exe = os.path.join(ROOT, 'work', 'disc', sys.argv[1]); BASE = int(sys.argv[2], 16)
    x = open(exe, 'rb').read()
    main_x = open(EXE, 'rb').read()

    def u32(a):
        o = a - BASE
        return struct.unpack_from('>I', x, o)[0] if 0 <= o <= len(x) - 4 else None

    def cstr(a):
        o = a - BASE
        if not 0 <= o < len(x):
            return None
        e = x.find(b'\0', o)
        s = x[o:e]
        return s.decode('latin1') if 0 < len(s) < 40 and all(32 <= c < 127 for c in s) else None

    rows = []; cur_dir = None
    for o in range(0, len(x) - 1, 2):
        w = struct.unpack_from('>H', x, o)[0]
        if (w & 0xF0FF) != 0x400B:                       # JSR @Rm
            continue
        m = (w >> 8) & 15; pc = BASE + o
        regs = {}
        for back in range(2, 40, 2):                      # 직전 명령에서 MOV.L @(disp,PC),Rn 리터럴 모으기(지연 슬롯 포함)
            q = o - back
            if q < 0:
                break
            v = struct.unpack_from('>H', x, q)[0]
            if v >> 12 == 0xD:
                n = (v >> 8) & 15
                if n not in regs:
                    regs[n] = u32(((BASE + q) & ~3) + 4 + (v & 0xFF) * 4)
            if v == 0x000B or (v & 0xF0FF) == 0x400B:    # 앞 호출 경계
                break
        slot = struct.unpack_from('>H', x, o + 2)[0]      # 지연 슬롯
        if slot >> 12 == 0xD:
            regs[(slot >> 8) & 15] = u32(((pc + 2) & ~3) + 4 + (slot & 0xFF) * 4)
        tgt = regs.get(m)
        if tgt == F_CD:
            cur_dir = cstr(regs.get(4) or 0) or cur_dir
            rows.append((pc, 'CD', cur_dir, None))
        elif tgt == F_READ:
            rows.append((pc, 'READ', '%s/%s' % (cur_dir, cstr(regs.get(4) or 0)), regs.get(5)))
    for pc, k, a, b in rows:
        if k == 'READ':
            print('%08X  %-28s → %s' % (pc, a, '0x%X' % b if b is not None else '?'))
    print('읽기 호출 %d곳' % sum(1 for r in rows if r[1] == 'READ'))


if __name__ == '__main__':
    main()
