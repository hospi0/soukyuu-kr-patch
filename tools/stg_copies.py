# -*- coding: utf-8 -*-
r"""1스테이지 출격 전 그림·맵의 사본 맞추기 (2026-10-17) — STG_B/ST1MAE.CGB·TOFF/ST1MAE.CGB = PREB_DAT GF 0x3BBFC 풀린 새 그림, TOFF/SS_ST1.BIN = STG_B/SS_ST1.BIN 새 맵
  python tools/stg_copies.py   (work/out/ 안에서)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sglz
OUT = os.path.join(ROOT, 'work', 'out')
nb = sglz.decode(open(os.path.join(OUT, 'STG_B', 'PREB_DAT.BIN'), 'rb').read(), 0x3BBFC)[0]
old = open(os.path.join(ROOT, 'work', 'disc', 'STG_B', 'ST1MAE.CGB'), 'rb').read()
assert len(nb) == len(old), (len(nb), len(old))
for p in ('STG_B/ST1MAE.CGB', 'TOFF/ST1MAE.CGB'):
    q = os.path.join(OUT, p); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(nb)
m = open(os.path.join(OUT, 'STG_B', 'SS_ST1.BIN'), 'rb').read()
q = os.path.join(OUT, 'TOFF', 'SS_ST1.BIN'); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(m)
print('사본 3개 완료', len(nb), len(m))
