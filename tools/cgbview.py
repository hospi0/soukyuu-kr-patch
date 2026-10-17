# -*- coding: utf-8 -*-
r"""창궁홍련대 16비트 직접색 그림(.CGB) + 맵(.PNB/_PNT.BIN) → PNG (2026-10-17)
  CGB = 8×8 셀(RGB555 빅엔디언, 셀당 128 B)을 16×16 글자 하나 = 셀 4개(왼위·오른위·왼아래·오른아래) 순서로 이어 둔 것.
  맵 칸 값 v → 글자 데이터 위치 = v × 128 바이트(값이 4씩 = 글자 하나 512 B).  값 0 = 빈칸.
  python tools/cgbview.py <CGB> <맵> <출력.png> [--word 1|2] [--w 32] [--h 32] [--screen N] [--cols 22] [--rows 14] [--csz 16|8]
  저장 화면 BUP: --word 1 --w 32 --h 32 --csz 16 (화면 N = --screen) · 제목 TITLE.PNB: --word 2 --w 64 --h 64 --csz 8 --cols 44 --rows 30
"""
import argparse
import struct

import numpy as np
from PIL import Image


def cell(cgb, off):
    w = np.frombuffer(cgb[off:off + 128].ljust(128, b'\0'), '>u2').reshape(8, 8)
    rgb = np.stack([(w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3], -1).astype(np.uint8)
    return rgb


def render(cgb, mp, word=1, mw=32, mh=32, screen=0, cols=22, rows=14, csz=16):
    """csz=16: 칸 = 16×16 글자(값×128 B, 셀 4개) · csz=8: 칸 = 8×8 셀(값×32 B) — 제목 화면(2워드 표)"""
    step = 2 * word
    ents = [struct.unpack_from('>H', mp, i + (step - 2))[0] for i in range(0, len(mp) - step + 1, step)]
    base = screen * mw * mh
    img = np.zeros((rows * csz, cols * csz, 3), np.uint8)
    for y in range(rows):
        for x in range(cols):
            k = base + y * mw + x
            if k >= len(ents):
                continue
            v = ents[k] & 0x7FFF
            if not v:
                continue
            if csz == 8:
                img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = cell(cgb, v * 32); continue
            off = v * 128
            for j, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = cell(cgb, off + j * 128)
    return img


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cgb'); ap.add_argument('map'); ap.add_argument('out')
    ap.add_argument('--word', type=int, default=1); ap.add_argument('--w', type=int, default=32)
    ap.add_argument('--h', type=int, default=32); ap.add_argument('--screen', type=int, default=0)
    ap.add_argument('--cols', type=int, default=22); ap.add_argument('--rows', type=int, default=14)
    ap.add_argument('--base', type=int, default=0, help='CGB 가 VRAM 에 실리는 위치(바이트) — 맵 값에서 뺌')
    ap.add_argument('--csz', type=int, default=16)
    a = ap.parse_args()
    cgb = open(a.cgb, 'rb').read(); mp = open(a.map, 'rb').read()
    if a.base:
        cgb = bytes(a.base) + cgb
    Image.fromarray(render(cgb, mp, a.word, a.w, a.h, a.screen, a.cols, a.rows, a.csz)).save(a.out)
