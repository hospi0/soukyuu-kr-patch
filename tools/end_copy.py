# -*- coding: utf-8 -*-
r"""엔딩 문장 사본 맞추기 (2026-10-18) — ENDING_S.BIN 과 ENDING_T.BIN 의 엔딩 맵(0x1010C)·GF(0x12A08~원래 끝)는 원본이 똑같음 → S 의 새 바이트를 T 에
  python tools/end_copy.py   (nbg_kr.py end3 build 다음)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sglz
D = os.path.join(ROOT, 'work', 'disc', 'ENDING'); O = os.path.join(ROOT, 'work', 'out', 'ENDING')
s0 = open(os.path.join(D, 'ENDING_S.BIN'), 'rb').read(); t0 = open(os.path.join(D, 'ENDING_T.BIN'), 'rb').read()
a, b = 0x1010C, sglz.decode(s0, 0x12A08)[1]
assert s0[a:b] == t0[a:b], '원본 S/T 구간 다름'
s1 = open(os.path.join(O, 'ENDING_S.BIN'), 'rb').read()
t1 = bytearray(open(os.path.join(O, 'ENDING_T.BIN'), 'rb').read() if os.path.exists(os.path.join(O, 'ENDING_T.BIN')) else t0)
t1[a:b] = s1[a:b]
open(os.path.join(O, 'ENDING_T.BIN'), 'wb').write(bytes(t1))
print('ENDING_T 맞춤', hex(a), hex(b))
