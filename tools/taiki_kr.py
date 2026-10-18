# -*- coding: utf-8 -*-
r"""2P 자리 «待機中» → «대기 중» (2026-10-18)
  FONT_TXT.CGB(무압축 4bpp, VRAM 0x74000) 타일 0x124~0x147 = 12×3칸(96×24), 맵은 코드가 씀(팔레트 D).
  색: c 빨강 · b 진빨강(오른쪽·아래 가장자리) · 5 남색 그림자 · 1/d 주황·남색 사선 띠(대각 x+y 줄무늬, 주기 13).
  출력: work/out/FONT_TXT.CGB · work/out/TOFF/FONT_TXT.CGB(같은 파일 두 벌) · 미리보기 work/title/taiki_prev.png(원본|새것)
  python tools/taiki_kr.py [preview|build]
"""
import collections
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
T0, NT, TW = 0x124, 36, 12
TEXT = '대기 중'
FILES = ['FONT_TXT.CGB', 'TOFF/FONT_TXT.CGB']
STATE = 'tok2'                                   # 사용자 스테이트(2026-10-18 15:43) — 팔레트 D


def tiles_to_img(f):
    w = np.zeros((24, 96), int)
    for k in range(NT):
        a = np.frombuffer(f[(T0 + k) * 32:(T0 + k) * 32 + 32], np.uint8)
        r, x = divmod(k, TW); w[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return w


def img_to_tiles(w):
    out = b''
    for k in range(NT):
        r, x = divmod(k, TW); blk = w[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
        out += bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
    return out


def background(w):
    # 띠 줄무늬: 보이는 1/d 의 대각선(x+y) 다수결, 안 보이는 대각선은 «1 줄 시작» 목록으로
    D = collections.defaultdict(collections.Counter)
    for y in range(7, 16):
        for x in range(96):
            if w[y, x] in (1, 13):
                D[x + y][w[y, x]] += 1
    starts = [16, 29, 43, 56, 69, 82, 95]
    def stripe(s):
        if D[s]:
            return D[s].most_common(1)[0][0]
        return 1 if any(st <= s < st + 7 for st in starts) or s == 36 else 13
    bg = np.zeros_like(w)
    # 띠 오른쪽 끝 R(y): 원본 1/d 마지막 자리(글자에 안 가린 오른쪽 끝)
    for y in range(7, 16):
        xs = [x for x in range(96) if w[y, x] in (1, 13)]
        R = max(xs)
        for x in range(3, R + 1):
            bg[y, x] = stripe(x + y)
        for x in range(R + 1, 94):
            if w[y, x] == 5 or x > 82:
                bg[y, x] = 5 if w[y, x] == 5 else 0
    for y in (16, 17):
        for x in range(5, 94):
            bg[y, x] = 5
    # 글자 영역 밖(왼쪽 x<13 · 오른쪽 x>=84)은 원본 그대로
    bg[:, :13] = w[:, :13]; bg[:, 84:] = w[:, 84:]
    return bg


def glyph_mask(w=68, h=23):
    # 큰 크기로 그려 상자(68×23)에 맞춰 줄인 뒤 가로 2px 굵게(원본 붓글씨 굵기)
    f = ImageFont.truetype(FONT, 160); f.set_variation_by_name(b'Black')
    im = Image.new('L', (900, 300)); ImageDraw.Draw(im).text((20, 20), TEXT, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 110)
    im = Image.fromarray(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]).resize((w - 2, h), Image.LANCZOS)
    g = np.array(im) > 90
    g2 = np.zeros((h, w), bool)
    for d in range(3):
        g2[:, d:d + w - 2] |= g
    return g2


def render(w):
    g = glyph_mask()
    gh, gw = g.shape
    M = np.zeros((24, 96), bool)
    ox = 13 + (70 - gw) // 2 - 1; oy = 0
    M[oy:oy + gh, ox:ox + gw] = g
    new = background(w)
    sh = np.zeros_like(M)
    for dx, dy in ((1, 0), (2, 0), (3, 0), (2, 1), (3, 1)):
        s = np.zeros_like(M); s[dy:, dx:] = M[:24 - dy, :96 - dx]; sh |= s
    new[sh & ~M] = 5
    edge = M & ~(np.roll(M, -1, 1) & np.roll(M, -1, 0))
    new[M] = 12; new[edge] = 11
    return new


def cram():
    c = open(os.path.join(ROOT, 'work', 'mem', STATE, 'CRAM.bin'), 'rb').read()
    c = bytes(b for i in range(0, len(c), 2) for b in (c[i + 1], c[i]))
    P = np.frombuffer(c, '>u2').astype(int)[0x6D * 16:0x6D * 16 + 16]   # 보조 팔레트 6(PNCN 0xC0CC) · 맵 팔레트 D
    return np.stack([(P & 31) << 3, ((P >> 5) & 31) << 3, ((P >> 10) & 31) << 3], -1).astype(np.uint8)


def main():
    act = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    src = open(os.path.join(ROOT, 'work', 'disc', FILES[0]), 'rb').read()
    w = tiles_to_img(src); new = render(w)
    P = cram(); gap = np.zeros((24, 4, 3), np.uint8) + 60
    a = np.concatenate([P[w], gap, P[new]], 1)
    Image.fromarray(a).resize((a.shape[1] * 6, a.shape[0] * 6), Image.NEAREST).save(os.path.join(ROOT, 'work', 'title', 'taiki_prev.png'))
    print('미리보기 work/title/taiki_prev.png')
    if act == 'build':
        nb = img_to_tiles(new)
        for fp in FILES:
            o = open(os.path.join(ROOT, 'work', 'disc', fp), 'rb').read()
            assert o == src
            d = bytearray(o); d[T0 * 32:T0 * 32 + NT * 32] = nb
            p = os.path.join(ROOT, 'work', 'out', fp); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(bytes(d)); print('→', p)


if __name__ == '__main__':
    main()
