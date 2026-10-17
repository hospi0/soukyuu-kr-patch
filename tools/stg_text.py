# -*- coding: utf-8 -*-
r"""게임 안 문구(NBG3) 미리보기 — 스테이지 맵 파일(SS_ST?.BIN, 머리 4 B 뒤 64칸×N줄)을 통째로 길게 렌더 (2026-10-17)
  칸 번호 = (v & 0xFFF) | 0x3000 → VRAM 번호×0x20. VRAM 구성: 0x74000 FONT_TXT.CGB · 0x75000 SS_TX_AB.CGB · 0x78000 <문장 그림>.
  python tools/stg_text.py <맵 파일> <문장 그림 파일(.CGB 또는 파일:GF위치hex)> <출력.png>
  흑백(읽기용): 화소 값 0 = 바탕, 나머지 = 글자.
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


def vram(sent):
    v = bytearray(0x80000)
    f = open(os.path.join(DISC, 'FONT_TXT.CGB'), 'rb').read(); v[0x74000:0x74000 + len(f)] = f
    s = open(os.path.join(DISC, 'BUP', 'SS_TX_AB.CGB'), 'rb').read(); v[0x75000:0x75000 + min(len(s), 0x3000)] = s[:0x3000]
    v[0x78000:0x78000 + len(sent)] = sent[:0x80000 - 0x78000]
    return bytes(v)


def load_sent(spec):
    if ':' in spec[2:]:
        p, off = spec.rsplit(':', 1)
        return sglz.decode(open(os.path.join(DISC, p), 'rb').read(), int(off, 16))[0]
    return open(os.path.join(DISC, spec), 'rb').read()


def render(mapb, v, w=64):
    n = len(mapb) // (w * 2)
    ents = struct.unpack('>%dH' % (n * w), mapb[:n * w * 2])
    img = np.zeros((n * 8, w * 8), np.uint8)
    for k, e in enumerate(ents):
        if not e or e == 0xFFFF:
            continue
        o = ((e & 0xFFF) | 0x3000) * 0x20
        a = np.frombuffer(v[o:o + 32], np.uint8)
        px = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
        y, x = divmod(k, w)
        img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = np.where(px > 0, 255, 0)
    return img


if __name__ == '__main__':
    m = open(os.path.join(DISC, sys.argv[1]), 'rb').read()[0x04:]   # 머리 4 B 뒤부터 64칸 줄
    img = render(m, vram(load_sent(sys.argv[2])))
    img = np.roll(img, int(sys.argv[4]) * 8 if len(sys.argv) > 4 else 0, 1)   # 화면 가로 스크롤만큼 돌려 맞춤(칸 수)
    Image.fromarray(255 - img).save(sys.argv[3])
