# -*- coding: utf-8 -*-
r"""이름 입력 화면 «特別賞与» → «특별 상여», «位» → «위» (2026-10-18)
  RANK_DAT.BIN GF 0x1B160(→VRAM 0x60000) 의 타일을 제자리에서 다시 그림 — 칸은 코드가 놓음(NBG3).
    特別賞与 = 3×12칸, 타일 0x641~0x663 줄 순서(0x641~0x64C / 0x64D~0x658 / 0x659~0x661·[0x640 공유 칸 — 손대지 않음]·0x662·0x663)
    位       = 4×4칸, 타일 0x620~0x62F 줄 순서
  색 번호: 1 채움 · 6 오른쪽 아래 가장자리 · 9 바깥 테두리(원본 붓글씨 꼴). 새 압축 ≤ 원래 길이.
  python tools/name_kr.py [preview|build] → 미리보기 work/spr/name_prev.png(원본|새것)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

FP, OFF = 'RANK_DAT.BIN', 0x1B160
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
TOKU = [list(range(0x641, 0x64D)), list(range(0x64D, 0x659)), list(range(0x659, 0x662)) + [None, 0x662, 0x663]]
I = [list(range(0x620 + 4 * r, 0x624 + 4 * r)) for r in range(4)]


def grid(t, g):
    out = np.zeros((len(g) * 8, len(g[0]) * 8), int)
    for r, row in enumerate(g):
        for c, ti in enumerate(row):
            if ti is None:
                continue
            a = np.frombuffer(t[ti * 32:ti * 32 + 32], np.uint8).astype(int)
            out[r * 8:r * 8 + 8, c * 8:c * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return out


def put(t, g, img):
    t = bytearray(t)
    for r, row in enumerate(g):
        for c, ti in enumerate(row):
            if ti is None:
                continue
            blk = img[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            t[ti * 32:ti * 32 + 32] = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
    return bytes(t)


def draw(text, w, h, forbid=None):
    f = ImageFont.truetype(FONT, 200); f.set_variation_by_name(b'Black')
    im = Image.new('L', (1200, 300)); ImageDraw.Draw(im).text((20, 20), text, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 110); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    M = np.zeros((h, w), bool)
    gw, gh = w - 4, h - 4
    M[1:1 + gh, 1:1 + gw] = np.array(Image.fromarray(a).resize((gw, gh), Image.LANCZOS)) > 100
    if forbid is not None:
        M &= ~forbid
    dil = M.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            dil |= np.roll(np.roll(M, dy, 0), dx, 1)
    if forbid is not None:
        dil &= ~forbid
    out = np.zeros((h, w), int)
    out[dil] = 9; out[M] = 1
    edge = M & ~(np.roll(M, -1, 1) & np.roll(M, -1, 0))
    out[edge] = 6
    return out


def main():
    act = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    src = os.path.join(ROOT, 'work', 'out', FP)
    d = bytearray(open(src if os.path.exists(src) else os.path.join(ROOT, 'work', 'disc', FP), 'rb').read())
    orig = open(os.path.join(ROOT, 'work', 'disc', FP), 'rb').read()
    t0, oend = sglz.decode(orig, OFF)
    t, _ = sglz.decode(bytes(d), OFF)
    assert t[0x620 * 32:0x664 * 32] == t0[0x620 * 32:0x664 * 32] or act == 'build', '다른 도구가 이 타일을 바꿈'
    forbid = np.zeros((24, 96), bool); forbid[16:24, 72:80] = True        # 0x640 공유 칸(3행 10열)
    a_new = draw('특별 상여', 96, 24, forbid); b_new = draw('위', 32, 32)
    a_old = grid(t0, TOKU); b_old = grid(t0, I)
    nt = put(put(t, TOKU, a_new), I, b_new)
    comp = sglz.encode(nt); assert sglz.decode(comp, 0)[0] == nt
    print('압축', len(comp), '/', oend - OFF)
    cr = open(os.path.join(ROOT, 'work', 'mem', 'name1', 'CRAM.bin'), 'rb').read()
    cr = bytes(x for i in range(0, len(cr), 2) for x in (cr[i + 1], cr[i])); P = np.frombuffer(cr, '>u2').astype(int)
    def col(g, pn):
        c = P[(0x60 + pn) * 16 + g]; o = np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], -1).astype(np.uint8)
        o[g == 0] = (30, 30, 50); return o
    A = np.concatenate([col(a_old, 0), np.full((24, 4, 3), 120, np.uint8), col(a_new, 0)], 1)
    B = np.concatenate([col(b_old, 2), np.full((32, 4, 3), 120, np.uint8), col(b_new, 2)], 1)
    W = max(A.shape[1], B.shape[1])
    im = np.concatenate([np.pad(A, ((0, 4), (0, W - A.shape[1]), (0, 0))), np.pad(B, ((0, 0), (0, W - B.shape[1]), (0, 0)))], 0)
    Image.fromarray(im).resize((im.shape[1] * 5, im.shape[0] * 5), Image.NEAREST).save(os.path.join(ROOT, 'work', 'spr', 'name_prev.png'))
    if act == 'build':
        assert len(comp) <= oend - OFF
        d[OFF:OFF + len(comp)] = comp
        open(src, 'wb').write(bytes(d)); print('→', src)


if __name__ == '__main__':
    main()
