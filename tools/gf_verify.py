# -*- coding: utf-8 -*-
r"""GF 리소스 ↔ 파일 확정: 스테이트마다 VRAM 목적지(인수×0x10)에 «풀린 결과가 그대로 있는» 경우만 인정 (2026-10-17)
  python tools/gf_verify.py   → work/gf_map.tsv (스테이트·리소스 주소·파일·파일 위치·풀린 크기·VRAM)
  후보 파일 = 적재 주소(work/loadbase.json)가 리소스 주소를 덮는 파일 전부 + 스테이트 RAM 에서 그 자리 바이트가 같은 파일.
"""
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
from gf_dump import records, tiles_png  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')


def main():
    files = {}
    for r, _, fs in os.walk(DISC):
        for f in fs:
            p = os.path.join(r, f)
            files[os.path.relpath(p, DISC).replace(os.sep, '/')] = open(p, 'rb').read()
    recs = records()
    found = {}
    for sd in sorted(glob.glob(os.path.join(ROOT, 'work', 'mem', 's*'))):
        st = os.path.basename(sd)
        if not os.path.exists(os.path.join(sd, 'VDP2_VRAM.bin')) or st == 's4x':
            continue
        V = open(os.path.join(sd, 'VDP2_VRAM.bin'), 'rb').read()
        L = open(os.path.join(sd, 'WorkRAML.bin'), 'rb').read()
        for a, p in recs:
            if p in found:
                continue
            o = p - 0x200000
            probe = L[o:o + 24]
            if len(set(probe)) < 4:
                continue
            for k, d in files.items():                 # 스테이트 RAM 의 그 자리 바이트가 들어 있는 파일
                i = d.find(probe)
                while i >= 0:
                    try:
                        out, end = sglz.decode(d, i)
                    except IndexError:
                        out = b''
                    dst = a * 0x10
                    if len(out) >= 32 and V[dst:dst + len(out)] == out:
                        found[p] = (st, k, i, len(out), dst)
                        break
                    if len(out) >= 256:                 # 목적지를 인수(R6)로 따로 주는 호출 — VRAM 어디든 통째로 있으면
                        j = V.find(out)
                        if j >= 0:
                            found[p] = (st, k, i, len(out), j)
                            break
                    i = d.find(probe, i + 1)
                if p in found:
                    break
    os.makedirs(os.path.join(ROOT, 'work', 'gf'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'gf_map.tsv'), 'w', encoding='utf-8') as f:
        f.write('리소스주소\t스테이트\t파일\t파일위치\t풀린크기\tVRAM\n')
        for a, p in recs:
            if p in found:
                st, k, i, n, dst = found[p]
                f.write('%06X\t%s\t%s\t%05X\t%d\t%05X\n' % (p, st, k, i, n, dst))
                out, _ = sglz.decode(files[k], i)
                tiles_png(out, os.path.join(ROOT, 'work', 'gf', 'ok_%s_%05X.png' % (os.path.basename(k).split('.')[0], i)))
                print('%06X  %-4s %-22s 0x%05X  %6d B → VRAM 0x%05X' % (p, st, k, i, n, dst))
    print('확정 %d / %d' % (len(found), len(recs)))


if __name__ == '__main__':
    main()
