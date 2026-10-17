# -*- coding: utf-8 -*-
r"""스테이트의 NBG 층이 쓰는 그림(VRAM) → 출처 파일 찾기 (2026-10-17)
  1) 디스크 파일 평문(무압축 CGB 등)  2) MAP.BIN 의 GF 리소스를 모든 적재 후보 파일에서 푼 결과
  python tools/layer_src.py s6 [s7 ...]     (층 = 켜진 NBG 전부, 칸 범위를 0x800 조각으로 검사)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import vdp2render as vr  # noqa: E402
from gf_dump import records  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')


def load_files():
    files = {}
    for r, _, fs in os.walk(DISC):
        for f in fs:
            p = os.path.join(r, f); files[os.path.relpath(p, DISC).replace(os.sep, '/')] = open(p, 'rb').read()
    return files


def gf_outputs(files):
    """GF 리소스 = 파일마다 앞 목차(8B 항목) + MAP.BIN 표 주소를 모든 파일·모든 적재 후보로 시도 → (이름, 위치, 풀린 결과)"""
    outs = []
    seen = set()
    for k, d in files.items():                          # 파일 앞 목차형(PMENU.BIN 등): [종류][u16][LWRAM 주소]
        i = 0
        while i + 8 <= len(d) and d[i:i + 2] in (b'GF', b'GP', b'BD', b'CD', b'CP'):
            t, a, p = struct.unpack_from('>2sHI', d, i); i += 8
            if t != b'GF':
                continue
            for base in (0x200000, 0x25A800, 0x25D300, 0x21A200, 0x2BDD00):
                off = p - base
                if 0 <= off < len(d) and (k, off) not in seen:
                    try:
                        o, _ = sglz.decode(d, off)
                    except IndexError:
                        continue
                    if len(o) >= 256:
                        seen.add((k, off)); outs.append((k, off, o))
    import json
    lb = json.load(open(os.path.join(ROOT, 'work', 'loadbase.json'), encoding='utf-8'))
    for a, p in records():
        for k, base in lb.items():
            d = files.get(k)
            if d is None or not base <= p < base + len(d) or (k, p - base) in seen:
                continue
            try:
                o, _ = sglz.decode(d, p - base)
            except IndexError:
                continue
            if len(o) >= 256:
                seen.add((k, p - base)); outs.append((k, p - base, o))
    return outs


def main():
    files = load_files()
    gfs = gf_outputs(files)
    print('GF 후보 %d개' % len(gfs))
    for st in sys.argv[1:]:
        V = open(os.path.join(ROOT, 'work', 'mem', st, 'VDP2_VRAM.bin'), 'rb').read()
        for n in range(4):
            im, I = vr.render(st, n)
            if not I['on'] or 'cells' not in I:
                continue
            used = sorted(set(int(x) for x in I['cells'].ravel() if x))
            if not used:
                continue
            unit = 0x20
            lo = used[0] * unit; hi = min(len(V), (used[-1] + 16) * unit)
            print('== %s NBG%d %d색  VRAM %05X..%05X' % (st, n, I['colors'], lo, hi))
            last = None
            for a in range(lo & ~0x7FF, hi, 0x800):
                blk = V[a:a + 64]
                if len(set(blk)) < 4:
                    continue
                src = None
                for k, d in files.items():
                    i = d.find(blk)
                    if i >= 0:
                        src = '평문 %s 0x%X' % (k, i); break
                if not src:
                    for k, off, o in gfs:
                        i = o.find(blk)
                        if i >= 0:
                            src = 'GF %s 0x%X (+0x%X)' % (k, off, i); break
                src = src or '-'
                if src.split(' 0x')[0] != last:
                    print('  %05X %s' % (a, src)); last = src.split(' 0x')[0]


if __name__ == '__main__':
    main()
