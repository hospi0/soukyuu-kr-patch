# -*- coding: utf-8 -*-
r"""작전 실패 화면 «作戦失敗» → «작전 실패» (2026-10-18)
  G_OVR.BIN(적재 0x200000) 머리 표 34항목 8B = ['CP'][u16 0x1540][포인터 u32] → sglz 스트림, 풀면 168×64 8bpp(VDP1 색모드 4, CRAM 0번부터).
  34장 = 作戦失敗 → 세로로 늘어나며 GAME OVER 로 바뀌는 변형 애니메이션.
  새 그림: 0번 = 한글(원본 잉크 세로 범위 12‥51 에 맞춤) · 색 = «그 장 원본»의 줄(y)·가장자리 종류별 최다 색 번호.
          1‥BLEND0-1번 = 한글을 원본 장의 세로 범위만큼 늘인 잔상 겹침 · BLEND0‥BLEND1 = 원본과 점무늬 섞기 · 그 뒤 원본 그대로.
  압축 = 항목 자리(다음 포인터까지) 안. 포인터 그대로.
  python tools/fail_kr.py [preview|build] → work/spr/fail_prev.png(원본|새것 실제 색) · fail_prev.gif
"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

FP, BASE, N, W, H = 'G_OVR.BIN', 0x200000, 34, 168, 64
TEXT = ('작전', '실패')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
Y0, Y1 = 12, 51                     # 원본 0번 잉크 세로 범위
X0, X1, GAP = 2, 165, 6
BLEND0, BLEND1 = 16, 21             # 이 범위에서 원본으로 점점 넘어감


def frames(d):
    out = []
    for i in range(N):
        _, _, p = struct.unpack('>2sHI', d[i * 8:i * 8 + 8])
        t, e = sglz.decode(d, p - BASE, 1 << 20)
        out.append((p - BASE, e, np.frombuffer(t[:W * H], np.uint8).reshape(H, W).astype(int), t))
    return out


def word_mask(txt, w, h):
    f = ImageFont.truetype(FONT, 220); f.set_variation_by_name(b'Black')
    im = Image.new('L', (900, 320)); ImageDraw.Draw(im).text((20, 20), txt, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 110); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.array(Image.fromarray(a).resize((w, h), Image.LANCZOS)) > 110


def korean():
    M = np.zeros((H, W), bool)
    ww = (X1 - X0 + 1 - GAP) // 2
    M[Y0:Y1 + 1, X0:X0 + ww] = word_mask(TEXT[0], ww, Y1 - Y0 + 1)
    M[Y0:Y1 + 1, X1 + 1 - ww:X1 + 1] = word_mask(TEXT[1], ww, Y1 - Y0 + 1)
    B = M | np.roll(M, 1, 1)                 # 원본 붓글씨 굵기 — 오른쪽·아래로 1화소
    B[Y0 + 1:Y1 + 1] |= M[Y0:Y1]
    return B


def classes(M):
    up = np.roll(M, 1, 0); dn = np.roll(M, -1, 0); lf = np.roll(M, 1, 1); rt = np.roll(M, -1, 1)
    c = np.zeros(M.shape, int)              # 0 안쪽
    c[M & ~rt] = 4; c[M & ~lf] = 3; c[M & ~dn] = 2; c[M & ~up] = 1
    return c


def colour_table(f):
    """그 장 원본: 줄(y)·종류 → 최다 색 번호(검정 255 제외)"""
    M = (f > 0) & (f != 255); C = classes(f > 0)
    tab = {}
    rows = {}
    for y in range(H):
        for k in range(5):
            v = f[y][M[y] & (C[y] == k)]
            if len(v):
                tab[(y, k)] = int(np.bincount(v).argmax())
        v = f[y][M[y]]
        if len(v):
            rows[y] = int(np.bincount(v).argmax())
    return tab, rows


def paint(S, f):
    tab, rows = colour_table(f)
    ry = sorted(rows)
    C = classes(S); out = np.zeros((H, W), int)
    for y, x in zip(*np.nonzero(S)):
        k = C[y, x]
        v = tab.get((y, k))
        if v is None:
            yy = min(ry, key=lambda q: abs(q - y)); v = tab.get((yy, k), rows[yy])
        out[y, x] = v
    return out


def stretch(K, f):
    ys = np.nonzero(f)[0]; c = (Y0 + Y1) / 2
    s = max((c - ys.min()) / (c - Y0), (ys.max() - c) / (Y1 - c))
    S = K.copy()
    for sc in np.linspace(1, s, 6)[1:]:
        yy = np.arange(H); src = np.round(c + (yy - c) / sc).astype(int)
        ok = (src >= 0) & (src < H)
        L = np.zeros_like(K); L[ok] = K[src[ok]]; S |= L
    return S


def make(F):
    K = korean()
    news = []
    rng = np.random.RandomState(7); noise = np.repeat(rng.rand(H, 1), W, 1)      # 줄 단위(점무늬는 압축 초과)
    for i, (_, _, f, _) in enumerate(F):
        if i >= BLEND1:
            news.append(f.copy()); continue
        g = paint(stretch(K, f) if i else K, f)
        if i >= BLEND0:
            a = (i - BLEND0 + 1) / (BLEND1 - BLEND0 + 1)
            g = np.where(noise < a, f, g)
        news.append(g)
    return news


def pal():
    cr = open(os.path.join(ROOT, 'work', 'mem', 'dg2', 'CRAM.bin'), 'rb').read()
    cr = bytes(x for i in range(0, len(cr), 2) for x in (cr[i + 1], cr[i])); return np.frombuffer(cr, '>u2').astype(int)


def rgb(P, f):
    c = P[f]; o = np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], -1).astype(np.uint8)
    o[f == 0] = (30, 30, 50); return o


def main():
    act = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    src = os.path.join(ROOT, 'work', 'disc', FP)
    d = open(src, 'rb').read()
    F = frames(d); news = make(F)
    out = bytearray(d); sizes = []
    for i, ((o, e, f, t), g) in enumerate(zip(F, news)):
        if (g == f).all():
            continue
        nt = bytes(g.astype(np.uint8).ravel()) + t[W * H:]
        comp = sglz.encode(nt); assert sglz.decode(comp, 0)[0] == nt
        slot = (F[i + 1][0] if i + 1 < N else e) - o
        sizes.append((i, len(comp), slot))
        if len(comp) > slot:
            raise SystemExit('%d번 압축 초과 %d > %d' % (i, len(comp), slot))
        out[o:o + len(comp)] = comp
    print('바뀐 장', len(sizes), '최대 사용률 %.2f' % max(a / b for _, a, b in sizes))
    P = pal()
    rows = [np.concatenate([rgb(P, f), np.full((H, 4, 3), 120, np.uint8), rgb(P, g)], 1) for (_, _, f, _), g in zip(F, news)]
    sheet = np.concatenate([np.concatenate(rows[r:r + 2] + [np.zeros((H, 340, 3), np.uint8)] * (2 - len(rows[r:r + 2])), 1)
                            for r in range(0, N, 2)], 0)
    Image.fromarray(sheet).resize((sheet.shape[1] * 2, sheet.shape[0] * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'spr', 'fail_prev.png'))
    gif = [Image.fromarray(np.concatenate([rgb(P, f), rgb(P, g)], 0)).resize((W * 3, H * 6), Image.NEAREST) for (_, _, f, _), g in zip(F, news)]
    gif[0].save(os.path.join(ROOT, 'work', 'spr', 'fail_prev.gif'), save_all=True, append_images=[gif[0]] * 20 + gif[1:] + [gif[-1]] * 20, duration=66, loop=0)
    if act == 'build':
        p = os.path.join(ROOT, 'work', 'out', FP); open(p, 'wb').write(bytes(out)); print('→', p)


if __name__ == '__main__':
    main()
