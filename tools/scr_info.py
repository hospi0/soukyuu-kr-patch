# -*- coding: utf-8 -*-
r"""스테이트 화면의 NBG 층 → 맵 페이지 출처(파일 평문 검색) · 맵이 가리키는 타일 VRAM 구간별 개수 · 그 구간의 출처(gf_map/평문) (2026-10-17)
  python tools/scr_info.py <스테이트> <층…>
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import vdp2render as vr  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')


def files():
    out = {}
    for r, _, fs in os.walk(DISC):
        for f in fs:
            p = os.path.join(r, f); out[os.path.relpath(p, DISC).replace(os.sep, '/')] = open(p, 'rb').read()
    return out


def main():
    st = sys.argv[1]; F = files()
    V = open(os.path.join(ROOT, 'work', 'mem', st, 'VDP2_VRAM.bin'), 'rb').read()
    for n in map(int, sys.argv[2:]):
        for pl in range(4):
            im, I = vr.render(st, n, plane=pl)
            if 'base' not in I:
                continue
            base = int(I['base'], 16); one = I['one']; chsz = I['chsz']
            ncell = 64 if not chsz else 32; size = ncell * ncell * (2 if one else 4)
            page = V[base:base + size]
            src = [(k, hex(d.find(page))) for k, d in F.items() if d.find(page) >= 0]
            cells = I['cells']
            unit = 4 if (chsz and I['colors'] == 16) else (8 if (chsz and I['colors'] == 256) else 1)
            ranges = collections.Counter((int(c) * 0x20) >> 12 << 12 for c in cells.ravel() if c)
            print('%s NBG%d 면%d 맵 0x%05X %d색 칸%d 출처 %s' % (st, n, pl, base, I['colors'], 16 if chsz else 8, src[:2] or '-'))
            print('     타일 VRAM 4KB 구간별 칸 수:', {hex(k): v for k, v in sorted(ranges.items())})


if __name__ == '__main__':
    main()
