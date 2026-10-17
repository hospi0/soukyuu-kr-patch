# -*- coding: utf-8 -*-
r"""연습 메뉴 상세 본문(기체/인물·작전) 전부 렌더 (2026-10-17)
  PMENU.BIN 앞 목차 항목 [BD 맵(평문) + GF 글자 그림(압축, VRAM 0x6B000)] 쌍 — PM_JIK/PM_S123/PM_S456 은 모두 LWRAM 0x270000 에 실림.
  맵 = NBG3 1워드(16색, 8×8, 보조 모드 1): 칸 번호 = (v & 0xFFF) | 0x3000 → VRAM 번호×0x20, 팔레트 = v>>12 (색은 s7 스테이트 CRAM — 미리보기용).
  python tools/pm_detail.py   → work/pm/<파일>_<목차번호>.png + work/pm/list.tsv
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
BASE = 0x270000
VRAM_TILES = 0x6B000


def toc():
    d = open(os.path.join(DISC, 'PMENU', 'PMENU.BIN'), 'rb').read()
    out, i = [], 0
    while d[i:i + 2] in (b'GF', b'GP', b'BD', b'CD', b'CP'):
        out.append(struct.unpack_from('>2sHI', d, i)); i += 8
    return out


def cram_of(state='s7'):
    c = open(os.path.join(ROOT, 'work', 'mem', state, 'CRAM.bin'), 'rb').read()
    c = bytes(b for i in range(0, len(c), 2) for b in (c[i + 1], c[i]))
    return np.frombuffer(c, '>u2').astype(int)


def render(mapb, tiles, cram, w=64):
    ents = struct.unpack('>%dH' % (len(mapb) // 2), mapb)
    h = len(ents) // w
    img = np.zeros((h * 8, w * 8, 3), np.uint8)
    for k, v in enumerate(ents):
        chn = (v & 0xFFF) | 0x3000
        o = chn * 0x20 - VRAM_TILES
        if not 0 <= o <= len(tiles) - 32:
            continue
        a = np.frombuffer(tiles[o:o + 32], np.uint8); px = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8).astype(int)
        e = cram[(((v >> 12) & 15) * 16 + px) & 0x7FF]
        col = np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)
        col[px == 0] = 0
        y, x = divmod(k, w)
        img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = col
    return img


def main():
    t = toc(); cram = cram_of()
    os.makedirs(os.path.join(ROOT, 'work', 'pm'), exist_ok=True)
    files = {nm: open(os.path.join(DISC, 'PMENU', nm), 'rb').read() for nm in ('PM_JIK.BIN', 'PM_S123.BIN', 'PM_S456.BIN')}
    rows = []
    for k in range(len(t) - 1):
        tg, ta, tp = t[k]; bg, ba, bp = t[k + 1]
        if tg != b'GF' or ta != 0x6B00 or bg != b'BD':
            continue
        for nm, d in files.items():
            go, bo = tp - BASE, bp - BASE
            if not (0 <= go < len(d) and 0 <= bo < len(d)):
                continue
            try:
                tiles, end = sglz.decode(d, go)
            except IndexError:
                continue
            mapb = d[bo:go]                              # 맵은 GF 바로 앞까지
            if len(tiles) < 1024 or len(mapb) % 128:
                continue
            img = render(mapb, tiles, cram)
            if img.max() == 0:
                continue
            p = os.path.join(ROOT, 'work', 'pm', '%s_%02d.png' % (nm.split('.')[0], k))
            Image.fromarray(img).save(p)
            rows.append('%s\t%d\t%05X\t%d\t%05X\t%d\t%d' % (nm, k, go, end - go, bo, len(mapb), len(tiles)))
            print(nm, k, 'GF 0x%05X(%d B) 맵 0x%05X(%d B) 풀린 %d' % (go, end - go, bo, len(mapb), len(tiles)))
    open(os.path.join(ROOT, 'work', 'pm', 'list.tsv'), 'w', encoding='utf-8').write(
        '파일\t목차\tGF위치\tGF크기\t맵위치\t맵크기\t풀린크기\n' + '\n'.join(rows) + '\n')


if __name__ == '__main__':
    main()
