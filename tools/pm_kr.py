# -*- coding: utf-8 -*-
r"""연습 메뉴 상세 본문 18장 한글 그림 + 재배치 (2026-10-17)
  화면은 세로 2배 인터레이스(LSMD=3) → 글자를 «가로 1 : 세로 2» 로: Galmuri9 BDF 를 찍고 각 행을 두 번(원본 글자 ≈ 8.5×17).
  배치: 원본 줄 위치(줄 간격 ≈ 21.5px)·단(왼 x4~180 / 오른 x184~364) 그대로. 머리 n줄 = 왼쪽 단 첫 n줄(오른쪽 맞춤이던 줄은 오른쪽 맞춤),
        본문 = 남은 왼쪽 단 줄 → 오른쪽 단 줄 → (넘치면) 마지막 단 아래로 같은 간격 줄 추가.
  기체 페이지(34·36·38): 왼쪽 위 머리 영역의 S.O.Q 번호는 그대로, 읽기 줄 지움, 큰 이름 = NotoSerifKR Black(세로 2배).
  색: 본문·머리 = 원래 줄의 칸 팔레트 · 채움 15(흰) · 테두리 3(어두운 회색) 1px.
  재배치: 페이지마다 새 그림으로 타일 세트를 처음부터(빈 타일 0번 + 고유 타일) → 타일 수 ≤ 원본, 압축 ≤ 원본 길이.
  python tools/pm_kr.py  → work/pm/kr/<파일>_<목차>.png(원본|새것) · work/out/PMENU/<파일>(맵·GF 제자리)
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
import pm_layout as LY  # noqa: E402
from bdf import Font  # noqa: E402

G9 = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf')
NOTO = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
FILL, EDGE = 15, 3
USE_EDGE = int(os.environ.get('PM_EDGE', '0'))   # 테두리 — 넣으면 타일 수가 원본을 넘음(뒤 VRAM 0x70800~ 은 메뉴 머리 글자)
TRACK = int(os.environ.get('PM_TRACK', '0'))   # 글자 간격 조정(px)
COLS = [(4, 181), (184, 365)]
PITCH = 21.5
OUT = os.path.join(ROOT, 'work', 'out')


def g9_draw(text):
    """Galmuri9 + 글자 간격 조정(TRACK)"""
    pts, x = [], 0
    for ch in text:
        pp, w = G9.draw(ch)
        pts += [(px + x, py) for px, py in pp]
        x += w + (TRACK if ch != ' ' else 0)
    return pts, x


def text_layer(text):
    """Galmuri9 한 줄 → (세로 2배) 0/1 배열"""
    pts, w = g9_draw(text)
    if not pts:
        return np.zeros((2, max(1, w)), bool)
    h = max(y for x, y in pts) + 1
    a = np.zeros((h, max(w, max(x for x, y in pts) + 1)), bool)
    for x, y in pts:
        a[y, x] = True
    return np.repeat(a, 2, axis=0)


def width(text):
    return g9_draw(text)[1]


def wrap(text, w):
    """낱말 단위(넘치는 낱말은 글자 단위)로 줄 나눔"""
    out, cur = [], ''
    for wd in text.split(' '):
        t = (cur + ' ' + wd) if cur else wd
        if width(t) <= w:
            cur = t; continue
        if cur:
            out.append(cur); cur = ''
        while width(wd) > w:                           # 긴 낱말 쪼개기
            k = len(wd)
            while k > 1 and width(wd[:k]) > w:
                k -= 1
            out.append(wd[:k]); wd = wd[k:]
        cur = wd
    if cur:
        out.append(cur)
    return out


def big_name(text, w, h):
    """큰 이름: NotoSerifKR Black, 화면 비율로 맞춘 뒤 세로 2배"""
    hh = h // 2
    for size in range(hh + 10, 6, -1):
        f = ImageFont.truetype(NOTO, size); f.set_variation_by_name(b'Black')
        im = Image.new('L', (int(f.getlength(text)) + 8, size * 2), 0); ImageDraw.Draw(im).text((4, 0), text, font=f, fill=255)
        a = np.array(im) > 110; ys, xs = np.nonzero(a)
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if a.shape[1] <= w and a.shape[0] <= hh:
            return np.repeat(a, 2, axis=0)
    return np.repeat(a, 2, axis=0)


def outline(m):
    p = np.pad(m, 1); o = np.zeros_like(p)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(p, dy, 0), dx, 1)
    return (o & ~p)[1:-1, 1:-1]


def put(canvas, pal, m, x, y, palv, fill=FILL, edge=EDGE):
    h, w = m.shape
    y = max(0, int(y)); x = max(0, int(x))
    sub = canvas[y:y + h, x:x + w]; mm = m[:sub.shape[0], :sub.shape[1]]
    if USE_EDGE:
        ol = outline(np.pad(mm, 1))[1:-1, 1:-1]
        sub[ol & ~mm] = edge
    sub[mm] = fill
    for cy in range(y // 8, min(pal.shape[0], (y + h + 7) // 8)):
        for cx in range(x // 8, min(64, (x + w + 7) // 8)):
            if (canvas[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] > 0).any():
                pal[cy, cx] = palv


def load_kr():
    kr = collections.defaultdict(dict)
    for ln in open(os.path.join(ROOT, 'work', 'text', 'kr_pm_detail.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f, k, part, txt = ln.split('\t')[:4]
        kr[(f, int(k))][part] = txt
    return kr


def render_page(f, k, tr):
    p = LY.page(f, k); img = p['img']; pal = p['pal'].copy()
    two = (img[:, 186:] > 0).any()
    cols = COLS if two else COLS[:1]
    lines = {c: LY.lines(img, *c) for c in cols}
    heads = [tr[key] for key in sorted(t for t in tr if t.startswith('머리'))]
    body = tr.get('본문', '')
    new = np.zeros_like(img)
    machine = f == 'PM_JIK.BIN' and k in (34, 36, 38)
    L = list(lines[cols[0]])
    if machine:
        # 왼쪽 단 첫 «줄» = 머리 영역(높이 60 넘음): S.O.Q 번호 그대로, 읽기 줄 지움, 큰 이름 새로
        hy0, hy1 = L[0][0], L[0][1]
        reg = img[hy0:hy1, :181] > 0
        tall = np.nonzero(reg.sum(0) > 45)[0]              # 세로로 길게(45행 넘게) 잉크가 있는 열 = 큰 이름(작은 두 줄 쌓인 열은 ~32행)
        bx0 = tall.min() - 2
        sub = reg[:, :bx0]
        ys = np.nonzero(sub.any(1))[0]
        gaps = [y for y in range(ys.min(), ys.max()) if not sub[y].any()]
        cut = gaps[0] if gaps else ys.max()
        small_x1 = bx0
        new[hy0:hy0 + cut, :small_x1] = img[hy0:hy0 + cut, :small_x1]   # S.O.Q 번호 그대로
        big = [bx0 + 2, 181]
        bm = big_name(heads[1], 181 - big[0] - 2, hy1 - hy0)
        put(new, pal, bm, 180 - bm.shape[1], hy0 + (hy1 - hy0 - bm.shape[0]) // 2, pal[(hy0 + hy1) // 16, big[0] // 8], fill=FILL, edge=EDGE)
        slots = [(a, b) for a, b, x0, x1 in L[1:]]
        hdr = []
    else:
        nh = len(heads)
        hdr = L[:nh]; slots = [(a, b) for a, b, x0, x1 in L[nh:]]
        for (a, b, x0, x1), t in zip(hdr, heads):
            m = text_layer(t); cx0, cx1 = cols[0]
            right = x0 > (cx0 + cx1) // 2 - 20 and x1 > cx1 - 12     # 오른쪽 맞춤이던 줄
            x = (x1 - m.shape[1]) if right else x0
            if m.shape[1] > cx1 - cx0 - 4:                 # 단 폭 넘으면 가로로 눌러 넣음(자르지 않음)
                w_ = cx1 - cx0 - 4
                m = m[:, (np.arange(w_) * m.shape[1] // w_)]
                x = (x1 - m.shape[1]) if right else x0
            palv = collections.Counter(p['pal'][a // 8:(b + 7) // 8, x0 // 8:(x1 + 7) // 8].ravel()).most_common(1)[0][0]
            put(new, pal, m, x, a + (b - a - m.shape[0]) // 2, palv)
    # 본문 줄 자리: 왼쪽 단 남은 줄 + 오른쪽 단 줄
    allslots = [(cols[0], s) for s in slots]
    if two:
        allslots += [(cols[1], (a, b)) for a, b, x0, x1 in lines[cols[1]]]
    wmax = cols[0][1] - cols[0][0] - 4
    blines = wrap(body, wmax)
    H = min(img.shape[0], int(allslots[-1][1][1]) + 10) if allslots else img.shape[0]   # 상자 안(원래 마지막 줄 +10)까지만
    while len(allslots) < len(blines):                  # 넘치면 마지막 단 아래로 같은 간격
        c, (a, b) = allslots[-1]
        na = a + PITCH
        if na + 18 > H:
            break
        allslots.append((c, (na, na + 18)))
    over = len(blines) - len(allslots)
    if over > 0:                                       # 마지막 단의 줄을 페이지 끝까지 고르게 다시 나눔
        c_last = allslots[-1][0]
        idx = [i for i, (c, s) in enumerate(allslots) if c == c_last]
        top = allslots[idx[0]][1][0]
        need = len(idx) + over
        pitch = (H - 18 - top) / max(1, need - 1)
        if pitch < 19:                                 # 줄 간격이 너무 좁으면 실패 → 번역 줄일 것
            need19 = int((H - 18 - top) // 19) + 1
            return p, new, pal, dict(본문줄=len(blines), 자리=len(allslots), 넘침=need - need19)
        allslots = allslots[:idx[0]] + [(c_last, (top + q * pitch, top + q * pitch + 18)) for q in range(need)]
        over = len(blines) - len(allslots)
    bodypal = collections.Counter(p["pal"][[int(s[1][0]) // 8 for s in allslots[:3]], 1:20].ravel()).most_common(1)[0][0] if allslots else 14
    for (c, (a, b)), t in zip(allslots, blines):
        m = text_layer(t)
        put(new, pal, m, c[0] + 2, a + (b - a - m.shape[0]) // 2, bodypal)
    return p, new, pal, dict(본문줄=len(blines), 자리=len(allslots), 넘침=max(0, over))


def rebuild(p, new, pal):
    """새 그림 → 타일 세트(0 = 빈 타일 + 고유) · 맵 값 = (팔레트<<12) | (0x580 + 번호)"""
    tiles = [bytes(32)]; idx = {bytes(32): 0}; ents = []
    for r in range(new.shape[0] // 8):
        for x in range(64):
            blk = new[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
            b = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
            if b not in idx:
                idx[b] = len(tiles); tiles.append(b)
            ents.append((int(pal[r, x]) << 12) | (0x580 + idx[b]))
    nb = b''.join(tiles)
    comp = sglz.encode(nb)
    assert sglz.decode(comp, 0)[0] == nb
    return ents, nb, comp


def main():
    kr = load_kr()
    os.makedirs(os.path.join(ROOT, 'work', 'pm', 'kr'), exist_ok=True)
    outs = {}
    import read_lines as R
    cr = P.cram_of('s7')
    rgb = lambda e: np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)
    global TRACK
    for ln in open(os.path.join(ROOT, 'work', 'pm', 'valid.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f, k, _ = ln.split('\t'); k = int(k)
        for TRACK in (0,):                              # 간격 0 고정(사용자: 간격 좁히지 말고 번역을 줄일 것)
            p, new, pal, rep = render_page(f, k, kr[(f, k)])
            ents, nb, comp = rebuild(p, new, pal)
            nt_old = len(p['tiles']) // 32; nt_new = len(nb) // 32
            ok = nt_new <= nt_old and len(comp) <= p['end'] - p['go'] and len(ents) * 2 == p['go'] - p['bo'] and rep['넘침'] == 0
            rep.update(타일=(nt_new, nt_old), 압축=(len(comp), p['end'] - p['go']), 맞음=ok, 간격=TRACK)
            if ok:
                break
        print(f, k, rep, flush=True)
        if ok:
            body = bytearray(outs.get(f, p['d']))
            body[p['bo']:p['go']] = struct.pack('>%dH' % len(ents), *ents)
            body[p['go']:p['go'] + len(comp)] = comp
            outs[f] = bytes(body)
        # 미리보기(원본 | 새것) — 세로 2배 화면이라 표시는 세로 절반
        def col(a, pp):
            o = np.zeros(a.shape + (3,), np.uint8) + np.array((40, 10, 10), np.uint8)
            for r in range(a.shape[0] // 8):
                for x in range(46):
                    blk = a[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
                    cc = rgb(cr[((0x70 + pp[r, x]) * 16 + blk) & 0x7FF]); cc[blk == 0] = (40, 10, 10)
                    o[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = cc
            return o[:, :368]
        a = col(p['img'], p['pal']); b = col(new, pal)
        im = Image.fromarray(np.concatenate([a, np.full((a.shape[0], 6, 3), 128, np.uint8), b], 1))
        im = im.resize((im.width * 2, im.height), Image.NEAREST)
        im.save(os.path.join(ROOT, 'work', 'pm', 'kr', '%s_%02d.png' % (f[:-4], k)))
    for f, data in outs.items():
        pth = os.path.join(OUT, 'PMENU', f); os.makedirs(os.path.dirname(pth), exist_ok=True); open(pth, 'wb').write(data)


if __name__ == '__main__':
    main()
