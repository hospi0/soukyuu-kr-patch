# -*- coding: utf-8 -*-
r"""이어하기 화면(継続可能 + 팁 6개) 한글 그림 — 미리보기 전용 단계 (2026-10-17)
  자료: STG_?/STG?_DAT.BIN = [맵 64칸×N줄, 0x28 부터][GF 글자 그림(→VRAM 0x78000)]. 맵 칸 번호 = (v&0xFFF)|0x3000, 팔레트 = 0x60 + (v>>12).
  게임은 맵의 팁 블록(6줄)을 화면 NBG3 20~25행으로 복사(스테이트 s14 확인). 継続可能·CONTINUE? 도 같은 맵 안.
  스타일(메모리 기본값): 채움 한 색 + 글자 둘레 1px 테두리 · 글꼴 NotoSerifKR(팁 Bold·머리 Black) 안티앨리어싱 없이 · 위치는 잉크 경계 기준.
  python tools/cont_kr.py [스테이지문자=B]   → work/cont/preview_<X>.png (원본 | 새것, 실제 CRAM 색 + s14 배경층)
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

DISC = os.path.join(ROOT, 'work', 'disc')
FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'   # 팁 = Bold · 머리 = Black (원본 명조와 가장 가까움, 2026-10-17 비교)
# 스테이지별 [파일, GF 위치] — 맵(머리 9행 + 팁 6×6행 = 45행)은 GF 바로 앞(GF − 0x1680)
T_DANGER = '위험할 때는 봄버를 아끼지 않는 것이 중요.'
T_ONEPT = '한 곳만 조준할 수 있는 적에게 레이저는 효과적이지 않다.'
T_MULTI = '레이저는 한 번에 여러 곳을 조준해야 위력을 발휘한다.'
T_BOMBS = '봄버와 확산 봄버를 구분해 쓰는 데 주의.'
T_HOMING = '적의 추적 공격은 돌아 들어가듯 피하는 것이 요령.'
T_MINMOVE = '적탄을 최소한의 움직임으로 피해 다음 공격에 대비한다.'
T_PRESAGE = '적의 레이저 공격에는 반드시 전조가 있다.'
T_DEPTH = '적기가 화면 안쪽이나 앞쪽에 있을 때 파괴하는 것이 중요.'
T_INVINC = '봄버는 발사한 순간 무적이 된다.'
T_ITEM = '아이템은 놓치지 말고 챙기는 것이 좋다.'
STAGES = {
    'B': ('STG_B/STGB_DAT.BIN', 0x92A8, [T_DANGER, T_ONEPT, '적의 공격을 외우고 대책을 세우면 실력이 는다.', T_INVINC,
                                         '적탄을 충분히 끌어당겨 피하는 것이 중요한 테크닉.', '누구나 처음에는 초보자. 계속하면 실력이 는다.']),
    'O': ('STG_O/STGO_DAT.BIN', 0x190C, [T_PRESAGE, T_MULTI, T_DEPTH, '조준 중에 봄버를 발사하면 확산 봄버가 된다.', T_HOMING, T_MINMOVE]),
    'C': ('STG_C/STGC_DAT.BIN', 0x18E8, [T_BOMBS, '아이템을 놓치지 않으면 고득점을 얻을 수 있다.', T_ITEM,
                                         '계속은 힘. 얻은 경험을 다음에 살리는 것이 중요.', '추적 레이저를 쓰면 공략의 폭이 넓어진다.', T_ONEPT]),
    'A': ('STG_A/STGA_DAT.BIN', 0x1798, ['작전 중의 적을 전멸시키면 고득점을 얻을 수 있다.', '위력과 공격 범위에 따라 레이저를 구분해 쓰는 것이 중요.',
                                         '봄버는 적에게 직접 맞혀야 진정한 위력을 발휘한다.', '대형 적에 부딪혀도 죽지는 않는다.',
                                         '샷 공격만으로 앞으로 나아가기는 어렵다.', T_MINMOVE]),
    'S': ('STG_S/STGS_DAT.BIN', 0x1774, [T_DANGER, T_ONEPT, T_MULTI, T_BOMBS, T_HOMING, '적탄을 충분히 끌어당겨 피하는 것도 중요한 테크닉.']),
    'L': ('STG_L/STGL_ANY.BIN', 0x9F04, [T_PRESAGE, T_DEPTH, T_INVINC, '전 스테이지 클리어까지 앞으로 한 걸음. 자신의 한계에 도전하라',
                                         '전 스테이지 클리어까지 앞으로 한 걸음. 자신의 한계에 도전하라', T_ITEM]),
}
TIP_ROWS, NTIP = 6, 6
MAP_HEAD = {'O': 0x28E}
# 아래 값은 load() 가 스테이지마다 채움
GF_OFF = {X: v[1] for X, v in STAGES.items()}
MAP0 = 0x28
TIP0 = 257
HEAD = (246, 257)
TIPS = STAGES['B'][2]
HEAD_KR = "계속 가능"
HEAD_SHRINK = int(os.environ.get("HEAD_SHRINK", "8"))   # 「계속 가능」을 원본 잉크 높이보다 작게(px) — 하스피 «너무 커서 잘린다»
WORD_GAP = 3                                     # 띄어쓰기를 글꼴 기본보다 넓힘(px)
TIP_SIZE = int(os.environ.get("TIP_SIZE", "21"))   # 팁 글자 크기
TIP_EDGE = int(os.environ.get("TIP_EDGE", "0"))      # 팁 1px 테두리 — 0(원본처럼 없음): 테두리를 넣으면 타일 자리 부족(코드용 카운트다운 숫자 타일은 못 씀)
TIP_X = int(os.environ.get("TIP_X", "16"))         # 줄 시작 x — 타일 경계(8의 배수)에 맞추면 걸치는 칸이 준다
TIP_DY = int(os.environ.get("TIP_DY", "0"))         # 줄 위 여백(픽셀) — 타일 3행(24px) 안에 들어가게


def load(X):
    global MAP0, TIP0, HEAD, TIPS
    path, go, TIPS = STAGES[X]
    d = open(os.path.join(DISC, path), 'rb').read()
    tiles, end = sglz.decode(d, go)
    head = MAP_HEAD.get(X, go - 0x1680)          # 머리 줄 시작(2스테이지는 2바이트 뒤 — 마지막 칸이 GF 첫 2바이트와 겹침)
    MAP0 = head % 128; h = (head - MAP0) // 128
    HEAD = (max(0, h - 2), h + 9); TIP0 = h + 9
    m = d[MAP0:go]
    ents = list(struct.unpack('>%dH' % (len(m) // 2), m[:len(m) // 2 * 2]))
    ents += [0xFFFF] * (-len(ents) % 64)            # GF 와 겹쳐 잘린 칸 = 안 쓰는 칸(화면 밖 63열)
    # ★머리 줄(h) 위 2행은 맵이 아니다 — 스테이지 물체 표·팔레트(3스테이지 0x168~ 물체 표를 ec00 으로 덮어 도중 크래시, 2026-10-18)
    ents[:h * 64] = [0xFFFF] * (h * 64)
    return d, go, end, tiles, ents


def cell_px(tiles, e):
    o = ((e & 0xFFF) | 0x3000) * 0x20 - 0x78000
    if not 0 <= o <= len(tiles) - 32:
        return None
    a = np.frombuffer(tiles[o:o + 32], np.uint8)
    return np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8).astype(int)


def region_index(tiles, ents, r0, r1):
    """맵 r0~r1 행 → (색 번호 그림, 칸별 팔레트)"""
    img = np.zeros(((r1 - r0) * 8, 512), int); pal = np.zeros((r1 - r0, 64), int)
    for r in range(r0, r1):
        for x in range(64):
            e = ents[r * 64 + x]
            px = cell_px(tiles, e) if e and e != 0xFFFF else None
            pal[r - r0, x] = e >> 12
            if px is not None:
                img[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8] = px
    return img, pal


def font(size, weight=b'Bold'):
    f = ImageFont.truetype(FONT, size); f.set_variation_by_name(weight); return f


def text_mask(text, size, width_px, weight=b'Bold'):
    """한 색(이진) 글자 — 폭을 넘으면 낱말 단위로 줄바꿈. 줄마다 같은 기준(문장 안 가장 높은 글자 위끝)으로 위를 자르고 좌우는 잉크로 자른 마스크 목록"""
    f = font(size, weight)
    top = min(f.getbbox(ch)[1] for ch in text if ch.strip())   # 문장 안 가장 높은 글자 기준 — «가» 기준이면 계·속 윗부분이 잘림(하스피 지적 2026-10-17)
    sp = f.getlength(' ') + WORD_GAP
    L = lambda ws: sum(f.getlength(w) for w in ws) + sp * (len(ws) - 1)
    words = text.split(' ')
    if L(words) <= width_px:
        lines = [words]
    else:                                             # 두 줄: 두 줄 폭이 가장 비슷한 낱말 경계에서(«쓰는 데 / 주의.» 같은 꼬리 방지)
        best = None
        for k in range(1, len(words)):
            a_, b_ = words[:k], words[k:]
            if L(a_) <= width_px and L(b_) <= width_px:
                sc = max(L(a_), L(b_))
                if best is None or sc < best[0]:
                    best = (sc, [a_, b_])
        if best:
            lines = best[1]
        else:                                         # 두 줄로 안 되면 앞에서부터 채움
            lines, cur = [], []
            for w in words:
                if not cur or L(cur + [w]) <= width_px:
                    cur.append(w)
                else:
                    lines.append(cur); cur = [w]
            lines.append(cur)
    out = []
    for ws in lines:
        w = int(L(ws)) + 6; h = size * 2 + 8                 # 넉넉히 — size+8 이면 굵은 받침 아래가 잘림
        im = Image.new('L', (w, h), 0); dr = ImageDraw.Draw(im); x = 2
        for wd in ws:
            dr.text((x, 0), wd, font=f, fill=255); x += f.getlength(wd) + sp
        a = np.array(im) > 110
        xs = np.nonzero(a.any(0))[0]
        ys = np.nonzero(a.any(1))[0]
        out.append(a[top:ys[-1] + 1, xs[0]:xs[-1] + 1])
    return out


def fit_head(text, ink_h, weight=b'Black'):
    """잉크 높이가 원본 이하가 되는 가장 큰 크기로 한 줄 (잉크로 잘라 반환)"""
    for size in range(ink_h + 16, 8, -1):
        m = text_mask(text, size, 999, weight)[0]
        ys = np.nonzero(m.any(1))[0]
        if ys[-1] - ys[0] + 1 <= ink_h:
            return m[ys[0]:ys[-1] + 1]


def outline(mask):
    m = np.pad(mask, 1)
    o = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return (o & ~m)[1:-1, 1:-1]


def draw_lines(canvas, masks, x0, y0, pitch, fill, edge):
    for i, m in enumerate(masks):
        h, w = m.shape; y = y0 + i * pitch
        sub = canvas[y:y + h, x0:x0 + w]
        mm = m[:sub.shape[0], :sub.shape[1]]
        ol = outline(np.pad(mm, 1))[1:-1, 1:-1]
        if edge is not None:
            sub[ol] = edge
        sub[mm] = fill


def main():
    X = sys.argv[1] if len(sys.argv) > 1 else 'B'
    d, go, end, tiles, ents = load(X)
    c = P.cram_of('s14')
    rgb = lambda e: np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)
    # 팁 블록 원본/새것 (팔레트 14 고정: 1=흰 F8F8F8, 4=회 404040)
    r0, r1 = HEAD[0], TIP0 + TIP_ROWS * NTIP
    orig, pal = region_index(tiles, ents, r0, r1)
    new = orig.copy()
    # 지우기: 머리(継続可能 줄들만 — CONTINUE? 는 그대로)·팁 전부
    ink_rows = [y for y in range(orig.shape[0]) if (orig[y, :352] > 0).any()]
    new[:, :] = np.where(np.isin(np.arange(new.shape[0])[:, None] // 8 + r0, range(TIP0, r1)), 0, new)
    # 継続可能 영역: CONTINUE? 위쪽까지
    cont_top = None
    for y in range((TIP0 - r0) * 8 - 1, -1, -1):
        if not (orig[y, :352] > 0).any():
            cont_top = y; break
    hs = (TIP0 - 9 - r0) * 8                           # 머리 줄 시작(그 위는 다른 그림일 수 있음 — 2스테이지)
    rows_head = (orig[hs:cont_top, :352] > 0).any(1).nonzero()[0] + hs
    hy0, hy1 = rows_head[0], rows_head[-1] + 1
    # CONTINUE? 줄은 잉크 덩어리 두 개 중 아래 것 — 継続可能 = 위 덩어리
    gaps = [y for y in range(hy0, hy1) if not (orig[y, :352] > 0).any()]
    cut = gaps[0] if gaps else hy1
    head_box = (hy0, cut)
    xs = (orig[hy0:cut, :352] > 0).any(0).nonzero()[0]
    new[hy0:cut, :] = 0
    # 머리: 원본 잉크 높이보다 HEAD_SHRINK px 작게, 원래 칸 안 세로 가운데(위아래 테두리 1px 포함해도 칸 밖으로 안 나감)
    hm = fit_head(HEAD_KR, cut - hy0 - HEAD_SHRINK)
    hy = hy0 + (cut - hy0 - hm.shape[0]) // 2
    draw_lines(new, [hm], (xs[0] + xs[-1]) // 2 - hm.shape[1] // 2, hy, 0, 15, 8)
    for k, t in enumerate(TIPS):
        y0 = (TIP0 + k * TIP_ROWS - r0) * 8
        ms = text_mask(t, TIP_SIZE, 326)
        draw_lines(new, ms, TIP_X, y0 + TIP_DY, 24, 1, 4 if TIP_EDGE else None)
    # 미리보기
    def col(img):
        out = np.zeros(img.shape + (3,), np.uint8) + np.array((24, 8, 40), np.uint8)
        for r in range(img.shape[0] // 8):
            for x in range(64):
                p = 0x60 + pal[r, x]
                blk = img[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
                cc = rgb(c[(p * 16 + blk) & 0x7FF]); cc[blk == 0] = (24, 8, 40)
                out[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = cc
        return out[:, :352]
    a, b = col(orig), col(new)
    sep = np.zeros((a.shape[0], 6, 3), np.uint8) + 128
    im = Image.fromarray(np.concatenate([a, sep, b], 1)); im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    os.makedirs(os.path.join(ROOT, 'work', 'cont'), exist_ok=True)
    p = os.path.join(ROOT, 'work', 'cont', 'preview_%s_v3.png' % X); im.save(p); print(p, '머리', head_box, '팁 줄수', [(len(m), max(x.shape[1] for x in m)) for m in (text_mask(t, TIP_SIZE, 326) for t in TIPS)])
    np.save(os.path.join(ROOT, 'work', 'cont', 'new_%s.npy' % X), new)


if __name__ == '__main__':
    main()


def rebuild(X='B'):
    """새 그림(work/cont/new_X.npy)을 타일로 쪼개 → 바뀐 칸만 새 타일, 안 쓰이게 된 타일 자리 재사용 → (새 맵 바이트, 새 타일, 압축, 보고)"""
    d, go, end, tiles, ents = load(X)
    new = np.load(os.path.join(ROOT, 'work', 'cont', 'new_%s.npy' % X))
    r0, r1 = HEAD[0], TIP0 + TIP_ROWS * NTIP
    nt = len(tiles) // 32
    T = [tiles[i * 32:i * 32 + 32] for i in range(nt)]
    blank_e = collections.Counter(ents[TIP0 * 64:(TIP0 + 1) * 64]).most_common(1)[0][0]
    # 바꿀 칸 = 영역 안에서 원본 칸과 새 그림이 다른 칸
    def tidx(e):
        return ((e & 0xFFF) | 0x3000) - 0x3C00
    changed = {}
    for r in range(r0, r1):
        for x in range(64):
            blk = new[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8]
            b = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
            e = ents[r * 64 + x]
            if e == 0xFFFF:
                continue
            if e == 0 and not any(b):                 # 값 0 칸(빈칸)은 글자가 들어올 때만 바꾼다 — 건너뛰면 글자 윗줄이 잘림(2026-10-17)
                continue
            ti = tidx(e)
            if e and 0 <= ti < nt and T[ti] == b:
                continue
            changed[(r, x)] = b
    keep = collections.Counter()
    for i, e in enumerate(ents):
        if e in (0, 0xFFFF):
            continue
        if divmod(i, 64) in changed:
            continue
        ti = tidx(e)
        if 0 <= ti < nt:
            keep[ti] += 1
    # 빈자리 = «바뀐 칸만 쓰던» 타일뿐. 맵이 안 가리키는 타일은 코드가 직접 쓰는 글자(카운트다운 숫자 등)일 수 있어 절대 안 건드림(2026-10-17)
    was = collections.Counter(tidx(ents[r * 64 + x]) for (r, x) in changed if ents[r * 64 + x] not in (0, 0xFFFF))
    free = sorted(i for i in was if 0 <= i < nt and not keep[i])
    have = {T[i]: i for i in range(nt) if keep[i]}
    newents = list(ents); used_new = {}
    for (r, x), b in sorted(changed.items()):
        if not any(b):
            newents[r * 64 + x] = blank_e; continue
        if b in have:
            ti = have[b]
        elif b in used_new:
            ti = used_new[b]
        else:
            if not free:
                raise SystemExit('타일 자리 부족: 바뀐칸 %d 새타일 %d 빈자리 %d(전체 %d) 남은 바뀐칸 %d' % (len(changed), len(used_new), len([i for i in range(nt) if not keep[i]]), nt, len(changed)))
            ti = free.pop(0); T[ti] = b; used_new[b] = ti
        palbits = (ents[r * 64 + x] & 0xF000) if ents[r * 64 + x] else (blank_e & 0xF000)
        newents[r * 64 + x] = palbits | ((0x3C00 + ti) & 0xFFF)
    nt_bytes = b''.join(T)
    # 왕복 검사: 새 맵 + 새 타일로 다시 그린 영역 == 새 그림 (화소 하나라도 다르면 중단)
    for r in range(r0, r1):
        for x in range(64):
            e = newents[r * 64 + x]
            blk = new[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8]
            if e in (0, 0xFFFF):
                if blk.any():
                    raise SystemExit('왕복 불일치(빈칸에 글자): 행 %d 칸 %d' % (r, x))
                continue
            o = tidx(e) * 32
            t = np.frombuffer(nt_bytes[o:o + 32], np.uint8); px = np.stack([t >> 4, t & 15], 1).ravel().reshape(8, 8)
            if not (px == blk).all():
                raise SystemExit('왕복 불일치: 행 %d 칸 %d' % (r, x))
    comp = sglz.encode(nt_bytes)
    assert sglz.decode(comp, 0)[0] == nt_bytes
    rep = dict(바뀐칸=len(changed), 새타일=len(used_new), 남은빈자리=len(free), 원본압축=end - go, 새압축=len(comp))
    return struct.pack('>%dH' % len(newents), *newents), nt_bytes, comp, rep
