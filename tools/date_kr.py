# -*- coding: utf-8 -*-
r"""출격 전 날짜 줄(2056年10月14日 22時21分)의 한자 글리프 → 년·월·일·시·분 (2026-10-17)
  코드가 맵에 직접 쓰는 4×4 타일(32×32) 글리프 — 출격 전 세트(PRE?_DAT GF) 의 타일 0x7E(年)·0x8F(月)·0x9F(日)·0xAF(時)·0xBF(分) 부터 16장씩, 6스테이지 같은 자리.
  같은 자리에 같은 색 번호(원본 안쪽 최다 = 채움 · 바깥 경계 최다 = 테두리)·같은 잉크 높이로 NotoSerifKR Bold(Black 은 ㅇ이 뭉개짐).
  입력/출력: work/out/STG_?/PRE?_DAT.BIN (없으면 원본에서) — 압축 ≤ 원래 길이 검사. 미리보기 work/stg/date_kr.png
  python tools/date_kr.py
"""
import collections
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import stg_blocks as S  # noqa: E402

GL = [('年', '년', 0x7E), ('月', '월', 0x8F), ('日', '일', 0x9F), ('時', '시', 0xAF), ('分', '분', 0xBF)]
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
OUT = os.path.join(ROOT, 'work', 'out')


def glyph(t, t0):
    g = np.zeros((32, 32), np.uint8)
    for k in range(16):
        o = (t0 + k) * 32; a = np.frombuffer(t[o:o + 32], np.uint8)
        y, x = divmod(k, 4); g[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    return g


def put(t, t0, g):
    t = bytearray(t)
    for k in range(16):
        y, x = divmod(k, 4); blk = g[y * 8:y * 8 + 8, x * 8:x * 8 + 8]
        t[(t0 + k) * 32:(t0 + k) * 32 + 32] = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
    return bytes(t)


def korean(ch, g):
    ink = g > 0; ys, xs = np.nonzero(ink)
    H = ys.max() - ys.min() + 1; W = xs.max() - xs.min() + 1
    pad = np.pad(ink, 1)
    edge_px = ink & ~(pad[2:, 1:-1] & pad[:-2, 1:-1] & pad[1:-1, 2:] & pad[1:-1, :-2])
    fill = collections.Counter(g[ink & ~edge_px]).most_common(1)[0][0]
    edge = collections.Counter(g[edge_px]).most_common(1)[0][0]
    best = None
    for size in range(H + 12, 8, -1):
        f = ImageFont.truetype(FONT, size); f.set_variation_by_name(b'Bold')
        im = Image.new('L', (64, 64), 0); ImageDraw.Draw(im).text((8, 4), ch, font=f, fill=255)
        a = np.array(im) > 110; yy, xx = np.nonzero(a)
        a = a[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        if a.shape[0] <= H - 2 and a.shape[1] <= min(W + 4, 30):
            best = a; break
    out = np.zeros((32, 32), np.uint8)
    y0 = ys.min() + (H - best.shape[0]) // 2; x0 = (32 - best.shape[1]) // 2
    sub = out[y0:y0 + best.shape[0], x0:x0 + best.shape[1]]
    p2 = np.pad(best, 1); o = np.zeros_like(p2)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(p2, dy, 0), dx, 1)
    ol = (o & ~p2)[1:-1, 1:-1]
    sub[best] = fill                                     # 테두리 없음 — 원본 경계색이 밝은 회색이라 작은 구멍(ㅇ)이 메워져 보임
    if y0 > 0:                                           # 테두리 바깥 1px(위)
        pass
    return out


def main():
    prev = []
    for X in 'BOCASL':
        spec = S.SETS[X][1]['PRE']; fp, off = spec.rsplit(':', 1); off = int(off, 16)
        src = os.path.join(OUT, fp)
        d = bytearray(open(src if os.path.exists(src) else os.path.join(S.DISC, fp), 'rb').read())
        orig_len = (lambda b: sglz.decode(b, off)[1] - off)(open(os.path.join(S.DISC, fp), 'rb').read())
        t, end = sglz.decode(bytes(d), off)
        row = []
        for jp, kr, t0 in GL:
            g = glyph(t, t0); n = korean(kr, g); t = put(t, t0, n)
            row.append(np.concatenate([np.pad(g, 2), np.pad(n, 2)], 0))
        comp = sglz.encode(t)
        assert sglz.decode(comp, 0)[0] == t
        if len(comp) > orig_len:
            raise SystemExit('%s 압축 초과 %d > %d' % (X, len(comp), orig_len))
        d[off:off + len(comp)] = comp
        os.makedirs(os.path.dirname(src), exist_ok=True); open(src, 'wb').write(bytes(d))
        prev.append(np.concatenate(row, 1)); print(X, fp, '압축', len(comp), '/', orig_len)
    img = np.concatenate([np.pad(p, ((0, 4), (0, 0))) for p in prev], 0)
    Image.fromarray((img * 17).astype(np.uint8)).resize((img.shape[1] * 3, img.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'stg', 'date_kr.png'))
    if os.path.exists(os.path.join(OUT, 'STG_B', 'PREB_DAT.BIN')):
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, 'stg_copies.py')])


if __name__ == '__main__':
    main()
