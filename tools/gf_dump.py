# -*- coding: utf-8 -*-
r"""MAP.BIN 의 GF 리소스 전부 → 적재 주소(work/loadbase.json)로 파일·위치를 찾아 풀고 4bpp 타일 그림(회색)으로 뽑기 (2026-10-17)
  python tools/gf_dump.py   → work/gf/<파일>_<위치>.png + 목록 출력
"""
import json
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')


def records():
    m = open(os.path.join(DISC, 'MAP.BIN'), 'rb').read()
    out, seen = [], set()
    for mt in re.finditer(rb'(?=(GF))', m):
        i = mt.start(); _, a, p = struct.unpack_from('>2sHI', m, i)
        if 0x200000 <= p < 0x300000 and p not in seen:
            seen.add(p); out.append((a, p))
    return out


def tiles_png(data, path, cols=32):
    n = len(data) // 32; r = max(1, (n + cols - 1) // cols)
    img = np.zeros((r * 8, cols * 8), np.uint8)
    for t in range(n):
        tt = np.frombuffer(data[t * 32:t * 32 + 32], np.uint8)
        px = np.empty(64, np.uint8); px[0::2] = tt >> 4; px[1::2] = tt & 15
        img[t // cols * 8:t // cols * 8 + 8, t % cols * 8:t % cols * 8 + 8] = px.reshape(8, 8) * 17
    Image.fromarray(img).resize((img.shape[1] * 2, img.shape[0] * 2), 0).save(path)


def main():
    base = json.load(open(os.path.join(ROOT, 'work', 'loadbase.json'), encoding='utf-8'))
    base = {k.replace('\\', '/'): v for k, v in base.items() if v >= 0x200000 and v < 0x300000}
    size = {k: os.path.getsize(os.path.join(DISC, k)) for k in base}
    os.makedirs(os.path.join(ROOT, 'work', 'gf'), exist_ok=True)
    for a, p in records():
        hit = [k for k, b in base.items() if b <= p < b + size[k]]
        best = None
        for k in hit:                                   # 같은 주소에 실리는 파일이 여럿 — 정상으로 풀리는 것
            off = p - base[k]; d = open(os.path.join(DISC, k), 'rb').read()
            try:
                out, end = sglz.decode(d, off)
            except IndexError:
                continue
            if len(out) >= 64 and end <= len(d) and (best is None or len(out) > len(best[2])):
                best = (k, off, out)
        if not best:
            print('%06X  %s' % (p, ('해제되는 후보 없음 ' + ','.join(hit)) if hit else '파일 미상')); continue
        k, off, out = best
        nm = os.path.join(ROOT, 'work', 'gf', '%s_%05X.png' % (os.path.basename(k).split('.')[0], off))
        tiles_png(out, nm)
        print('%06X  %-22s 0x%05X  풀린 %6d  VRAM 0x%05X  %s' % (p, k, off, len(out), a * 0x10, os.path.basename(nm)))


if __name__ == '__main__':
    main()
