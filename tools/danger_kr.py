# -*- coding: utf-8 -*-
r"""6스테이지 보스 경고 «危険» → «위험» (2026-10-18)
  VDP1 스프라이트 72×56 4bpp(색뱅크 0xE0) = STG_L/PREL_DAT.BIN 0x28DBC 압축(sglz, 원래 803 B) — 다른 스테이지엔 없음.
  0~21행 = 줄무늬 삼각형(그대로) · 22~51행 = 글자: 7 노랑 채움 · 6 안쪽 가장자리 · 1 검은 테.
  새 압축 ≤ 원래 길이. 출력 work/out/STG_L/PREL_DAT.BIN 에 합침 · 미리보기 work/spr/danger_prev.png(원본|새것)
  python tools/danger_kr.py [preview|build]
"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

FP, OFF, W, H = 'STG_L/PREL_DAT.BIN', 0x28DBC, 72, 56
TEXT = '위험'
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
Y0, Y1, X0, X1 = 22, 52, 5, 67                    # 글자 칸(원본 잉크 범위)


OFF2 = 0x290E0


def load_at(off):
    d = open(os.path.join(ROOT, 'work', 'disc', FP), 'rb').read()
    s, e = sglz.decode(d, off)
    a = np.frombuffer(s, np.uint8)
    return d, e, np.stack([a >> 4, a & 15], 1).ravel().reshape(H, W).astype(int)


def load(root):
    d = open(os.path.join(ROOT, 'work', root, FP), 'rb').read()
    s, e = sglz.decode(d, OFF)
    a = np.frombuffer(s, np.uint8)
    return d, e, np.stack([a >> 4, a & 15], 1).ravel().reshape(H, W).astype(int)


def glyph(w, h):
    f = ImageFont.truetype(FONT, 200); f.set_variation_by_name(b'Black')
    im = Image.new('L', (700, 300)); ImageDraw.Draw(im).text((20, 20), TEXT, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 110)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.array(Image.fromarray(a).resize((w, h), Image.LANCZOS)) > 110


def make(px):
    new = px.copy(); new[Y0:Y1 + 2, :] = 0
    gw, gh = X1 - X0 - 4, Y1 - Y0 - 4
    M = np.zeros((H, W), bool); M[Y0 + 2:Y0 + 2 + gh, X0 + 2:X0 + 1 + gw] = glyph(gw - 1, gh)
    M |= np.roll(M, 1, 1)                                   # 가로 1px 굵게(원본 붓글씨 굵기)
    dil = M.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dil |= np.roll(np.roll(M, dy, 0), dx, 1)
    inner = M & ~np.roll(M, 1, 1)                            # 원본처럼 왼쪽 가장자리만 6
    new[dil] = 1; new[M] = 7; new[inner] = 6
    return new


def tobytes(px):
    return bytes(((px[:, 0::2] << 4) | px[:, 1::2]).astype(np.uint8).ravel())


def cram():
    c = open(os.path.join(ROOT, 'work', 'mem', 'dg1', 'CRAM.bin'), 'rb').read()
    c = bytes(b for i in range(0, len(c), 2) for b in (c[i + 1], c[i]))
    P = np.frombuffer(c, '>u2').astype(int)[0xE0:0xF0]
    return np.stack([(P & 31) << 3, ((P >> 5) & 31) << 3, ((P >> 10) & 31) << 3], -1).astype(np.uint8)


def main():
    act = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    d, e, px = load('disc'); new = make(px)
    P = cram(); bg = np.array([90, 40, 50], np.uint8)
    def col(p):
        a = P[p]; a[p == 0] = bg; return a
    im = np.concatenate([col(px), np.zeros((H, 4, 3), np.uint8) + 200, col(new)], 1)
    Image.fromarray(im).resize((im.shape[1] * 6, H * 6), Image.NEAREST).save(os.path.join(ROOT, 'work', 'spr', 'danger_prev.png'))
    comp = sglz.encode(tobytes(new)); assert sglz.decode(comp, 0)[0] == tobytes(new)
    print('압축', len(comp), '/', e - OFF)
    # 둘째 경고(붉은 판, 0x290E0) = 같은 그림·글자 색만 1→6·7→9·6→8 (0~21행 삼각형은 그대로) — 같은 화면에 둘 다 뜸(2026-10-18 실기)
    d2, e2, px2 = load_at(OFF2)
    new2 = px2.copy(); txt = new[22:, :]
    m2 = txt.copy(); m2[txt == 1] = 6; m2[txt == 7] = 9; m2[txt == 6] = 8
    new2[22:, :] = m2
    comp2 = sglz.encode(tobytes(new2)); assert sglz.decode(comp2, 0)[0] == tobytes(new2)
    print('둘째 압축', len(comp2), '/', e2 - OFF2)
    if act == 'build':
        assert len(comp) <= e - OFF and len(comp2) <= e2 - OFF2
        q = os.path.join(ROOT, 'work', 'out', FP)
        body = bytearray(open(q, 'rb').read() if os.path.exists(q) else d)
        body[OFF:OFF + len(comp)] = comp
        body[OFF2:OFF2 + len(comp2)] = comp2
        os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(bytes(body))
        print('→', q)


if __name__ == '__main__':
    main()
