# -*- coding: utf-8 -*-
r"""기체 선택 NBG1(256색 16×16 글자) — 조종사 카드 3장 + 흐르는 띠 한글 (2026-10-17)
  JSELSP.BIN: 맵 BD 7200 @0x4 (32×32 페이지 4장 = 2×2 → 64×64 칸) · 글자 그림 GP 2000 @0x2008 (VRAM 0x20000, 256 B/글자).
  카드 글자 = 카드 안 글자 영역(인물 그림 왼쪽)의 «어둡고 채도 낮은» 화소 → 지운 자리는 행별 바탕 최빈값.
  띠 글자 = 띠 행의 «빨간» 화소 → 행별 바탕 최빈값. 글자 = NotoSerifKR(이름 Black · 나머지 Bold), 원본 줄 위치.
  재배치: 바뀐 칸만 쓰던 글자만 빈자리(맵이 안 가리키는 글자는 보호) · 압축 ≤ 원본.
  python tools/jsel1_kr.py [lines]   (lines = 줄·조각 위치만 출력)
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
import pm_detail as P  # noqa: E402
os.environ.setdefault('X_SCALE', '0.9')                # 장평 90% — 글자 자리(빈 칸 201) 안에 맞추려고
import stg_kr as K  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc'); OUT = os.path.join(ROOT, 'work', 'out')
GP_OFF, MAP_OFF, BASE = 0x2008, 0x4, 0x20000
CARDS = [(416, 512), (608, 704), (800, 896)]
CARD_X = (34, 300)                                       # 글자 영역 왼쪽~소속 줄 끝(초상화는 x≥274, 소속 줄만 283 까지)
EXTRA = {0: (496, 512, 250, 293)}                      # 카드 1 「課長」(초상화 옆)                                       # 글자 영역(인물 그림 왼쪽)
BANNER = (992, 1024)
CARD_TEXT = [
    ['=파일럿', '야시다 카오루', '', '(주)진성중공업 궤도사업부 방위2과', '과장'],
    ['=파일럿', '미카즈키 료타', '', '(주)진성중공업 궤도사업부 방위2과'],
    ['=파일럿', '쿠니무라 리카', '', '(주)진성건설 풍요의 바다 방위부 주임보'],
]
BANNER_TEXT = {'搭乗機体を選択せよ。': '탑승 기체를 선택하라.', '強制射出まであと': '강제 사출까지 앞으로', '秒': '초'}


def load():
    d = open(os.path.join(DISC, 'JSELSP.BIN'), 'rb').read()
    tiles, end = sglz.decode(d, GP_OFF)
    flat = list(struct.unpack('>4096H', d[MAP_OFF:MAP_OFF + 8192]))
    W = 64; order = []
    for k in range(4096):
        pg, i = divmod(k, 1024); py, px = divmod(pg, 2); r, x = divmod(i, 32); order.append((py * 32 + r) * W + px * 32 + x)
    ents = [0] * 4096
    for k, pos in enumerate(order):
        ents[pos] = flat[k]
    img = np.zeros((1024, 1024), np.int32); bank = np.zeros((64, 64), int)
    for i, v in enumerate(ents):
        addr = (v & 0xFFF) * 0x80 - BASE; y, x = divmod(i, W); bank[y, x] = (v >> 12) & 7
        if 0 <= addr <= len(tiles) - 256:
            ch = np.frombuffer(tiles[addr:addr + 256], np.uint8)
            for kk, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = ch[kk * 64:kk * 64 + 64].reshape(8, 8)
    return d, tiles, end, ents, order, img, bank


def rgbv(cr, b, z):
    e = cr[(b * 256 + int(z)) & 0x7FF]; return (e & 31) * 8, ((e >> 5) & 31) * 8, ((e >> 10) & 31) * 8


def lines_of(mask, y0, x0):
    rows = mask.any(1); out = []; y = 0
    while y < len(rows):
        if not rows[y]:
            y += 1; continue
        a = y
        while y < len(rows) and rows[y]:
            y += 1
        xs = np.nonzero(mask[a:y].any(0))[0]
        out.append((y0 + a, y0 + y, x0 + xs.min(), x0 + xs.max() + 1))
    return out


def aa_line(text, ink, weight):
    """NotoSerifKR 안티에일리어싱 줄 → 덮임 정도(0~1) — 「한」 잉크 높이 ≈ ink"""
    px = ink
    while True:
        f = ImageFont.truetype(K.FONT, px + 1); f.set_variation_by_name(weight)
        bh = f.getbbox('한')
        if bh[3] - bh[1] > ink:
            break
        px += 1
    f = ImageFont.truetype(K.FONT, px); f.set_variation_by_name(weight)
    bb = f.getbbox(text)
    im = Image.new('L', (bb[2] - bb[0] + 2, bb[3] - bb[1] + 2), 0)
    ImageDraw.Draw(im).text((-bb[0] + 1, -bb[1] + 1), text, font=f, fill=255)
    return np.array(im).astype(float) / 255


_GRAY = {}


def nearest_gray(cr, bv, col):
    """그 칸 뱅크 팔레트에서 회색(채도 낮은) 색 중 col 에 가장 가까운 번호"""
    if bv not in _GRAY:
        ids = [i for i in range(1, 256) if (lambda c_: max(c_) - min(c_) < 28)(rgbv(cr, bv, i))]
        _GRAY[bv] = (np.array(ids), np.array([rgbv(cr, bv, i) for i in ids], float))
    ids, cols = _GRAY[bv]
    return int(ids[np.argmin(((cols - col) ** 2).sum(1))])


def main():
    d, tiles, end, ents, order, img, bank = load()
    # 색 = PNB12.BIN(세 카드가 다 제 색인 팔레트 — s9 CRAM 은 선택 안 된 카드가 어둡게 바뀌어 있음)
    cr = np.frombuffer(open(os.path.join(DISC, 'PNB12.BIN'), 'rb').read(), '>u2').astype(int)
    new = img.copy()
    kink = np.zeros(img.shape, bool)                     # 새로 그린 한글 잉크
    origtxt = np.zeros(img.shape, bool)                  # 원래 글자(+초상화 어두운 화소) — 바탕 칸 복사 원본에서 제외
    lum = np.zeros(img.shape); sat = np.zeros(img.shape); red = np.zeros(img.shape, bool)
    for y in range(1024):
        for x in range(1024):
            z = img[y, x]
            if z:
                r, g, b = rgbv(cr, bank[y // 16, x // 16], z)
                lum[y, x] = max(r, g, b); sat[y, x] = max(r, g, b) - min(r, g, b); red[y, x] = r > 150 and g < 110 and b < 110
    only_lines = len(sys.argv) > 1 and sys.argv[1] == 'lines'
    for ci, (cy0, cy1) in enumerate(CARDS):
        x0, x1 = CARD_X
        reg = img[cy0:cy1, x0:x1]
        dk = (reg > 0) & (lum[cy0:cy1, x0:x1] < 140) & (sat[cy0:cy1, x0:x1] < 70)
        txt = dk.copy(); txt[:, 262 - x0:] = False
        ls0 = lines_of(txt, cy0, x0)
        la, lb = ls0[-1][0] - cy0, ls0[-1][1] - cy0       # 맨 아래 소속 줄은 283 까지
        txt[la:lb, :283 - x0] = dk[la:lb, :283 - x0]
        if ci in EXTRA:
            ea, eb, ex0, ex1 = EXTRA[ci]
            txt[ea - cy0:eb - cy0, ex0 - x0:ex1 - x0] = dk[ea - cy0:eb - cy0, ex0 - x0:ex1 - x0]
        origtxt[cy0:cy1, x0:x1] = dk
        ls = lines_of(txt, cy0, x0)
        print('카드', ci + 1, [(a, b - a, xa, xb) for a, b, xa, xb in ls])
        if only_lines:
            continue
        # 줄 «=뒤말» = 왼쪽 덩어리(S.O.Q-004 등 영문 번호)는 원본 유지, 가장 큰 틈 오른쪽만 바꿈
        spans = []
        for (a, b, xa, xb), t in zip(ls, CARD_TEXT[ci]):
            if t.startswith('='):
                cs = np.nonzero(txt[a - cy0:b - cy0].any(0))[0] + x0
                gi = int(np.argmax(np.diff(cs))); xa = int(cs[gi + 1]); t = t[1:]
                txt[a - cy0:b - cy0, :xa - 2 - x0] = False
            spans.append((a, b, xa, xb, t))
        # 지우기: 줄 상자(±2 px) 안 «바탕과 다른 무채색» 화소 전부 → 행 바탕 최빈값(흐린 가장자리까지)
        sub = new[cy0:cy1, x0:x1]
        lsat = sat[cy0:cy1, x0:x1]
        for (a, b, xa, xb, t) in spans:
            for yy in range(max(cy0, a - 2) - cy0, min(cy1, b + 2) - cy0):
                Yr = cy0 + yy
                # 행 바탕 = 실제 색(RGB) 최빈값 — 행 안에 팔레트(뱅크)가 다른 칸이 섞여 있어 번호로 정하면 파랗게 나옴
                cols_ = collections.Counter(rgbv(cr, bank[Yr // 16, (x0 + q) // 16], reg[yy, q]) for q in range(x1 - x0) if reg[yy, q] and not txt[yy, q])
                if not cols_:
                    continue
                bgrgb = np.array(cols_.most_common(1)[0][0], float)
                xa_, xb_ = xa - 2 - x0, min(xb + 2, 293) - x0
                for q in range(xa_, xb_):
                    X = x0 + q
                    if q + x0 >= 262 and not (b >= 480 + (cy0 - 416)):   # 위쪽 줄은 초상화 앞(262)까지
                        continue
                    z = reg[yy, q]
                    if not z or lsat[yy, q] >= 70:
                        continue
                    bv = int(bank[Yr // 16, X // 16])
                    if np.abs(np.array(rgbv(cr, bv, z), float) - bgrgb).sum() < 12:
                        continue
                    sub[yy, q] = nearest_gray(cr, bv, bgrgb)
        # 색: 칸 뱅크별로 그 뱅크 글자 화소 최빈값
        bk_ = np.repeat(np.repeat(bank[cy0 // 16:cy1 // 16], 16, 0), 16, 1)[:, x0:x1]
        darkb = {}
        for bv in np.unique(bk_[txt]):
            darkb[int(bv)] = collections.Counter(reg[txt & (bk_ == bv)].tolist()).most_common(1)[0][0]
        dflt = collections.Counter(reg[txt].tolist()).most_common(1)[0][0]
        for (a, b, xa, xb, t) in spans:
            if not t:
                continue
            h = b - a
            al = aa_line(t, h - 3 if h >= 20 else h - 2, b'Black' if h >= 20 else b'Bold')
            lim_ = (xb - 46) if xa > (x0 + x1) // 2 and h < 20 and xa > 240 else ((262 if b < cy1 - 20 else 283) - xa)
            if al.shape[1] > lim_:
                al = np.array(Image.fromarray((al * 255).astype(np.uint8)).resize((lim_, al.shape[0]), Image.LANCZOS)).astype(float) / 255
            right = xa > 240
            xx = (xb - al.shape[1]) if right else xa
            ya = a + (h - al.shape[0]) // 2
            for yy, xq in zip(*np.nonzero(al > 0.06)):
                Y, X = ya + yy, xx + xq
                bv = int(bank[Y // 16, X // 16])
                tgt = np.array(rgbv(cr, bv, darkb.get(bv, dflt)), float)
                cur = np.array(rgbv(cr, bv, new[Y, X]), float) if new[Y, X] else np.array([248, 248, 248], float)
                col = cur * (1 - al[yy, xq]) + tgt * al[yy, xq]
                new[Y, X] = nearest_gray(cr, bv, col); kink[Y, X] = True
    # 흐르는 띠
    by0, by1 = BANNER
    reg = img[by0:by1]; txt = red[by0:by1]
    cols = np.nonzero(txt.any(0))[0]; runs = [[cols[0], cols[0] + 1]]
    for x in cols[1:]:
        if x - runs[-1][1] > 12:
            runs.append([x, x + 1])
        else:
            runs[-1][1] = x + 1
    print('띠 조각', [(a, b - a) for a, b in runs])
    if only_lines:
        return
    BAN = {40: '탑승 기체를 선택하라.', 313: '강제 사출까지 앞으로', 563: '초', 616: '탑승 기체를 선택하라.', 889: '강제 사출까지 앞으로'}   # 889 = 313 + 주기 576 사본(1024 에서 잘림) — 같게 그려 글자 칸 공유
    redc = collections.Counter(reg[txt].tolist()).most_common(1)[0][0]
    ty_ = np.nonzero(txt.any(1))[0]; TY0, TY1 = ty_.min() - 1, ty_.max() + 2
    for yy in range(by1 - by0):
        bgv = collections.Counter(reg[yy][~txt[yy] & (reg[yy] > 0)].tolist()).most_common(1)
        row = new[by0 + yy]
        for a0, a1 in runs:
            if a0 in BAN and bgv and TY0 <= yy < TY1:
                xa_, xb_ = max(0, a0 - 3), min(1024, a1 + 3)
                seg = reg[yy, xa_:xb_] != bgv[0][0]
                row[xa_:xb_][seg] = bgv[0][0]
    ty = np.nonzero(txt.any(1))[0]; ta, tb = by0 + ty.min(), by0 + ty.max() + 1
    for a0, a1 in runs:
        if a0 not in BAN:
            continue
        K.WEIGHT = b'Black'
        m = K.render_line(K.line_mask(BAN[a0]), tb - ta - 1); K.WEIGHT = None
        ref = {889: (313, 486), 616: (40, 284)}.get(a0)      # 사본은 원본 조각과 같은 폭으로(같은 그림 → 칸 공유)
        lim = (ref[1] - ref[0]) if ref else (a1 - a0)
        if m.shape[1] > lim:
            m = K.squeeze(m, lim)
        for k_ in range(min(m.shape[1], 1024 - a0)):    # 원본처럼 1024 에서 잘림(감기지 않음 — x17 은 「″」 기호)
            xk = a0 + k_; col_ = m[:, k_] > 0
            new[ta:ta + m.shape[0], xk][col_] = redc; kink[ta:ta + m.shape[0], xk] |= col_
    # 지우기만 한 칸(한글 잉크 없음) → 같은 칸 행에서 손대지 않은 «글자 없는» 바탕 칸을 통째로 복사(기존 글자 공유)
    origtxt[BANNER[0]:BANNER[1]] = red[BANNER[0]:BANNER[1]]
    for cy in range(64):
        for cx in range(64):
            sl = (slice(cy * 16, cy * 16 + 16), slice(cx * 16, cx * 16 + 16))
            if not (new[sl] != img[sl]).any() or kink[sl].any():
                continue
            for dx in list(range(1, 64)):
                done = False
                for nx in (cx - dx, cx + dx):
                    if 0 <= nx < 64:
                        s2 = (slice(cy * 16, cy * 16 + 16), slice(nx * 16, nx * 16 + 16))
                        if cy * 16 < BANNER[0] and nx * 16 + 16 <= 272 and bank[cy, nx] == bank[cy, cx] and not origtxt[s2].any() and (img[s2] > 0).all() and not (new[s2] != img[s2]).any():   # 띠는 제외(틈 무늬 칸이 들어옴)
                            new[sl] = img[s2]; done = True; break
                if done:
                    break
    # 재배치(16×16 글자 = 256 B 단위)
    nch = len(tiles) // 256; CH = [tiles[i * 256:(i + 1) * 256] for i in range(nch)]
    def chbytes(a, y, x):
        blk = a[y * 16:y * 16 + 16, x * 16:x * 16 + 16]
        return b''.join(bytes(blk[dy:dy + 8, dx:dx + 8].astype(np.uint8).ravel()) for dy, dx in ((0, 0), (0, 8), (8, 0), (8, 8)))
    cidx = lambda v: ((v & 0xFFF) * 0x80 - BASE) // 256
    changed = {}
    for i, v in enumerate(ents):
        y, x = divmod(i, 64)
        if not (new[y * 16:y * 16 + 16, x * 16:x * 16 + 16] != img[y * 16:y * 16 + 16, x * 16:x * 16 + 16]).any():
            continue
        changed[i] = chbytes(new, y, x)
    keep = collections.Counter(cidx(v) for i, v in enumerate(ents) if i not in changed and 0 <= cidx(v) < nch)
    was = {cidx(ents[i]) for i in changed if 0 <= cidx(ents[i]) < nch}
    free = sorted(c for c in was if not keep[c]); have = {CH[c]: c for c in range(nch) if keep[c]}; used = {}
    newents = list(ents)
    for i, bts in sorted(changed.items()):
        if bts in have:
            c = have[bts]
        elif bts in used:
            c = used[bts]
        else:
            if not free:
                need = len(set(changed.values()) - set(have))
                # 진단: 카드/띠별·바탕만인 칸
                cat = collections.Counter()
                for i2, b2 in changed.items():
                    y2 = i2 // 64 * 16
                    where = '띠' if y2 >= BANNER[0] else ('카드%d' % (1 + [k_ for k_, (a_, b_) in enumerate(CARDS) if a_ <= y2 < b_][0]) if any(a_ <= y2 < b_ for a_, b_ in CARDS) else '기타')
                    cat[where] += 1
                print('  바뀐 칸 분포', dict(cat), '고유 새 글자', need)
                raise SystemExit('글자 자리 부족: 필요 %d 빈자리 %d' % (need, len(used)))
            c = free.pop(0); CH[c] = bts; used[bts] = c
        newents[i] = (ents[i] & 0xF000) | (((BASE + c * 256) // 0x80) & 0xFFF)
    nb = b''.join(CH); comp = sglz.encode(nb); assert sglz.decode(comp, 0)[0] == nb
    if len(comp) > end - GP_OFF:
        raise SystemExit('압축 초과 %d > %d' % (len(comp), end - GP_OFF))
    outp = os.path.join(OUT, 'JSELSP.BIN')
    body = bytearray(open(outp, 'rb').read() if os.path.exists(outp) else d)
    body[GP_OFF:GP_OFF + len(comp)] = comp
    flat = [0] * 4096
    for k, pos in enumerate(order):
        flat[k] = newents[pos]
    body[MAP_OFF:MAP_OFF + 8192] = struct.pack('>4096H', *flat)
    open(outp, 'wb').write(bytes(body))
    print('바뀐칸', len(changed), '새글자', len(used), '남은빈자리', len(free), '압축', len(comp), '/', end - GP_OFF)
    def col(a, oy=0):
        o = np.zeros(a.shape + (3,), np.uint8)
        for y in range(a.shape[0]):
            for x in range(a.shape[1]):
                if a[y, x]:
                    o[y, x] = rgbv(cr, bank[(y + oy) // 16, x // 16], a[y, x])
        return o
    parts = []
    for (y0_, y1_) in CARDS + [BANNER]:
        parts.append(np.concatenate([col(img[y0_:y1_, :1024 if y0_ == BANNER[0] else 400], y0_), np.full((y1_ - y0_, 4, 3), 128, np.uint8), col(new[y0_:y1_, :1024 if y0_ == BANNER[0] else 400], y0_)], 1))
    W_ = max(p_.shape[1] for p_ in parts)
    parts = [np.pad(p_, ((0, 4), (0, W_ - p_.shape[1]), (0, 0))) for p_ in parts]
    Image.fromarray(np.concatenate(parts)).save(os.path.join(ROOT, 'work', 'nbg', 'jsel1_preview.png'))


if __name__ == '__main__':
    main()
