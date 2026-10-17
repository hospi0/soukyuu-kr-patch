# -*- coding: utf-8 -*-
r"""상세 본문 페이지 배치 분석 (2026-10-17) — 단(열) 경계·줄(y 범위·x 범위·높이) 목록
  화면은 세로 2배 인터레이스: 원본 글자 ≈ 폭 8.5 × 높이 17px.
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pm_detail as P, sglz


def page(fname, k):
    t = P.toc(); d = open(os.path.join(P.DISC, 'PMENU', fname), 'rb').read()
    go = t[k][2] - P.BASE; bo = t[k + 1][2] - P.BASE
    tiles, end = sglz.decode(d, go); ents = list(struct.unpack('>%dH' % ((go - bo) // 2), d[bo:go]))
    img = np.zeros((len(ents) // 64 * 8, 512), np.uint8); pal = np.zeros((len(ents) // 64, 64), int)
    for i, v in enumerate(ents):
        o = ((v & 0xFFF) | 0x3000) * 0x20 - P.VRAM_TILES; y, x = divmod(i, 64); pal[y, x] = v >> 12
        if 0 <= o <= len(tiles) - 32:
            a = np.frombuffer(tiles[o:o + 32], np.uint8); img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return dict(d=d, go=go, bo=bo, end=end, tiles=tiles, ents=ents, img=img, pal=pal)


def columns(img):
    ink = (img > 0).any(0); xs = np.nonzero(ink)[0]
    cols = [[xs[0], xs[0] + 1]]
    for x in xs[1:]:
        if x - cols[-1][1] > 14:
            cols.append([x, x + 1])
        else:
            cols[-1][1] = x + 1
    return cols


def lines(img, x0, x1):
    ink = (img[:, x0:x1] > 0).sum(1) > 0; out = []; y = 0
    while y < len(ink):
        if not ink[y]:
            y += 1; continue
        a = y
        while y < len(ink) and ink[y]:
            y += 1
        xs = np.nonzero((img[a:y, x0:x1] > 0).any(0))[0]
        out.append((a, y, x0 + xs.min(), x0 + xs.max() + 1))
    return out


if __name__ == '__main__':
    for ln in open(os.path.join(P.ROOT, 'work', 'pm', 'valid.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f, k, _ = ln.split('\t'); k = int(k)
        p = page(f, k); cols = columns(p['img'])
        print('%s %d 단 %s' % (f, k, cols))
        for c in cols:
            ls = lines(p['img'], c[0], c[1])
            print('   ', [(a, b - a, x0, x1) for a, b, x0, x1 in ls])
