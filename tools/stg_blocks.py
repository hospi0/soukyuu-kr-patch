# -*- coding: utf-8 -*-
r"""게임 안 문구 맵(SS_ST?.BIN, 머리 4B 뒤 64칸 줄) → 글 블록(잉크 있는 연속 행 묶음) 나누고, 블록마다 «어느 문장 그림 세트로 그려야 맞는지» 판정 (2026-10-17)
  판정: 맞는 세트면 글자 획이 타일 경계를 넘어 이어짐 → 경계 연속성 점수(이웃 칸 경계 화소의 잉크 일치율)가 높은 쪽.
  python tools/stg_blocks.py <스테이지 문자>   → 블록 표 + work/stg/blocks_<X>.png(블록마다 판정된 세트로 렌더)
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')
# 스테이지 → (맵 파일, {세트 이름: 그림 spec}) — spec = CGB 경로 또는 '경로:GF위치'
SETS = {
    'B': ('STG_B/SS_ST1.BIN', {'PRE': 'STG_B/PREB_DAT.BIN:3BBFC', 'ATO': 'STG_B/ST1ATO.CGB'}),
    'O': ('STG_O/SS_ST2.BIN', {'PRE': 'STG_O/PREO_DAT.BIN:2FAB0', 'ATO': 'STG_O/ST2ATO.CGB'}),
    'C': ('STG_C/SS_ST3.BIN', {'PRE': 'STG_C/PREC_DAT.BIN:108', 'ATO': 'STG_C/ST3ATO.CGB'}),
    'A': ('STG_A/SS_ST4.BIN', {'PRE': 'STG_A/PREA_DAT.BIN:230CC', 'ATO': 'STG_A/ST4ATO.CGB'}),
    'S': ('STG_S/SS_ST5.BIN', {'PRE': 'STG_S/PRES_DAT.BIN:35AE4', 'ATO': 'STG_S/ST5ATO.CGB'}),
    'L': ('STG_L/SS_ST6.BIN', {'PRE': 'STG_L/PREL_DAT.BIN:7ECD8', 'ATO': 'STG_L/ST6ATO.CGB', 'NAKA': 'STG_L/ST6NAKA2.CGB'}),
}
FONT_LO, FONT_HI = 0x3A00, 0x3C00      # 0x74000~0x78000 = 공용 글꼴(FONT_TXT·SS_TX_AB) — 문장 그림 아님


def load_tiles(spec):
    if ':' in spec[2:]:
        p, off = spec.rsplit(':', 1)
        return sglz.decode(open(os.path.join(DISC, p), 'rb').read(), int(off, 16))[0]
    return open(os.path.join(DISC, spec), 'rb').read()


def load_map(path):
    d = open(os.path.join(DISC, path), 'rb').read()
    m = d[4:]; n = len(m) // 128
    return d, list(struct.unpack('>%dH' % (n * 64), m[:n * 128])), n


def chn(e):
    return (e & 0xFFF) | 0x3000


BLANK = set()


def is_text(e):
    return e not in (0, 0xFFFF) and e not in BLANK and chn(e) >= FONT_HI


def blocks(ents, n):
    """문장 그림 칸이 있는 행(화면 안 0~43열)을 연속 묶음으로 — 빈칸 값(파일에서 가장 흔한 값)은 뺌"""
    import collections
    BLANK.clear(); BLANK.update(v for v, _ in collections.Counter(ents).most_common(2))
    rows = [r for r in range(n) if any(is_text(e) for e in ents[r * 64:r * 64 + 44])]
    out = []
    for r in rows:
        if out and r == out[-1][1]:
            out[-1][1] = r + 1
        else:
            out.append([r, r + 1])
    return [tuple(b) for b in out]


def render_rows(ents, r0, r1, tiles):
    img = np.zeros(((r1 - r0) * 8, 512), np.uint8)
    for r in range(r0, r1):
        for x in range(64):
            e = ents[r * 64 + x]
            if not is_text(e):
                continue
            o = chn(e) * 0x20 - 0x78000
            if not 0 <= o <= len(tiles) - 32:
                continue
            a = np.frombuffer(tiles[o:o + 32], np.uint8)
            img[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return img


def continuity(img):
    """타일 경계(가로·세로)에서 맞닿은 화소의 잉크 일치율 — 잉크가 경계에 닿은 곳만 셈"""
    ink = img > 0
    tot = agree = 0
    for x in range(8, ink.shape[1], 8):
        a, b = ink[:, x - 1], ink[:, x]; m = a | b
        tot += m.sum(); agree += (a & b).sum()
    for y in range(8, ink.shape[0], 8):
        a, b = ink[y - 1], ink[y]; m = a | b
        tot += m.sum(); agree += (a & b).sum()
    return agree / tot if tot else 0.0


def classify(X):
    path, sets = SETS[X]
    d, ents, n = load_map(path)
    T = {k: load_tiles(v) for k, v in sets.items()}
    res = []
    for r0, r1 in blocks(ents, n):
        sc = {k: continuity(render_rows(ents, r0, r1, t)) for k, t in T.items()}
        best = max(sc, key=sc.get)
        res.append((r0, r1, best, sc))
    return res, ents, T


def main():
    X = sys.argv[1]
    res, ents, T = classify(X)
    parts = []
    for r0, r1, best, sc in res:
        print('행 %3d~%3d  %-4s  %s' % (r0, r1 - 1, best, ' '.join('%s=%.2f' % kv for kv in sc.items())))
        img = render_rows(ents, r0, r1, T[best])
        lab = np.full((10, 512), 0, np.uint8)
        parts += [np.where(img > 0, 255, 0).astype(np.uint8)[:, :352], np.full((4, 352), 90, np.uint8)]
    os.makedirs(os.path.join(ROOT, 'work', 'stg'), exist_ok=True)
    Image.fromarray(255 - np.concatenate(parts)).save(os.path.join(ROOT, 'work', 'stg', 'blocks_%s.png' % X))


if __name__ == '__main__':
    main()


def classify_rows(X):
    """행마다 세트 판정(그 행 안 세로 타일 경계 연속성 + 위아래 행과의 가로 경계) → 같은 세트 연속 행끼리 묶음 [(r0, r1, 세트)]"""
    path, sets = SETS[X]
    d, ents, n = load_map(path)
    blocks(ents, n)                                  # BLANK 채움
    T = {k: load_tiles(v) for k, v in sets.items()}
    rows = [r for r in range(n) if any(is_text(e) for e in ents[r * 64:r * 64 + 44])]
    raw = {}
    for r in rows:
        raw[r] = {k: continuity(render_rows(ents, max(0, r - 1), min(n, r + 2), t)) for k, t in T.items()}
    rs = set(rows); lab = {}
    for r in rows:                                   # 같은 글 덩어리 안 앞뒤 2행 평균으로 다듬음
        win = [q for q in range(r - 2, r + 3) if q in rs and all(z in rs for z in range(min(q, r), max(q, r) + 1))]
        avg = {k: sum(raw[q][k] for q in win) / len(win) for k in T}
        lab[r] = max(avg, key=avg.get)
    # 다수결로 다듬기(앞뒤 1행)
    out = []
    for r in rows:
        k = lab[r]
        if out and out[-1][1] == r and out[-1][2] == k:
            out[-1][1] = r + 1
        else:
            out.append([r, r + 1, k])
    return [tuple(o) for o in out], ents, T


if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == 'rows':
    pass
