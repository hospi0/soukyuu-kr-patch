# -*- coding: utf-8 -*-
r"""이어하기 한글 미리보기(실제 화면 합성) — 스테이트 s14 의 NBG3 맵에서 화면 행↔파일 맵 행을 맞춰 새 맵·새 타일로 갈아 그린 뒤,
  스크린샷(work/shots/14.png)을 원본 글자층과 가장 잘 겹치는 배율·위치로 맞춰 그 위에 합성 (2026-10-17)
  python tools/cont_preview.py [X=B]  → work/cont/screen_<X>.png (원본 스크린샷 | 새 글자 합성)
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cont_kr as C  # noqa: E402
import pm_detail as P  # noqa: E402


def main():
    X = sys.argv[1] if len(sys.argv) > 1 else 'B'
    m, t, comp, rep = C.rebuild(X); print(rep)
    d, go, end, tiles, ents = C.load(X); newents = struct.unpack('>%dH' % (len(m) // 2), m)
    V = open(os.path.join(ROOT, 'work', 'mem', 's14', 'VDP2_VRAM.bin'), 'rb').read()
    vm = list(struct.unpack_from('>4096H', V, 0x72000))
    rowmap = {}
    for vr in range(32):
        row = tuple(vm[vr * 64:vr * 64 + 64])
        if not any(v not in (0, 0xEC00) for v in row):
            continue
        for fr in range(len(ents) // 64):
            if tuple(ents[fr * 64:fr * 64 + 64]) == row:
                rowmap[vr] = fr; break
    c = P.cram_of('s14')
    rgb = lambda e: np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)

    def render(vmap, tb):
        v = bytearray(V); v[0x78000:0x78000 + len(tb)] = tb
        out = np.zeros((240, 352, 3), np.uint8); a = np.zeros((240, 352), bool)
        for r in range(30):
            for x in range(44):
                e = vmap[r * 64 + x]; o = ((e & 0xFFF) | 0x3000) * 0x20
                b = np.frombuffer(bytes(v[o:o + 32]), np.uint8); px = np.stack([b >> 4, b & 15], 1).ravel().reshape(8, 8).astype(int)
                out[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = rgb(c[((0x60 + (e >> 12)) * 16 + px) & 0x7FF]); a[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = px > 0
        return out, a
    newvm = list(vm)
    for vr, fr in rowmap.items():
        newvm[vr * 64:vr * 64 + 64] = newents[fr * 64:fr * 64 + 64]
    o1, a1 = render(vm, tiles); o2, a2 = render(newvm, t)
    shot0 = Image.open(os.path.join(ROOT, 'work', 'shots', '14.png')).convert('RGB')
    best = None
    for H in range(200, 281, 2):
        s = np.array(shot0.resize((352, H), Image.LANCZOS)).astype(int)
        for dy in range(-24, 25):
            y0, y1 = max(0, dy), min(240, H + dy)
            seg = s[y0 - dy:y1 - dy]; aa = a1[y0:y1]
            sc = np.abs(seg[aa] - o1[y0:y1][aa]).mean()
            if best is None or sc < best[0]:
                best = (sc, H, dy)
    sc, H, dy = best; print('스크린샷 맞춤 높이 %d 위치 %+d (차 %.1f)' % (H, dy, sc))
    s = np.array(shot0.resize((352, H), Image.LANCZOS))
    shot = np.zeros((240, 352, 3), np.uint8); y0, y1 = max(0, dy), min(240, H + dy); shot[y0:y1] = s[y0 - dy:y1 - dy]
    bg = shot.copy()
    # 원래 글자 화소는 주변 배경색(위아래 3px 평균)으로 메워 지움
    # 미리보기 전용: 스크린샷의 원래 글자(번짐 4px 포함) 자리를 크게 흐린 배경으로 덮음 — 글자 흔적이 새 글자와 섞여 보이지 않게
    from PIL import ImageFilter
    m = a1.copy()
    for _ in range(4):
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    blur = np.array(Image.fromarray(shot).filter(ImageFilter.GaussianBlur(8)))
    bg = shot.copy(); bg[m] = blur[m]
    new = bg.copy(); new[a2] = o2[a2]
    sep = np.zeros((240, 6, 3), np.uint8) + 128
    p = os.path.join(ROOT, 'work', 'cont', 'screen_%s_v3.png' % X)
    Image.fromarray(np.concatenate([shot, sep, new], 1)).resize((710 * 2, 480), Image.NEAREST).save(p); print(p)


if __name__ == '__main__':
    main()
