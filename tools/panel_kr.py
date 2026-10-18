# -*- coding: utf-8 -*-
r"""연습 메뉴 작전 패널(스테이지 1~6) 한글 그림 + 재배치 (2026-10-17)
  PMENU.BIN 목차 [GP 4800(256색 16×16 글자 그림 → VRAM 0x48000) + BD 5E00(맵 32×11)] × 6 (목차 4·6·…·14 / 5·7·…·15).
  맵 값 v: 글자 주소 = (v & 0xFFF)×0x80 (8×8 칸 4개 = 256 B, 순서 왼위·오른위·왼아래·오른아래) · 색 뱅크 = (v>>12)&7 (CRAM 뱅크×256).
  글자 화소 = 밝고 채도 낮은(흰·회) 화소 + 둘레 1px(검은 테두리) — 사진 상자(x114~244, y10~109)·바깥 테두리 3px 제외.
  바탕 = 행마다 줄무늬 가로 주기만큼 떨어진 바탕 화소로 복원. 글자 = NotoSerifKR(큰 것 Black) 흰 채움 + 검은 테두리, 세로 2배(인터레이스).
  재배치: 패널마다 글자 세트 통째(16×16 단위 중복 제거) — 글자 수·압축 ≤ 원본.
  python tools/panel_kr.py → work/out/PMENU/PMENU.BIN(합침) · work/nbg/panel_<n>.png(원본|새것)
"""
import collections
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import pm_detail as P  # noqa: E402
import stg_kr as K  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc'); OUT = os.path.join(ROOT, 'work', 'out')
PHOTO = (117, 10, 244, 109)
NOTO = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
TEXT = {
    1: ['스테이지 1', '도쿄 상공', '작전:', '「본사 상공 소속 불명기 요격」'],
    2: ['스테이지 2', '궤도상', '작전:', '「공격 위성의 훈련 저지」'],
    3: ['스테이지 3', '협곡', '작전:「아군 기지', '기습을 노리는 적 부대 요격」'],
    4: ['스테이지 4', '암초 공역', '작전:', '「암초 공역에 잔존하는 적 전력 소탕」'],
    5: ['스테이지 5', '북해 유전', '작전:', '「제압된 유전 겸 발착장 탈환」'],
    6: ['스테이지 6', '화성 표면', '작전:「적 본거지에 대한', '수직 강하 기습 공격」'],
}


def decode_panel(d, t, k):
    tg, a, p = t[k]; off = p - 0x200000
    tiles, end = sglz.decode(d, off); base = a * 0x10
    bt, ba, bp = t[k + 1]; boff = bp - 0x200000; n = (p - bp) // 2
    ents = list(struct.unpack('>%dH' % n, d[boff:boff + n * 2])); W = 32; H = n // W
    img = np.zeros((H * 16, W * 16), np.int32); bank = np.zeros((H, W), int)
    for i, v in enumerate(ents):
        addr = (v & 0xFFF) * 0x80 - base; y, x = divmod(i, W); bank[y, x] = (v >> 12) & 7
        for kk, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
            o = addr + kk * 64
            if 0 <= o <= len(tiles) - 64:
                img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = np.frombuffer(tiles[o:o + 64], np.uint8).reshape(8, 8)
    return dict(off=off, end=end, tiles=tiles, base=base, boff=boff, n=n, ents=ents, img=img, bank=bank, W=W, H=H)


def aa_text(text, h, maxw):
    """안티에일리어싱 줄 → (채움, 테두리) 덮임 0~1. 원래 줄 높이 h 로 그리고 가로만 ½(세로 2배 인터레이스 비율). 테 = 가로 1·세로 2px"""
    px = 8
    while True:
        f = ImageFont.truetype(NOTO, px + 1); f.set_variation_by_name(b'Black')
        bh = f.getbbox('한')
        if bh[3] - bh[1] > h - 6:
            break
        px += 1
    f = ImageFont.truetype(NOTO, px); f.set_variation_by_name(b'Black')
    bb = f.getbbox(text)
    im = Image.new('L', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), 0)
    ImageDraw.Draw(im).text((-bb[0] + 4, -bb[1] + 4), text, font=f, fill=255)
    w = min(max(1, im.width // 2), maxw - 2)
    fa = np.array(im.resize((w, im.height), Image.LANCZOS)).astype(float) / 255
    oa = cv2.dilate((fa * 255).astype(np.uint8), np.ones((5, 3), np.uint8)).astype(float) / 255
    return fa, oa


def main():
    d = open(os.path.join(DISC, 'PMENU', 'PMENU.BIN'), 'rb').read(); t = P.toc()
    cr = P.cram_of('s6')
    rgbv = lambda e: ((e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3)
    outp = os.path.join(OUT, 'PMENU', 'PMENU.BIN')
    body = bytearray(open(outp, 'rb').read() if os.path.exists(outp) else d)
    for s in range(1, 7):
        k = 4 + (s - 1) * 2
        pn = decode_panel(d, t, k); img = pn['img']; bank = pn['bank']
        Hh, Ww = img.shape
        lum = np.zeros(img.shape); sat = np.zeros(img.shape)
        for y in range(Hh):
            for x in range(Ww):
                if img[y, x]:
                    r, g, b = rgbv(cr[(bank[y // 16, x // 16] * 256 + img[y, x]) & 0x7FF])
                    lum[y, x] = max(r, g, b); sat[y, x] = max(r, g, b) - min(r, g, b)
        txt = (lum > 90) & (sat < 60)                    # 흰 글자 + 회색 번짐까지
        x0, y0, x1, y1 = PHOTO
        txt[y0:y1, x0:x1] = False; txt[:3] = False; txt[:, :3] = False; txt[152:] = False; txt[:, 246:] = False
        # 오른쪽 끝(x246~251)에 걸친 글자 조각: 테두리선 열(행 80% 이상 밝음)을 빼고, 글자 줄이 있는 행에서만
        raw_ = (lum > 90) & (sat < 60)
        edgec = [x for x in range(246, 252) if raw_[3:152, x].mean() < 0.8]
        rows_ = np.nonzero(txt.any(1))[0]
        for x in edgec:
            txt[rows_, x] |= raw_[rows_, x]
        dil = txt.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                dil |= np.roll(np.roll(txt, dy, 0), dx, 1)
        dil[y0:y1, x0:x1] = False
        # 줄무늬 주기
        best, per = -1, 16
        clean = ~dil & (img > 0)
        for pp in range(8, 40):
            m = clean[:, pp:250] & clean[:, :250 - pp]
            sc = ((img[:, pp:250] == img[:, :250 - pp]) & m).sum() / max(1, m.sum())
            if sc > best:
                best, per = sc, pp
        new = img.copy()
        # 줄무늬 패턴: 행마다 (x mod 주기) 위치별 바탕 화소 최빈값 → 빈 자리는 사선 기울기만큼 밀린 이웃 행에서
        okpx = (img > 0) & ~dil
        okpx[y0:y1, x0:x1] = False; okpx[:, :3] = False; okpx[:, 244:] = False
        pat = np.full((Hh, per), -1, np.int64)
        for y in range(Hh):
            for r in range(per):
                xs_ = np.arange(3 + ((r - 3) % per), 240, per)
                vv = img[y, xs_][okpx[y, xs_]]
                if len(vv):
                    pat[y, r] = collections.Counter(vv.tolist()).most_common(1)[0][0]
        # 사선 기울기(윗행 대비 가로 이동)
        bs, slope = -1, 0
        for sh in range(-per // 2, per // 2):
            m = (pat[1:] >= 0) & (np.roll(pat[:-1], sh, 1) >= 0)
            sc = ((pat[1:] == np.roll(pat[:-1], sh, 1)) & m).sum() / max(1, m.sum())
            if sc > bs:
                bs, slope = sc, sh
        for it_ in range(Hh):
            changed_ = False
            for y in range(Hh):
                for r in range(per):
                    if pat[y, r] < 0:
                        for dy in (1, -1, 2, -2, 3, -3):
                            yy_ = y + dy
                            if 0 <= yy_ < Hh:
                                v_ = pat[yy_, (r - slope * dy) % per]
                                if v_ >= 0:
                                    pat[y, r] = v_; changed_ = True; break
            if not changed_:
                break
        for y, x in zip(*np.nonzero(dil)):
            v_ = pat[y, x % per]
            if v_ >= 0:
                new[y, x] = v_
        # 원래 줄 위치(글자 마스크 가로 투영)
        rows = txt.any(1); lines = []; yy = 0
        while yy < Hh:
            if not rows[yy]:
                yy += 1; continue
            a0 = yy
            while yy < Hh and rows[yy]:
                yy += 1
            xs = np.nonzero(txt[a0:yy].any(0))[0]
            lines.append((a0, yy, xs.min(), xs.max() + 1))
        # 글자 색: 흰 채움 = 글자 화소 최다 · 테두리 = 둘레 화소 중 가장 어두운 것 최다
        fillc = collections.Counter(img[txt]).most_common(1)[0][0]
        ring = dil & ~txt
        darkc = collections.Counter(img[ring & (lum < 60)]).most_common(1)
        darkc = darkc[0][0] if darkc else 0
        bk = collections.Counter(bank[[l[0] // 16 for l in lines], 1]).most_common(1)[0][0]
        nb = bank.copy()
        labs = TEXT[s]
        print('패널', s, '줄', [(a, b - a, xa, xb) for a, b, xa, xb in lines], '주기', per)
        pal_rgb = {}
        def prgb(bv):
            if bv not in pal_rgb:
                pal_rgb[bv] = np.array([rgbv(cr[(bv * 256 + i) & 0x7FF]) for i in range(256)], float)
            return pal_rgb[bv]
        for (a0, a1, xa, xb), lab in zip(lines, labs):
            h = a1 - a0
            right = (x0 - 3) if a0 < y1 else 240           # 사진 높이에 걸치는 줄은 사진 앞에서 멈춤
            fa, oa = aa_text(lab, h, right - xa)
            yy0 = a0 + (h - fa.shape[0]) // 2
            for yy, xq in zip(*np.nonzero(oa > 0.04)):
                Y, X = yy0 + yy, xa + xq
                if Y < 0 or Y >= Hh or X >= Ww:
                    continue
                bv = int(bank[Y // 16, X // 16]); Pp = prgb(bv)
                cur = Pp[new[Y, X]] if new[Y, X] else np.zeros(3)
                col = cur * (1 - oa[yy, xq])                 # 검은 테
                col = col * (1 - fa[yy, xq]) + 255 * fa[yy, xq]   # 흰 채움
                dd_ = ((Pp[1:] - col) ** 2).sum(1)           # 0 = 투명 제외
                new[Y, X] = 1 + int(np.argmin(dd_))
        # 재배치(16×16 글자 단위)
        chars = []; idx = {}; ents = []
        for i in range(pn['n']):
            y, x = divmod(i, pn['W'])
            blk = new[y * 16:y * 16 + 16, x * 16:x * 16 + 16]
            bts = b''.join(bytes(blk[dy:dy + 8, dx:dx + 8].astype(np.uint8).ravel()) for dy, dx in ((0, 0), (0, 8), (8, 0), (8, 8)))
            key = bts
            if key not in idx:
                idx[key] = len(chars); chars.append(bts)
            addr = pn['base'] + idx[key] * 256
            ents.append((int(nb[y, x]) << 12) | ((addr // 0x80) & 0xFFF))
        nbt = b''.join(chars); comp = sglz.encode(nbt); assert sglz.decode(comp, 0)[0] == nbt
        ok = len(nbt) <= len(pn['tiles']) and len(comp) <= pn['end'] - pn['off']
        print('   글자', len(chars), '/', len(pn['tiles']) // 256, '압축', len(comp), '/', pn['end'] - pn['off'], '맞음' if ok else '✗')
        if ok:
            body[pn['off']:pn['off'] + len(comp)] = comp
            body[pn['boff']:pn['boff'] + pn['n'] * 2] = struct.pack('>%dH' % pn['n'], *ents)
        def col(a):
            o = np.zeros(a.shape + (3,), np.uint8)
            for y in range(a.shape[0]):
                for x in range(a.shape[1]):
                    if a[y, x]:
                        o[y, x] = rgbv(cr[(bank[y // 16, x // 16] * 256 + a[y, x]) & 0x7FF])
            return o[:160, :256]
        pim = Image.fromarray(np.concatenate([col(img), np.full((160, 4, 3), 128, np.uint8), col(new)], 1))
        pim.resize((pim.width * 4, pim.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'nbg', 'panel_%d.png' % s))
    os.makedirs(os.path.dirname(outp), exist_ok=True); open(outp, 'wb').write(bytes(body))


if __name__ == '__main__':
    main()
