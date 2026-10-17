# -*- coding: utf-8 -*-
r"""연습 메뉴 직접색 그림(CD 블록) 한글화 — 배너 3·조종사 카드 3·작전 카드 12 (2026-10-17)
  CD = GF 와 같은 압축(sglz) 의 16비트 직접색 · 맵 BD(바로 앞, 폭 32) 값 v → 풀린 데이터 위치 (v&0xFFF)×0x80 − VRAM 목적지.
  지우기: 지정 구역 안 «흰(최소 >190)·빨강 + 2px 안에 거의 검정» 화소 + 둘레 5px → OpenCV 메우기(TELEA).
  그리기: NotoSerifKR Black, 흰/빨강(원본 빨강 표본) 채움 + 검은 2px 테두리. 한 줄 = 크기가 다른 조각들(아래 맞춤).
  재압축 크기 ≤ 원본 압축 길이. 결과는 work/out/PMENU/<파일> 의 같은 자리에 합침(다른 도구가 고친 부분 유지).
  python tools/cd_kr.py → work/cd/kr_<이름>.png(원본|새것)
"""
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc', 'PMENU'); OUT = os.path.join(ROOT, 'work', 'out', 'PMENU')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
W_, S_ = 'W', 'R'                                      # 흰 · 빨강


def L(*segs, x=4, base=266, al='L', maxw=120, aa=True):
    """줄: 조각 (글, 잉크 높이, 색) 들 · base = 아래 기준 y · al L/R/C"""
    return dict(segs=segs, x=x, base=base, al=al, maxw=maxw, aa=aa)


# (파일, CD 위치, BD 위치, VRAM 목적지, 지울 구역 [(x0,y0,x1,y1)], 줄들)
JOBS = {
    'stage1': ('PM_S123', 0x1E9E0, None, 0x35000, [(0, 190, 128, 272)], [L(('도쿄', 40, W_), ('상공', 20, W_))]),
    'stage2': ('PM_S123', 0x29298, None, 0x35000, [(0, 190, 128, 272)], [L(('궤도', 40, W_), ('상', 20, W_), al='R', x=124)]),
    'stage3': ('PM_S123', 0x35240, None, 0x35000, [(0, 200, 128, 272)], [L(('대', 20, W_), ('협곡', 40, W_), al='R', x=124)]),
    'boss1': ('PM_S123', 0x42804, None, 0x35000, [(0, 200, 128, 272)],
              [L(('전익형 폭장기', 15, W_), base=228, al='C', x=64), L(('코쿠베츠', 28, S_), al='C', x=64)]),
    'boss2': ('PM_S123', 0x50398, None, 0x35000, [(0, 170, 128, 272)],
              [L(('대우주·대지상', 15, W_), base=206), L(('공격 위성', 15, W_), base=224), L(('신센', 34, S_), al='R', x=124)]),
    'boss3': ('PM_S123', 0x5F4DC, None, 0x35000, [(0, 0, 128, 112)],
              [L(('대형', 15, W_), base=20), L(('전술', 15, W_), base=38), L(('격투', 15, W_), base=56), L(('공격기', 15, W_), base=74),
               L(('돈류', 36, S_), al='R', x=124, base=48, maxw=78)]),
    'stage4': ('PM_S456', 0x270BC, None, 0x35000, [(0, 195, 128, 272)], [L(('암초', 20, W_), ('공역', 40, W_))]),
    'stage5': ('PM_S456', 0x32AA8, None, 0x35000, [(0, 195, 128, 272)], [L(('북해', 20, W_), ('유전', 40, W_), aa=False)]),
    'stage6': ('PM_S456', 0x3F4D8, None, 0x35000, [(0, 190, 128, 272)], [L(('화성', 40, W_), ('상공', 20, W_), aa=False)]),
    'boss4': ('PM_S456', 0x4DD2C, None, 0x35000, [(0, 178, 128, 272)],
              [L(('범용 전술', 15, W_), base=212), L(('아키타카', 28, S_), al='C', x=64, base=246), L(('전투 우주기', 15, W_), base=266)]),
    'boss5': ('PM_S456', 0x59FAC, None, 0x35000, [(0, 178, 128, 272)],
              [L(('극지 전략 수송 공격기', 15, W_), base=208, al='C', x=64), L(('카이호', 32, S_), al='C', x=64, base=262)]),
    'boss6': ('PM_S456', 0x66010, None, 0x35000, [(0, 190, 128, 272)],
              [L(('고고도 중계', 15, W_), base=212), L(('부공 공격기', 15, W_), base=230), L(('바쿠잔', 30, S_), al='C', x=64)]),
    'pilot1': ('PM_JIK', 0x6D6B4, None, 0x35000, [(0, 0, 128, 86)], [L(('야시다', 28, W_), base=36, x=6, maxw=118), L(('카오루', 28, W_), base=72, al='R', x=122, maxw=118)]),
    'pilot2': ('PM_JIK', 0x74D90, None, 0x35000, [(0, 0, 128, 86)], [L(('미카즈키', 28, W_), base=36, x=6, maxw=118), L(('료타', 28, W_), base=72, al='R', x=122, maxw=118)]),
    'pilot3': ('PM_JIK', 0x7D3B0, None, 0x35000, [(0, 0, 128, 86)], [L(('쿠니무라', 28, W_), base=36, x=6, maxw=118), L(('리카', 28, W_), base=72, al='R', x=122, maxw=118)]),
    'banner1': ('PMENU', 0x207A4, None, 0x35000, [(2, 60, 72, 158), (140, 2, 254, 62)],
                [L(('토류', 40, W_), base=152, x=6, maxw=70), L(('야시다', 22, W_), base=26, al='R', x=252, maxw=112), L(('카오루', 22, W_), base=54, al='R', x=252, maxw=112)]),
    'banner2': ('PMENU', 0x284D0, None, 0x35000, [(2, 60, 72, 158), (140, 2, 254, 62)],
                [L(('시덴', 40, W_), base=152, x=6, maxw=70), L(('미카즈키', 22, W_), base=26, al='R', x=252, maxw=112), L(('료타', 22, W_), base=54, al='R', x=252, maxw=112)]),
    # banner3 «호가» maxw 56 = 8행 4열(x64~) 공유 칸 피함
    'banner3': ('PMENU', 0x32118, None, 0x35000, [(2, 60, 72, 158), (140, 2, 254, 62)],
                [L(('호가', 40, W_), base=152, x=6, maxw=56), L(('쿠니무라', 22, W_), base=26, al='R', x=252, maxw=112), L(('리카', 22, W_), base=54, al='R', x=252, maxw=112)]),
}


def font(px):
    f = ImageFont.truetype(FONT, px); f.set_variation_by_name(b'Black'); return f


def px_for(ink):
    px = ink
    while (lambda bb: bb[3] - bb[1])(font(px + 1).getbbox('한')) <= ink:
        px += 1
    return px


def find_bd(d, co):
    """CD 바로 앞 BD(32칸 폭) — 길이는 0x2C0(352)·0x480(576)·0x800(1024) 중 값이 모두 0x6xx~ 인 것"""
    for n in (1024, 576, 352):
        bo = co - n * 2
        m = struct.unpack('>%dH' % n, d[bo:bo + n * 2])
        if all(0x400 <= (v & 0xFFF) for v in m) and max(v & 0xFFF for v in m) < 0x1000:
            return bo, m
    raise SystemExit('BD 못 찾음 %X' % co)


def compose(t, m, vb):
    H = (len(m) + 31) // 32
    img = np.zeros((H * 16, 512), np.uint16)
    for i, v in enumerate(m):
        a = (v & 0xFFF) * 0x80 - vb; y, x = divmod(i, 32)
        for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
            o = a + k * 128
            if 0 <= o <= len(t) - 128:
                img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = np.frombuffer(t[o:o + 128], '>u2').reshape(8, 8)
    return img


def to_rgb(w):
    return np.stack([(w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3], -1).astype(np.uint8)


def to555(rgb):
    r, g, b = (rgb[..., 0].astype(np.uint16) >> 3), (rgb[..., 1].astype(np.uint16) >> 3), (rgb[..., 2].astype(np.uint16) >> 3)
    return (0x8000 | (b << 10) | (g << 5) | r).astype(np.uint16)


def render_line(ln, redc):
    """조각들을 아래 맞춤으로 이은 RGBA — 폭 넘치면 가로 축소(≥0.7) 후 크기 축소"""
    scale = 1.0
    while True:
        parts = []
        for t, ink, col in ln['segs']:
            f = font(px_for(max(8, int(ink * scale))))
            bb = f.getbbox(t, stroke_width=3)
            w0, h0 = bb[2] - bb[0] + 2, bb[3] - bb[1] + 2
            fl = Image.new('L', (w0, h0), 0)               # 채움 = 글자 + 1px 굵게(원본 획 굵기)
            big = ink >= 24                                # 큰 글자만 1px 굵게 + 테 2px · 작은 글자는 테 1px
            ImageDraw.Draw(fl).text((-bb[0] + 1, -bb[1] + 1), t, font=f, fill=255, stroke_width=1 if big else 0, stroke_fill=255)
            fa = np.array(fl)
            oa = cv2.dilate(fa, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5) if big else (3, 3)))
            fill = (255, 255, 255) if col == W_ else tuple(int(c) for c in redc)
            arr = np.zeros((h0, w0, 4), np.uint8); arr[..., 3] = oa
            fr = fa.astype(float)[..., None] / 255
            arr[..., :3] = (np.array(fill)[None, None, :] * fr).astype(np.uint8)
            im = Image.fromarray(arr)
            base = -bb[1] + 1 + f.getbbox('한')[3]          # 「한」 아래 = 줄 기준
            parts.append((im, base))
        gap = 2
        w = sum(p.width for p, _ in parts) + gap * (len(parts) - 1)
        asc = max(b for _, b in parts); desc = max(p.height - b for p, b in parts)
        out = Image.new('RGBA', (w, asc + desc), (0, 0, 0, 0)); x = 0
        for p, b in parts:
            out.alpha_composite(p, (x, asc - b)); x += p.width + gap
        if not ln['aa']:                               # 안티에일리어싱 끔(재압축이 원본을 넘는 그림)
            a_ = np.array(out); a_[..., 3] = np.where(a_[..., 3] > 127, 255, 0); out = Image.fromarray(a_)
        if w <= ln['maxw']:
            return out, asc
        if w * 0.7 <= ln['maxw']:
            return out.resize((ln['maxw'], out.height), Image.LANCZOS), asc
        scale *= 0.94


def main():
    os.makedirs(OUT, exist_ok=True)
    outs = {}
    for name, (fn, co, _, vb, zones, lines) in JOBS.items():
        d = open(os.path.join(DISC, fn + '.BIN'), 'rb').read()
        if fn not in outs:
            p = os.path.join(OUT, fn + '.BIN')
            outs[fn] = bytearray(open(p, 'rb').read() if os.path.exists(p) else d)
        t, end = sglz.decode(d, co); olen = end - co
        bo, m = find_bd(d, co)
        w16 = compose(t, m, vb); rgb = to_rgb(w16)
        a = rgb.astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
        white = a.min(2) > 190; red = (r > 140) & (g < 100) & (b < 100) & (r > g + 60)
        neard = cv2.dilate((a.max(2) < 50).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        zone = np.zeros(white.shape, bool)
        for x0, y0, x1, y1 in zones:
            zone[y0:y1, x0:x1] = True
        txt = (white | red) & neard & zone
        n_, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(txt.astype(np.uint8), np.ones((3, 3), np.uint8)), 8)
        keep = np.zeros_like(txt)
        for k in range(1, n_):
            if st[k, 4] >= 25:
                keep |= (lab == k) & txt
        redc = np.median(a[keep & red], 0) if (keep & red).any() else np.array([230, 20, 20])
        sat_ = a.max(2) - a.min(2)
        light = ((a.min(2) > 90) & (sat_ < 50)) | ((r > 170) & (g < 70) & (b < 70))   # 글자 둘레 무채색 안티에일리어싱까지 — 메우기가 회색을 끌어오지 않게
        for _ in range(2):
            keep |= light & zone & (cv2.dilate(keep.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
        # 굵은 획 속살(테두리에서 먼 흰 화소)까지: 구역 안 흰·빨강 덩어리 중 글자 화소와 이어진 것 전체
        sred = (r > 170) & (g < 70) & (b < 70)                 # 확장은 엄격한 빨강만(주황 하늘 제외)
        n2, lab2 = cv2.connectedComponents(((white | sred) & zone).astype(np.uint8), connectivity=8)
        hit = np.unique(lab2[keep & (lab2 > 0)])
        sizes = np.bincount(lab2.ravel())
        hit = [h for h in hit if sizes[h] <= 2500]                # 큰 덩어리(흰 구름 등 배경)는 제외
        keep |= np.isin(lab2, hit) & (lab2 > 0)
        dl = 7 if name.startswith('banner') else 11       # 배너는 인물·기체가 글자에 붙어 있어 둘레 3px 만
        er = (cv2.dilate(keep.astype(np.uint8), np.ones((dl, dl), np.uint8)) > 0) & zone
        hh_ = int(np.nonzero(w16.any(1))[0].max()) + 1; ww_ = int(np.nonzero(w16.any(0))[0].max()) + 1
        new = rgb.copy()                                    # 메우기는 그림 범위 안에서만(바깥 검정을 끌어오지 않게)
        new[:hh_, :ww_] = cv2.inpaint(np.ascontiguousarray(rgb[:hh_, :ww_]), (er[:hh_, :ww_]).astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
        if os.environ.get('CDDBG') == name:
            Image.fromarray(np.concatenate([rgb, np.stack([er.astype(np.uint8) * 255] * 3, -1), new], 1)[:300, :]).save(os.path.join(ROOT, 'work', 'cd', 'dbg_%s.png' % name))
        pim = Image.fromarray(new).convert('RGBA')
        for ln in lines:
            im, asc = render_line(ln, redc)
            x = ln['x'] if ln['al'] == 'L' else (ln['x'] - im.width if ln['al'] == 'R' else ln['x'] - im.width // 2)
            pim.alpha_composite(im, (max(0, x), ln['base'] - asc))
        new = np.array(pim.convert('RGB'))
        nw = to555(new); nw[w16 == 0] = 0
        # 칸 제자리 쓰기
        tb = bytearray(t); seen = {}
        for i, v in enumerate(m):
            ao = (v & 0xFFF) * 0x80 - vb; y, x = divmod(i, 32)
            for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                o = ao + k * 128
                if 0 <= o <= len(t) - 128:
                    blk = nw[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8].astype('>u2').tobytes()
                    if o in seen and seen[o] != blk:
                        continue                              # 공유 칸은 처음 것 유지
                    seen[o] = blk; tb[o:o + 128] = blk
        comp = sglz.encode(bytes(tb)); assert sglz.decode(comp, 0)[0] == bytes(tb)
        ok = len(comp) <= olen
        print(name, fn, hex(co), '압축', len(comp), '/', olen, '맞음' if ok else '✗ 초과')
        if ok:
            outs[fn][co:co + len(comp)] = comp
        chk = to_rgb(compose(bytes(tb), m, vb))
        hh = int(np.nonzero(w16.any(1))[0].max()) + 1; ww = int(np.nonzero(w16.any(0))[0].max()) + 1
        Image.fromarray(np.concatenate([rgb[:hh, :ww], np.full((hh, 4, 3), 128, np.uint8), chk[:hh, :ww]], 1)).save(
            os.path.join(ROOT, 'work', 'cd', 'kr_%s.png' % name))
    for fn, data in outs.items():
        open(os.path.join(OUT, fn + '.BIN'), 'wb').write(bytes(data))


if __name__ == '__main__':
    main()
