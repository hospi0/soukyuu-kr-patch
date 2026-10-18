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

# ★4·6스테이지 출격 전 맵(0~35행)은 STG?_DAT 안에도 한 벌 있고 게임은 그걸 씀 — 안 맞추면 새 그림 + 옛 맵으로 글자가 뒤섞임(2026-10-18 실기)
EMB = [('STG_A/SS_ST4.BIN', 'STG_A/STGA_DAT.BIN', 0xE72C, 36), ('STG_L/SS_ST6.BIN', 'STG_L/STGL_DAT.BIN', 0x347D4, 36)]
DISC = os.path.join(ROOT, 'work', 'disc')
for mp, dp, at, rows in EMB:
    om = open(os.path.join(DISC, mp), 'rb').read()[4:4 + rows * 128]
    od = open(os.path.join(DISC, dp), 'rb').read()
    assert od[at:at + rows * 128] == om, ('사본 자리 원본 불일치', dp)
    nm = open(os.path.join(OUT, mp), 'rb').read()[4:4 + rows * 128]
    q = os.path.join(OUT, dp)
    body = bytearray(open(q, 'rb').read() if os.path.exists(q) else od)
    body[at:at + rows * 128] = nm
    os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(bytes(body))
    print('맵 사본', dp, hex(at), rows, '행')

# ★6스테이지 경고 «위험»(PREL_DAT 0x28DBC·0x290E0)은 stg_build 가 PREL_DAT 를 디스크 원본부터 다시 쓰면 사라짐 → 여기서 다시 넣음(2026-10-18 실기)
import subprocess
subprocess.run([sys.executable, os.path.join(HERE, 'danger_kr.py'), 'build'])
