# -*- coding: utf-8 -*-
r"""설정 화면 난이도 이름 8개 한글화 — OPT_PNT 그림 A(GF 0x4822C → VRAM 0x4D000, 4bpp 8×8, 칸 기준 0x2000) (2026-10-17)
  코드가 난이도마다 NBG1 맵 15~18행에 조각 타일을 깔고, 조각 타일 일부를 여러 이름이 함께 씀
  (쉬움 조 1·2·3 = 簡単 꼬리 / 난이도 조 4~8 = 難度 꼬리, 4·5 = 標準難度, 6·7·8 = 的難度).
  → 같은 조는 같은 크기·오른쪽 끝 맞춤으로 그려 공유 타일 내용이 같아지게. 인터레이스 화면이라 세로 2배.
  각 난이도 맵 = 스테이트 d1~d8(work/mem). 빈칸(0x680)에 떨어지는 잉크는 못 그림 → 잃은 화소 수 출력.
  python tools/diff_kr.py → work/out/TITLE/OPT_PNT.BIN(합침) · work/nbg/diff_preview.png
"""
import collections
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc', 'TITLE'); OUT = os.path.join(ROOT, 'work', 'out', 'TITLE')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
GF = 0x4822C; VB = 0x4D000; BASE = 0x2000
R0, R1, C0, C1 = 15, 19, 26, 42
YOFF_A = 3                                             # 쉬움 조 세로 밀기(2번 「に」 빈칸 피함)
RIGHT = 41 * 8 + 7                                     # 오른쪽 끝(원본 잉크 끝 근처)
NAMES = {1: '가장 쉬움', 2: '더욱 쉬움', 3: '비교적 쉬움', 4: '표준 난이도', 5: 'AC판 표준 난이도',
         6: '도전적 난이도', 7: '위협적 난이도', 8: '폭력적 난이도'}
GROUP = {1: 'A', 2: 'A', 3: 'A', 4: 'B', 5: 'B', 6: 'B', 7: 'B', 8: 'B'}


def maps():
    out = {}
    for k in range(1, 9):
        V = open(os.path.join(ROOT, 'work', 'mem', 'd%d' % k, 'VDP2_VRAM.bin'), 'rb').read()
        m = struct.unpack('>4096H', V[0x5E000:0x60000])
        out[k] = np.array(m).reshape(64, 64)[R0:R1, C0:C1]
    return out


def tidx(v):
    a = ((v & 0xFFF) | BASE) * 0x20
    return (a - VB) // 32 if VB <= a else None


def render(text, char_w):
    """글자 폭 char_w 기준 크기, 세로 2배 → 덮임 0~1"""
    px = 10
    while True:
        f = ImageFont.truetype(FONT, px + 1); f.set_variation_by_name(b'Black')
        if f.getbbox('한')[2] - f.getbbox('한')[0] > char_w:
            break
        px += 1
    f = ImageFont.truetype(FONT, px * 4); f.set_variation_by_name(b'Black')
    ref = f.getbbox('한'); WW = 4 * (C1 - C0) * 8                # 4배 캔버스, 오른쪽 끝 고정(공유 꼬리 화소가 같게)
    im = Image.new('L', (WW, ref[3] - ref[1] + 8), 0)
    ImageDraw.Draw(im).text((4 * (RIGHT - C0 * 8), -ref[1] + 4), text, font=f, fill=255, anchor='rs' if False else 'ra')
    w = im.width // 4; h = im.height // 4 * 2
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(float) / 255


def ink_w(cov):
    xs = np.nonzero((cov > 0.3).any(0))[0]
    return (RIGHT - C0 * 8) - xs.min() if len(xs) else 0


def main():
    d = open(os.path.join(DISC, 'OPT_PNT.BIN'), 'rb').read()
    t, end = sglz.decode(d, GF); olen = end - GF; nt = len(t) // 32
    TL = [np.stack([np.frombuffer(t[i * 32:i * 32 + 32], np.uint8) >> 4, np.frombuffer(t[i * 32:i * 32 + 32], np.uint8) & 15], 1).reshape(8, 8)
          for i in range(nt)]
    M = maps()
    # 원본 색: 이름 칸 화소 최다(빨강 채움) · 둘째(어두운 빨강)
    cnt = collections.Counter()
    for k, m in M.items():
        for v in m.ravel():
            ti = tidx(v)
            if ti is not None and 0 <= ti < nt and (v & 0xFFF) not in (0x680, 0xC00):
                cnt.update(TL[ti][TL[ti] > 0].tolist())
    fill, shade = [c for c, _ in cnt.most_common(2)]
    print('색 채움', fill, '그늘', shade)
    # 조별 글자 폭: 가장 긴 이름이 그 조에서 가장 좁은 칸 범위에 들어가게
    def avail(k):
        cols = np.nonzero(((M[k] & 0xFFF) != 0x680) & ((M[k] & 0xFFF) != 0xC00))[1]
        return RIGHT - (C0 + cols.min()) * 8
    cw = {}
    for g in 'AB':
        ks = [k for k in NAMES if GROUP[k] == g]
        cw[g] = 30
        while any(ink_w(render(NAMES[k], cw[g])) > avail(k) for k in ks) and cw[g] > 6:
            cw[g] -= 1
        print('조', g, '글자 폭', cw[g], [(k, avail(k)) for k in ks])
    votes = collections.defaultdict(list)
    lost = {}
    canv = {}
    for k, txt in NAMES.items():
        cov = render(txt, cw[GROUP[k]])
        H = (R1 - R0) * 8; W = (C1 - C0) * 8
        c = np.zeros((H, W))
        h, w = cov.shape; y0 = (H - h) // 2 + (YOFF_A if GROUP[k] == 'A' else 0); x0 = 0
        c[max(0, y0):y0 + h, x0:x0 + w] = cov[max(0, -y0):H - y0][:, :]
        canv[k] = c
        m = M[k]; lost[k] = 0
        for r in range(R1 - R0):
            for q in range(C1 - C0):
                blk = c[r * 8:r * 8 + 8, q * 8:q * 8 + 8]
                v = m[r, q] & 0xFFF
                if v in (0x680, 0xC00):
                    lost[k] += int((blk > 0.5).sum()); continue
                tile = np.where(blk > 0.6, fill, np.where(blk > 0.3, shade, 0)).astype(np.uint8)
                votes[tidx(m[r, q])].append((k, tile))
    print('잃은 화소', lost)
    conflict = 0
    for ti, lst in votes.items():
        base_ = lst[0][1]
        for k, tl in lst[1:]:
            if not np.array_equal(base_, tl):
                conflict += int((base_ != tl).sum())
        TL[ti] = base_
    print('공유 타일 충돌 화소', conflict)
    nb = b''.join(bytes(((T_[:, 0::2] << 4) | T_[:, 1::2]).astype(np.uint8).ravel()) for T_ in TL)
    comp = sglz.encode(nb); assert sglz.decode(comp, 0)[0] == nb
    print('압축', len(comp), '/', olen)
    if len(comp) > olen:
        raise SystemExit('압축 초과')
    p = os.path.join(OUT, 'OPT_PNT.BIN')
    body = bytearray(open(p, 'rb').read() if os.path.exists(p) else d)
    body[GF:GF + len(comp)] = comp
    os.makedirs(OUT, exist_ok=True); open(p, 'wb').write(bytes(body))
    # 미리보기: 상태별 맵으로 새 타일 렌더(세로 ½ 로 실제 비율)
    rows = []
    for k in range(1, 9):
        m = M[k]; img = np.zeros(((R1 - R0) * 8, (C1 - C0) * 8), np.uint8)
        for r in range(R1 - R0):
            for q in range(C1 - C0):
                ti = tidx(m[r, q])
                if (m[r, q] & 0xFFF) not in (0x680, 0xC00) and ti is not None and 0 <= ti < nt:
                    img[r * 8:r * 8 + 8, q * 8:q * 8 + 8] = TL[ti]
        rgbi = np.zeros(img.shape + (3,), np.uint8); rgbi[img == fill] = (230, 20, 20); rgbi[img == shade] = (120, 10, 10)
        rows.append(np.pad(rgbi, ((2, 2), (2, 2), (0, 0)), constant_values=60))
    o = np.concatenate(rows, 0)
    Image.fromarray(o).resize((o.shape[1] * 3, o.shape[0] * 3 // 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'nbg', 'diff_preview.png'))


if __name__ == '__main__':
    main()
