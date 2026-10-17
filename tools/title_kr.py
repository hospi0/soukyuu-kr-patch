# -*- coding: utf-8 -*-
r"""제목 로고 한글화 — TITLE/TITLE.CGB(16비트 직접색, 8×8 셀 = 값×32 B) + TITLE.PNB(2워드, 폭 64) (2026-10-17)
  蒼穹紅蓮隊 → 창궁홍련대(글자별 같은 상자) · 읽기 줄 «— そうきゅうぐれんたい —» → «— 소큐구렌타이 —».
  지우기: 글자 몸(파랑·빨강·노랑·금)+둘레 3px, 초록 줄무늬, 읽기 줄(흰) → OpenCV 메우기(TELEA).
  그리기: NotoSerifKR Black 을 원래 글자 상자에 맞춰 늘림 · 채움 = 원본 행별 색(파랑 글자 공통 / 紅 따로) · 안쪽 금테 1px + 바깥 검은 테 2px.
  줄무늬 그림자 = 새 글자(+테) 를 (+2,+19) 민 모양 − 글자, 원본 줄무늬 켜짐 행(주기 5)에만, 행별 원본 초록.
  python tools/title_kr.py [build] → 미리보기 work/title/title_preview.png(원본|새것, 실제 색) · build 면 work/out/TITLE/TITLE.CGB
"""
import collections
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DISC = os.path.join(ROOT, 'work', 'disc', 'TITLE'); OUT = os.path.join(ROOT, 'work', 'out', 'TITLE')
PRV = os.path.join(ROOT, 'work', 'title')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
COLS, ROWS = 44, 64                                   # 실제 화면 = 352×512(인터레이스) — 맵 32×32(16×16) 중 22열
KR = '창궁홍련대'
READ_KR = '창궁홍련대'                                    # 양쪽 줄표는 원본 그대로
READ_ONLY = True                                         # 2026-10-17 사용자: 로고는 원본, 아래 흰 읽기 줄만 «창궁홍련대»
SHADOW = (2, 40)                                         # 화면 세로 2배(인터레이스) 기준


TIT_MAP, TIT_END = 0x36A00, 0x275D8                     # 게임이 쓰는 제목 그림 = TIT_PNT 0x0 압축 블록(VRAM 0x0) + 맵 0x36A00(32×32, 16×16 직접색, 값×0x80)


def load():
    """게임 제목 그림(TIT_PNT) — TITLE.CGB 는 실제로 안 쓰이는 사본(화소 89% 다름)"""
    import sglz
    d = open(os.path.join(DISC, 'TIT_PNT.BIN'), 'rb').read(); t, end = sglz.decode(d, 0)
    assert end == TIT_END, hex(end)
    ents = struct.unpack('>1024H', d[TIT_MAP:TIT_MAP + 0x800])
    img = np.zeros((512, 512), np.uint16)
    for i, v in enumerate(ents):
        a = (v & 0xFFF) * 0x80; y, x = divmod(i, 32)
        for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
            o = a + k * 128
            if v and o + 128 <= len(t):
                img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = np.frombuffer(t[o:o + 128], '>u2').reshape(8, 8)
    return t, ents, img[:ROWS * 8, :COLS * 8].copy()


def to_rgb(w):
    return np.stack([(w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3], -1).astype(np.uint8)


def to555(rgb):
    r, g, b = (rgb[..., 0].astype(np.uint16) >> 3), (rgb[..., 1].astype(np.uint16) >> 3), (rgb[..., 2].astype(np.uint16) >> 3)
    return (0x8000 | (b << 10) | (g << 5) | r).astype(np.uint16)


def glyph_mask(ch, w, h):
    """한 글자 마스크를 상자(w×h)에 꽉 차게(비율 무시) — 굵기 Black"""
    f = ImageFont.truetype(FONT, 200); f.set_variation_by_name(b'Black')
    bb = f.getbbox(ch)
    im = Image.new('L', (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), 0)
    ImageDraw.Draw(im).text((-bb[0] + 2, -bb[1] + 2), ch, font=f, fill=255)
    a = np.array(im); ys, xs = np.nonzero(a > 127)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.array(Image.fromarray(a).resize((w, h), Image.LANCZOS)) > 110


def main():
    build = len(sys.argv) > 1 and sys.argv[1] == 'build'
    cg, ents, w16 = load(); rgb = to_rgb(w16).astype(int)   # cg = 풀린 TIT_PNT 그림 데이터
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    H, W = r.shape
    blue = (b > 150) & (r < 120)
    red = (r > 170) & (b < 90) & ~((g > 150) & (r < 200))
    gold = (r > 150) & (g > 130) & (b < 100)
    green = (g > 100) & (r < 90) & (b < 90)
    body = blue | red | gold
    body[262:] = False                                      # 로고 아래(지구 불빛)는 제외
    # 글자 상자: 붙어 있는 글자가 있어 가로 범위는 고정(확대 그림에서 잼), 세로는 마스크로
    runs = [(25, 78), (81, 136), (137, 217), (218, 273), (277, 328)]
    boxes = []
    for x0, x1 in runs:
        ys = np.nonzero(body[:, x0:x1].any(1))[0]
        boxes.append((x0, x1, ys.min(), ys.max() + 1))
    print('글자 상자', boxes)
    # 행별 채움 색: 파랑 글자들(0,1,3,4) · 紅(2) — 금테 제외, 몸 안쪽(침식 2px)
    inner = cv2.erode((blue | red).astype(np.uint8), np.ones((9, 5), np.uint8)) > 0
    def rowcols(ids):
        out = {}
        for y in range(H):
            px = [tuple(rgb[y, x]) for i in ids for x in range(boxes[i][0], boxes[i][1]) if inner[y, x]]
            if px:
                out[y] = np.median(np.array(px), 0)
        return out
    rc_blue = rowcols([0, 1, 3, 4]); rc_red = rowcols([2])
    def fill_at(rc, y):
        if y in rc:
            return rc[y]
        k = min(rc, key=lambda q: abs(q - y)); return rc[k]
    goldc = np.median(rgb[gold & (np.arange(H)[:, None] < 262)], 0)
    # 줄무늬: 켜짐 행 · 행별 초록
    rowon = green.sum(1) > 20
    grow = {y: np.median(rgb[y][green[y]], 0) for y in range(H) if green[y].sum() > 5}
    # 읽기 줄: 상자 아래 흰 글자
    white = (rgb.min(2) > 170)
    ry0 = max(bx[3] for bx in boxes) - 2
    rrows = np.nonzero(white[ry0:ry0 + 50, 60:300].any(1))[0]
    read_y0, read_y1 = ry0 + rrows.min(), ry0 + rrows.max() + 1
    rcols_ = np.nonzero(white[read_y0:read_y1].any(0))[0]
    read_x0, read_x1 = rcols_.min(), rcols_.max() + 1
    rr = [[rcols_[0], rcols_[0] + 1]]
    for x in rcols_[1:]:
        if x - rr[-1][1] > 4:
            rr.append([x, x + 1])
        else:
            rr[-1][1] = x + 1
    kana_x0, kana_x1 = 108, 246                            # 가나 범위 고정(세로 2배 화면에선 줄표와 가나가 붙어 자동 판정 불가) — 양쪽 줄표 원본 유지
    read_y0, read_y1 = 265, 291
    print('읽기 줄 조각', rr)
    print('읽기 줄', read_y0, read_y1, read_x0, read_x1)
    # 지우기
    er = cv2.dilate(body.astype(np.uint8), np.ones((13, 7), np.uint8)) > 0
    er |= cv2.dilate(green.astype(np.uint8), np.ones((5, 3), np.uint8)) > 0
    if READ_ONLY:
        er[:] = False
    er[read_y0 - 2:read_y1 + 2, kana_x0 - 3:kana_x1 + 3] |= cv2.dilate(white[read_y0 - 2:read_y1 + 2, kana_x0 - 3:kana_x1 + 3].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    er[read_y1 + 6:] = False
    base8 = rgb.astype(np.uint8)
    new = cv2.inpaint(base8, er.astype(np.uint8) * 255, 7, cv2.INPAINT_TELEA).astype(int)
    # 새 글자 마스크
    gm = np.zeros((H, W), bool); which = np.full((H, W), -1)
    for i, (ch, (x0, x1, y0, y1)) in enumerate(zip(KR, boxes)):
        m = glyph_mask(ch, x1 - x0 - 6, y1 - y0 - 6)
        m = np.pad(m, 1); m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0   # 원본처럼 굵게(+1px — 2px 는 속공간이 메워짐)
        if READ_ONLY:
            continue
        sub = gm[y0 + 2:y1 - 2, x0 + 2:x1 - 2]; sub |= m
        which[y0 + 2:y1 - 2, x0 + 2:x1 - 2][m] = i
    goldm = cv2.dilate(gm.astype(np.uint8), np.ones((5, 3), np.uint8)) > 0
    blackm = cv2.dilate(goldm.astype(np.uint8), np.ones((9, 5), np.uint8)) > 0
    # 줄무늬 그림자
    dx, dy = SHADOW
    sh = np.zeros_like(blackm); sh[dy:, :] = np.roll(blackm, dx, 1)[:H - dy]
    sh &= ~blackm
    sh[read_y0 - 4:read_y1 + 6, kana_x0 - 30:kana_x1 + 34] = False   # 읽기 줄(줄표 포함) 둘레엔 그림자 없음(원본과 같게)
    for y in range(H):
        if rowon[y] and y in grow:
            new[y][sh[y]] = grow[y]
    # 글자: 검은 테 → 금테 → 채움
    new[blackm] = (8, 8, 8)
    new[goldm] = goldc
    for y in range(H):
        for x in np.nonzero(gm[y])[0]:
            new[y, x] = fill_at(rc_red if which[y, x] == 2 else rc_blue, y)
    # 읽기 줄
    px_ = 12
    while True:                                           # 줄표 사이 폭(−8px)을 채우는 크기
        f = ImageFont.truetype(FONT, px_ + 1); f.set_variation_by_name(b'Black')
        bb = f.getbbox(READ_KR, stroke_width=2)
        if bb[2] - bb[0] > kana_x1 - kana_x0 - 8 or (bb[3] - bb[1]) * 2 > read_y1 - read_y0 + 8:
            break
        px_ += 1
    f = ImageFont.truetype(FONT, px_); f.set_variation_by_name(b'Black')
    bb = f.getbbox(READ_KR, stroke_width=2)
    tim = Image.new('RGBA', (bb[2] - bb[0] + 2, bb[3] - bb[1] + 2), (0, 0, 0, 0))
    ImageDraw.Draw(tim).text((-bb[0] + 1, -bb[1] + 1), READ_KR, font=f, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    tim = tim.resize((tim.width, tim.height * 2), Image.LANCZOS)   # 세로 2배(인터레이스)
    tw_ = kana_x1 - kana_x0 - 6                           # 줄표 사이를 채우게 가로로 늘림(≤1.3배)
    if tim.width != tw_:
        tim = tim.resize((tw_, tim.height), Image.LANCZOS)   # 줄표 사이를 꽉 채움
    a = np.asarray(tim).astype(float); al = a[..., 3:4] / 255
    tx = (kana_x0 + kana_x1 - tim.width) // 2; ty = (read_y0 + read_y1 - tim.height) // 2
    reg = new[ty:ty + tim.height, tx:tx + tim.width].astype(float)
    new[ty:ty + tim.height, tx:tx + tim.width] = (reg * (1 - al) + a[..., :3] * al).astype(int)
    new = np.clip(new, 0, 255).astype(np.uint8)
    os.makedirs(PRV, exist_ok=True)
    nw = to555(new); nw[w16 == 0] = 0
    chk = to_rgb(nw)
    Image.fromarray(np.concatenate([rgb.astype(np.uint8), np.full((H, 4, 3), 128, np.uint8), chk], 1)).save(os.path.join(PRV, 'title_preview.png'))
    Image.fromarray(np.concatenate([rgb.astype(np.uint8)[:320], np.full((320, 4, 3), 128, np.uint8), chk[:320]], 1)).resize(((W * 2 + 4) * 3, 480), Image.NEAREST).save(os.path.join(PRV, 'title_zoom.png'))
    if build:
        import sglz
        tb = bytearray(cg); seen = {}
        for i, v in enumerate(ents):
            y, x = divmod(i, 32)
            if not v or y * 16 >= ROWS * 8 or x * 16 >= COLS * 8:
                continue
            a = (v & 0xFFF) * 0x80
            for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                o = a + k * 128
                blk = nw[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8].astype('>u2').tobytes()
                if o in seen and seen[o] != blk:
                    print('  ⚠ 공유 칸 %X 내용 다름 (%d,%d)' % (o, y, x))
                seen[o] = blk; tb[o:o + 128] = blk
        comp = sglz.encode(bytes(tb)); assert sglz.decode(comp, 0)[0] == bytes(tb)
        print('TIT_PNT 제목 그림 압축', len(comp), '/', TIT_END)
        if len(comp) > TIT_END:
            raise SystemExit('압축 초과')
        p_ = os.path.join(OUT, 'TIT_PNT.BIN'); d_ = open(os.path.join(DISC, 'TIT_PNT.BIN'), 'rb').read()
        body = bytearray(open(p_, 'rb').read() if os.path.exists(p_) else d_)
        body[0:len(comp)] = comp
        os.makedirs(OUT, exist_ok=True); open(p_, 'wb').write(bytes(body))

if __name__ == '__main__':
    main()
