# -*- coding: utf-8 -*-
r"""저장 안내 화면(BUP/RAM1~7.CGB, 16비트 직접색) 한글화 (2026-10-17)
  그림 = BUP_PNT 화면 0 맵(32×32, 16×16 글자, 값×128 B, 셀 4개 왼위·오른위·왼아래·오른아래) — 616칸 전부 고유 → 셀 제자리 수정.
  지우기: 흰 글자(최소 채널 >150) + 둘레 4px → OpenCV 메우기(TELEA). 그리기: NotoSerifKR Black(「한」 잉크 제목 22 · 본문 16px) 흰 채움 + 검은 2px 테두리.
  줄 = 원래 줄 위치(y 위·높이). 폭 넘치면 가로 0.78 까지 줄이고 그래도 넘치면 크기 축소.
  '|' = 코드가 숫자를 그리는 빈틈: 앞 조각은 틈 시작 전에서 끝나게, 뒤 조각은 원래 「の」 자리에서 시작.
  python tools/bup_kr.py → work/out/BUP/RAM1~7.CGB · 미리보기 work/bup/ram<n>.png(원본|새것)
"""
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DISC = os.path.join(ROOT, 'work', 'disc', 'BUP'); OUT = os.path.join(ROOT, 'work', 'out', 'BUP')
PRV = os.path.join(ROOT, 'work', 'bup')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
T, B = 'T', 'B'                                      # 제목(원래 줄 높이 ≈28) · 본문(≈20)
L_RESET = [(B, 'L 또는 R 버튼을 누른 채 리셋 버튼을 누르면'), (B, '세가새턴 본체의 저장 데이터 관리 화면으로 이동합니다.')]
START = '이대로 게임을 시작하려면 스타트 버튼을 눌러 주십시오.'
START2 = '게임을 시작하려면 스타트 버튼을 눌러 주십시오.'
# 줄: (원래 줄 y, 종류, 글, 맞춤) — 맞춤 'R' = 원래 줄 오른쪽 끝에 맞춤 · 빈틈 줄 = (y, B, '앞|뒤', (틈 시작, 뒤 시작))
LAYOUT = {
    1: [(54, T, '백업 RAM이 아직 준비되지 않았습니다.'), (91, T, '(초기화되지 않았습니다)', 'R'),
        (155, B, '세가새턴 본체의 저장 데이터 관리 화면에서'), (183, B, '모든 기록을 지워 주십시오.(초기화해 주십시오)'),
        (236,) + L_RESET[0], (263,) + L_RESET[1]],
    2: [(43, T, '기록을 저장할 빈 용량이 부족합니다.'), (109, B, '이대로 게임을 시작하면 「창궁홍련대」의'),
        (136, B, '기록은 저장할 수 없습니다.', 'R'),
        (189, B, '메인 데이터를 저장하려면|의 공간이 필요합니다.', (172, 220)),
        (243, B, '연습 데이터를 저장하려면|의 공간이 필요합니다.', (161, 221)),
        (298, B, START), (352,) + L_RESET[0], (383,) + L_RESET[1]],
    3: [(60, T, '백업 RAM에 기록을 제대로'), (97, T, '저장하지 못했습니다.'), (157, B, START2),
        (211,) + L_RESET[0], (237,) + L_RESET[1]],
    4: [(53, T, '기록을 제대로 읽어 들이지'), (89, T, '못했습니다.'), (176, B, '이대로는 기록을 저장할 수 없습니다.'),
        (230, B, START2), (283,) + L_RESET[0], (310,) + L_RESET[1]],
    5: [(37, T, '「창궁홍련대」의 기록을'), (73, T, '본체와 카트리지 RAM 중'), (110, T, '어디에 저장하시겠습니까?'),
        (169, B, 'A·B·C 중 아무 버튼이나 누르면 본체 RAM에,'), (196, B, 'X·Y·Z 중 아무 버튼이나 누르면 카트리지 RAM에'),
        (223, B, '저장합니다.')],
    6: [(48, T, '기록을 저장할 빈 용량이 부족합니다.'), (113, B, '이대로 게임을 시작하면 연습 데이터가 저장되지 않습니다.'),
        (167, B, '저장하려면|의 공간이 필요합니다.', (93, 145)), (221, B, START), (275,) + L_RESET[0], (307,) + L_RESET[1]],
    7: [(49, T, '기록을 저장할 빈 용량이 부족합니다.'), (113, B, '이대로 게임을 시작하면 메인 데이터가 저장되지 않습니다.'),
        (167, B, '저장하려면|의 공간이 필요합니다.', (93, 144)), (222, B, START), (277,) + L_RESET[0], (308,) + L_RESET[1]],
}
X0, XMAX = 16, 338                                   # 왼쪽 시작 · 오른쪽 끝(원본 최대 338)


def ents():
    mp = open(os.path.join(DISC, 'BUP_PNT.BIN'), 'rb').read()
    return struct.unpack('>1024H', mp[:2048])


def compose(cg, en):
    img = np.zeros((512, 512), np.uint16)
    for i, v in enumerate(en):
        if not v:
            continue
        y, x = divmod(i, 32)
        for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
            o = v * 128 + k * 128
            img[y * 16 + dy:y * 16 + dy + 8, x * 16 + dx:x * 16 + dx + 8] = np.frombuffer(cg[o:o + 128], '>u2').reshape(8, 8)
    return img


def to_rgb(w):
    return np.stack([(w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3], -1).astype(np.uint8)


def to555(rgb):
    r, g, b = (rgb[..., 0].astype(np.uint16) >> 3), (rgb[..., 1].astype(np.uint16) >> 3), (rgb[..., 2].astype(np.uint16) >> 3)
    return (0x8000 | (b << 10) | (g << 5) | r).astype(np.uint16)


def font(px, weight):
    f = ImageFont.truetype(FONT, px); f.set_variation_by_name(weight); return f


def text_img(t, kind, maxw):
    """RGBA 줄 그림 — 「한」 잉크 높이 ≈ 목표(제목 22 · 본문 15). 폭 넘치면 가로 축소(≥0.78) → 그래도 넘치면 크기 축소"""
    ink = 22 if kind == T else 16
    weight = b'Black'
    px = ink
    while True:                                      # 「한」 잉크 높이가 목표에 닿는 크기
        bh = font(px + 1, weight).getbbox('한')
        if bh[3] - bh[1] > ink:
            break
        px += 1
    while True:
        f = font(px, weight)
        bb = f.getbbox(t, stroke_width=2)
        w, h = bb[2] - bb[0] + 2, bb[3] - bb[1] + 2
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((-bb[0] + 1, -bb[1] + 1), t, font=f, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        if w <= maxw:
            return im, f.getbbox('한')[1] - bb[1] + 1
        if w * 0.78 <= maxw:
            return im.resize((maxw, h), Image.LANCZOS), f.getbbox('한')[1] - bb[1] + 1
        px -= 1


def paste(base, im, x, y):
    a = np.asarray(im).astype(float); al = a[..., 3:4] / 255
    h, w = a.shape[:2]
    reg = base[y:y + h, x:x + w].astype(float)
    base[y:y + h, x:x + w] = (reg * (1 - al[:reg.shape[0], :reg.shape[1]]) + a[:reg.shape[0], :reg.shape[1], :3] * al[:reg.shape[0], :reg.shape[1]]).astype(np.uint8)


def lines_of(rgb):
    white = rgb.min(2) > 180
    rows = white.any(1); out = []; y = 0
    while y < len(rows):
        if rows[y]:
            a = y
            while y < len(rows) and rows[y]:
                y += 1
            xs = np.nonzero(white[a:y].any(0))[0]
            if y - a > 3:
                out.append((a, y - a, xs.min(), xs.max()))
        else:
            y += 1
    return out


def main():
    en = ents(); os.makedirs(OUT, exist_ok=True); os.makedirs(PRV, exist_ok=True)
    for n, lay in LAYOUT.items():
        cg = open(os.path.join(DISC, 'RAM%d.CGB' % n), 'rb').read()
        w16 = compose(cg, en); rgb = to_rgb(w16)
        orig = lines_of(rgb); oy = {a: (h, x0, x1) for a, h, x0, x1 in orig}
        assert sorted(oy) == sorted(e[0] for e in lay), (n, sorted(oy), [e[0] for e in lay])
        white = (rgb.min(2) > 150).astype(np.uint8)
        mask = cv2.dilate(white, np.ones((9, 9), np.uint8))
        mask[416:] = 0
        new = cv2.inpaint(rgb, mask * 255, 6, cv2.INPAINT_TELEA)
        for e in lay:
            y, kind, t = e[0], e[1], e[2]
            h, ox0, ox1 = oy[y]
            if '|' in t:
                a_, b_ = t.split('|'); g0, g1 = e[3]
                im, top = text_img(a_, kind, g0 - 4 - ox0); paste(new, im, ox0, y + (h - im.height) // 2 + 1)
                im, top = text_img(b_, kind, XMAX - g1); paste(new, im, g1, y + (h - im.height) // 2 + 1)
                continue
            im, top = text_img(t, kind, XMAX - ox0)
            x = (ox1 + 2 - im.width) if (len(e) > 3 and e[3] == 'R') else ox0
            paste(new, im, max(4, x), y + (h - im.height) // 2 + 1)
        nw = to555(new); nw[w16 == 0] = 0
        out = bytearray(cg)
        for i, v in enumerate(en):
            if not v:
                continue
            yy, xx = divmod(i, 32)
            for k, (dy, dx) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                o = v * 128 + k * 128
                out[o:o + 128] = nw[yy * 16 + dy:yy * 16 + dy + 8, xx * 16 + dx:xx * 16 + dx + 8].astype('>u2').tobytes()
        open(os.path.join(OUT, 'RAM%d.CGB' % n), 'wb').write(bytes(out))
        chk = to_rgb(compose(bytes(out), en))
        Image.fromarray(np.concatenate([rgb[:416, :352], np.full((416, 4, 3), 128, np.uint8), chk[:416, :352]], 1)).save(os.path.join(PRV, 'ram%d.png' % n))
        print('RAM%d' % n, '줄', len(lay), '바뀐 바이트', sum(1 for a, b in zip(cg, out) if a != b))


if __name__ == '__main__':
    main()
