# -*- coding: utf-8 -*-
r"""연습 메뉴 기체 사양표(PM_JIK CD 3장) 한글화 (2026-10-17)
  검은 바탕 위 흰 글씨 → 지우기 = 구역 안 밝은 화소(최소 채널 >8 — 흐린 가장자리까지)를 검정으로(구분선은 구역 밖).
  작은 글씨 = 호기·라벨 Galmuri9 / 제원·무장 Galmuri7(세로 2배 14px — 원본 줄 간격 16~18) 세로 2배(인터레이스 화면) 흰색 · 큰 이름 = NotoSerifKR Black 흰 + 원래 상자에 맞춤.
  S.O.Q-xxx 줄은 원본 유지. 재압축 ≤ 원본 길이, work/out/PMENU/PM_JIK.BIN 에 합침(cd_kr 다음에 실행).
  python tools/spec_kr.py → work/cd/kr_spec<n>.png(원본|새것)
"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import cd_kr as C  # noqa: E402
from bdf import Font  # noqa: E402

GAL = r'C:\claude\utils\font\Galmuri-v2.40.3'
G9 = Font(os.path.join(GAL, 'Galmuri9.bdf')); G7 = Font(os.path.join(GAL, 'Galmuri7.bdf'))
SHEETS = {
    1: (0x25290, '1호기', '토류', ['전장 18미터 80센티', '전폭 17미터 70센티', '전고 10미터 50센티'],
        ['확산형 web 반자립 하전 예도탄(EI-DOU)', '집중형 web 와상 자계 중입자탄(PINPOINT)']),
    2: (0x326B0, '2호기', '시덴', ['전장 20미터 10센티', '전폭 17미터 80센티', '전고 11미터 40센티'],
        ['확산형 web 전천 열광류 조사기(ALLRANGE)', '집중형 web 자기 색식 교입자탄(BOU-RYU)']),
    3: (0x3F084, '3호기', '호가', ['전장 19미터', '전폭 18미터 60센티', '전고 12미터 40센티'],
        ['확산형 web 무사각 편중입자탄(RANDOM)', '집중형 web 색도 입하 무쌍 포탄(MU-SOU)']),
}
LABELS = [((148, 196, 174, 220), '전면', 'R'), ((177, 196, 210, 220), '측면', 'L'), ((148, 224, 174, 250), '상면', 'R')]
COL = (178, 252, 360, 420)                              # 오른쪽 설명 열(구분선 x175 밖)


def layer(font, text, track=0):
    pts, x = [], 0
    for ch in text:
        pp, w = font.draw(ch)
        pts += [(px + x, py) for px, py in pp]; x += w + (track if ch != ' ' else 0)
    h = max([y for _, y in pts] + [0]) + 1
    a = np.zeros((h, max(1, x)), bool)
    for px, py in pts:
        a[py, px] = True
    return np.repeat(a, 2, axis=0)                     # 세로 2배


def small(text, maxw, fonts=None):
    for f, tr in (fonts or ((G9, 0), (G9, -1), (G7, 0))):
        m = layer(f, text, tr)
        if m.shape[1] <= maxw:
            return m
    return m[:, :maxw]


def lines(mask, y0, x0):
    rows = mask.any(1); out = []; y = 0
    while y < len(rows):
        if rows[y]:
            s = y
            while y < len(rows) and rows[y]:
                y += 1
            xs = np.nonzero(mask[s:y].any(0))[0]; out.append((y0 + s, y0 + y, x0 + xs.min(), x0 + xs.max() + 1))
        else:
            y += 1
    return out


def big(text, w, h):
    f = ImageFont.truetype(C.FONT, 120); f.set_variation_by_name(b'Black')
    bb = f.getbbox(text); im = Image.new('L', (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), 0)
    ImageDraw.Draw(im).text((-bb[0] + 2, -bb[1] + 2), text, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 100); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    a = np.array(Image.fromarray(a).resize((w, h), Image.LANCZOS))
    return np.maximum(a, np.pad(a, ((0, 0), (1, 0)))[:, :-1])          # 가로 1px 굵게(원본 획)


def main():
    p = os.path.join(C.OUT, 'PM_JIK.BIN'); d = open(os.path.join(C.DISC, 'PM_JIK.BIN'), 'rb').read()
    out = bytearray(open(p, 'rb').read() if os.path.exists(p) else d)
    for n, (co, ki, nm, specs, weps) in SHEETS.items():
        t, end = sglz.decode(d, co); olen = end - co
        bo = co - 0x800; m = struct.unpack('>1024H', d[bo:bo + 0x800]); vb = 0x200   # 목차: BD 0x800 B 가 CD 바로 앞
        w16 = C.compose(t, m, vb); rgb = C.to_rgb(w16); a = rgb.astype(int)
        new = rgb.copy(); lum = a.min(2)
        x0, y0, x1, y1 = COL
        ls = lines(lum[y0:y1, x0:x1] > 150, y0, x0)        # [호기, S.O.Q, 이름+제원 블록, 무장1, 무장2]
        assert len(ls) == 5, ls
        def erase(ya, yb, xa, xb):
            reg = new[ya:yb, xa:xb]; reg[lum[ya:yb, xa:xb] > 8] = 0
        def put(mask, y, x, val=255):
            h, w = mask.shape; reg = new[y:y + h, x:x + w]
            reg[mask[:reg.shape[0], :reg.shape[1]] > 0] = val
        # 1) 호기
        ya, yb, xa, xb = ls[0]; erase(ya - 1, yb + 1, x0, x1); put(small(ki, 80), ya, xa)
        # 2) 이름 + 제원 블록: 제원 = 블록 안 x ≥ 이름 오른쪽
        ya, yb, xa, xb = ls[2]
        blk = lum[ya:yb, x0:x1] > 150; cols = np.nonzero(blk.any(0))[0]
        gaps = [(cols[i], cols[i + 1]) for i in range(len(cols) - 1) if cols[i + 1] - cols[i] > 4]
        nx1 = x0 + gaps[0][0] + 1; sx0 = x0 + gaps[0][1]
        sl = lines(lum[ya:yb, sx0:x1] > 150, ya, sx0)
        erase(ya - 1, yb + 1, x0, x1)
        bm = big(nm, nx1 - xa, yb - ya); reg = new[ya:yb, xa:nx1]
        reg[:] = np.maximum(reg, np.repeat(bm[..., None], 3, -1)[:reg.shape[0], :reg.shape[1]])
        for (sa, sb, _, _), txt in zip(sl, specs):
            put(small(txt, x1 - sx0, ((G7, 0), (G7, -1))), sa + 1, sx0)
        # 3) 무장 2줄
        for (wa, wb, wx, _), txt in zip(ls[3:], weps):
            erase(wa - 1, wb + 1, x0, x1); put(small(txt, x1 - 4 - wx, ((G7, 0), (G7, -1))), wa + 1, wx)
        # 4) 라벨
        for (lx0, ly0, lx1, ly1), txt, al in LABELS:
            ll = lines(lum[ly0:ly1, lx0:lx1] > 150, ly0, lx0)
            if not ll:
                continue
            la, lb, lxa, lxb = ll[0]; erase(ly0, ly1, lx0, lx1)
            mk = small(txt, 40); put(mk, la, (lxb - mk.shape[1]) if al == 'R' else lxa)
        nw = C.to555(new); nw[w16 == 0] = 0
        tb = bytearray(t); seen = {}
        for i, v in enumerate(m):
            ao = (v & 0xFFF) * 0x80 - vb; yy, xx = divmod(i, 32)
            for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                o = ao + k * 128
                if 0 <= o <= len(t) - 128:
                    b_ = nw[yy * 16 + dy:yy * 16 + dy + 8, xx * 16 + dx:xx * 16 + dx + 8].astype('>u2').tobytes()
                    if o in seen and seen[o] != b_:
                        continue
                    seen[o] = b_; tb[o:o + 128] = b_
        comp = sglz.encode(bytes(tb)); assert sglz.decode(comp, 0)[0] == bytes(tb)
        ok = len(comp) <= olen
        print('사양표', n, '압축', len(comp), '/', olen, '맞음' if ok else '✗ 초과')
        if ok:
            out[co:co + len(comp)] = comp
        chk = C.to_rgb(C.compose(bytes(tb), m, vb))
        Image.fromarray(np.concatenate([rgb[:420, :380], np.full((420, 4, 3), 128, np.uint8), chk[:420, :380]], 1)).save(
            os.path.join(C.ROOT, 'work', 'cd', 'kr_spec%d.png' % n))
    open(p, 'wb').write(bytes(out))


if __name__ == '__main__':
    main()
