# -*- coding: utf-8 -*-
r"""특별 시청 NBG3 «作曲» → «작곡» (2026-10-18)
  TOK_PNT GF 0x1C5B0(→VRAM 0x60000). 칸은 코드가 놓음 → 타일 제자리: 4줄 × 5칸, 줄 시작 0x01·0x16·0x2B·0x3F(+0~4).
  작곡가 이름(並木 学·崎元 仁·岩田 匡治·本山 淳弘)은 칸 폭이 한자 폭이라 한글이 안 들어가고(学=2칸), 崎元 仁은 중복 제거로 타일 줄이 밀려 그대로 둠.
  색: 15 채움 · 8 테두리. 압축 ≤ 원래 길이(뒤 0x209C4 는 tok1 덩어리).
  python tools/snd3_kr.py [preview|build]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

FP, OFF = 'TITLE/TOK_PNT.BIN', 0x1C5B0
ROWS = [0x01, 0x16, 0x2B, 0x3F]
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'


def block(t):
    g = np.zeros((32, 40), int)
    for r, s in enumerate(ROWS):
        for c in range(5):
            a = np.frombuffer(t[(s + c) * 32:(s + c) * 32 + 32], np.uint8).astype(int)
            g[r * 8:r * 8 + 8, c * 8:c * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return g


def main():
    act = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    src = os.path.join(ROOT, 'work', 'out', FP)
    d = bytearray(open(src if os.path.exists(src) else os.path.join(ROOT, 'work', 'disc', FP), 'rb').read())
    o = open(os.path.join(ROOT, 'work', 'disc', FP), 'rb').read()
    t0, oend = sglz.decode(o, OFF)
    t = bytearray(sglz.decode(bytes(d), OFF)[0])
    f = ImageFont.truetype(FONT, 200); f.set_variation_by_name(b'Bold')
    im = Image.new('L', (700, 300)); ImageDraw.Draw(im).text((20, 20), '작곡', font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 110); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    M = np.zeros((32, 40), bool); M[2:30, 2:38] = np.array(Image.fromarray(a).resize((36, 28), Image.LANCZOS)) > 100
    dil = M.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dil |= np.roll(np.roll(M, dy, 0), dx, 1)
    new = np.zeros((32, 40), int); new[dil] = 8; new[M] = 15
    for r, s in enumerate(ROWS):
        for c in range(5):
            blk = new[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            t[(s + c) * 32:(s + c) * 32 + 32] = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
    comp = sglz.encode(bytes(t)); assert sglz.decode(comp, 0)[0] == bytes(t)
    print('압축', len(comp), '/', oend - OFF)
    old = block(t0)
    img = np.concatenate([old, np.full((32, 3), 4), new], 1) * 16
    Image.fromarray(img.astype(np.uint8)).resize((img.shape[1] * 6, 32 * 6), Image.NEAREST).save(os.path.join(ROOT, 'work', 'nbg', 'snd3_prev.png'))
    if act == 'build':
        assert len(comp) <= oend - OFF
        d[OFF:OFF + len(comp)] = comp
        open(src, 'wb').write(bytes(d)); print('→', src)


if __name__ == '__main__':
    main()
