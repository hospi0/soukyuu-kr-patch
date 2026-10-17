# -*- coding: utf-8 -*-
r"""판독용: 그림 글자를 «실제 팔레트 밝기»로 렌더 → 잉크 가로 투영으로 줄을 나눠 줄마다 확대 PNG (2026-10-17)
  python tools/read_lines.py pm <PM 파일> <목차> <줄번호,…|all> [배율=6] [단=L|R|A]
  python tools/read_lines.py stg <SS_ST?.BIN> <문장 그림 spec> <y0> <y1> [배율=6]   (stg_text 렌더의 픽셀 줄 범위)
  출력: work/read/<이름>_<줄>.png
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import pm_detail as P  # noqa: E402
import stg_text as T  # noqa: E402

OUT = os.path.join(ROOT, 'work', 'read')


def lum_from_cram(state):
    c = P.cram_of(state)
    r, g, b = (c & 31), ((c >> 5) & 31), ((c >> 10) & 31)
    return (r * 0.3 + g * 0.59 + b * 0.11) * 255 / 31


def pm_page(fname, k, state='s7'):
    t = P.toc(); d = open(os.path.join(P.DISC, 'PMENU', fname), 'rb').read()
    go = t[k][2] - P.BASE; bo = t[k + 1][2] - P.BASE
    tiles, _ = sglz.decode(d, go); ents = struct.unpack('>%dH' % ((go - bo) // 2), d[bo:go])
    L = lum_from_cram(state)
    img = np.zeros((len(ents) // 64 * 8, 512))
    for i, v in enumerate(ents):
        o = ((v & 0xFFF) | 0x3000) * 0x20 - P.VRAM_TILES
        if not 0 <= o <= len(tiles) - 32:
            continue
        a = np.frombuffer(tiles[o:o + 32], np.uint8); px = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8).astype(int)
        val = np.where(px > 0, L[(((v >> 12) & 15) * 16 + px) & 0x7FF], 0)
        y, x = divmod(i, 64); img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = val
    return img


def split_lines(img, gap=1):
    ink = (img > 40).sum(1) > 0
    lines, y = [], 0
    while y < len(ink):
        if ink[y]:
            y0 = y
            while y < len(ink) and ink[y]:
                y += 1
            if y - y0 >= 6:
                lines.append((y0, y))
        y += 1
    return lines


def save(img, name, scale):
    img = np.clip(img, 0, 255)
    m = img.max() or 1
    im = Image.fromarray((255 - img * 255 / m).astype(np.uint8))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    os.makedirs(OUT, exist_ok=True); im.save(os.path.join(OUT, name))


def main():
    mode = sys.argv[1]
    if mode == 'pm':
        f, k, which = sys.argv[2], int(sys.argv[3]), sys.argv[4]
        scale = int(sys.argv[5]) if len(sys.argv) > 5 else 6
        col = sys.argv[6] if len(sys.argv) > 6 else 'A'
        img = pm_page(f, k)
        xs = np.nonzero((img > 40).sum(0))[0]
        if col in 'LR':
            mid = 256
            img = img[:, :mid] if col == 'L' else img[:, mid:]
        lines = split_lines(img)
        sel = range(1, len(lines) + 1) if which == 'all' else [int(s) for s in which.split(',')]
        for n in sel:
            y0, y1 = lines[n - 1]
            xs = np.nonzero((img[y0:y1] > 40).sum(0))[0]
            save(img[y0 - 1:y1 + 1, max(0, xs[0] - 2):xs[-1] + 3], '%s_%d_%s%d.png' % (f.split('.')[0], k, col, n), scale)
        print('줄 %d개' % len(lines))
    else:
        m = open(os.path.join(T.DISC, sys.argv[2]), 'rb').read()[4:]
        sent = T.load_sent(sys.argv[3]); v = T.vram(sent)
        y0, y1 = int(sys.argv[4]), int(sys.argv[5]); scale = int(sys.argv[6]) if len(sys.argv) > 6 else 6
        n = len(m) // 128; ents = struct.unpack('>%dH' % (n * 64), m[:n * 128])
        img = np.zeros((n * 8, 512))
        for i, e in enumerate(ents):
            if not e or e == 0xFFFF:
                continue
            o = ((e & 0xFFF) | 0x3000) * 0x20
            a = np.frombuffer(v[o:o + 32], np.uint8); px = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
            y, x = divmod(i, 64); img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = px * 17
        save(img[y0:y1], '%s_%d.png' % (os.path.basename(sys.argv[2]).split('.')[0], y0), scale)


if __name__ == '__main__':
    main()


def pm_chunks(fname, k, line, col='A', per=6, scale=10):
    """상세 본문 한 줄을 실제 팔레트 밝기로 per 글자씩 잘라 확대 저장 → 파일 이름 목록"""
    img = pm_page(fname, k)
    if col in 'LR':
        img = img[:, :256] if col == 'L' else img[:, 256:]
    y0, y1 = split_lines(img)[line - 1]
    xs = np.nonzero((img[y0:y1] > 40).sum(0))[0]
    seg = img[y0 - 1:y1 + 1, xs[0]:xs[-1] + 1]
    out = []
    step = 12 * per
    for i, x in enumerate(range(0, seg.shape[1], step)):
        c = seg[:, x:x + step + 4]
        im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).resize((c.shape[1] * scale, c.shape[0] * scale), Image.NEAREST)
        p = os.path.join(OUT, '%s_%d_%s%d_c%d.png' % (fname.split('.')[0], k, col, line, i)); im.save(p); out.append(p)
    return out


def pm_stack(fname, k, line, col='A', scale=8):
    """한 줄을 반으로 접어 위아래로 쌓은 한 장(실제 팔레트 밝기)"""
    img = pm_page(fname, k)
    if col in 'LR':
        img = img[:, :256] if col == 'L' else img[:, 256:]
    y0, y1 = split_lines(img)[line - 1]
    xs = np.nonzero((img[y0:y1] > 40).sum(0))[0]
    seg = img[y0 - 1:y1 + 1, xs[0]:xs[-1] + 1]
    h = (seg.shape[1] + 1) // 2
    a = np.zeros((seg.shape[0] * 2 + 3, h)); a[:seg.shape[0]] = seg[:, :h]; a[seg.shape[0] + 3:, :seg.shape[1] - h] = seg[:, h:]
    p = os.path.join(OUT, 'S_%s_%d_%s%d.png' % (fname.split('.')[0], k, col, line))
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST).save(p)
    return p
