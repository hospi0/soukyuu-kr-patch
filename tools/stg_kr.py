# -*- coding: utf-8 -*-
r"""게임 안 문구(스테이지 출격 전·중간·결과) 한글 그림 (2026-10-17)
  입력: tools/stg_items.py 의 항목 목록 + 번역 지정 work/text/stg_spec_<X>.tsv (번호<TAB>지정)
  지정 문법: 빈칸 = 지움(읽기 줄 등) · '=' = 그대로 · 줄바꿈 '\n' · '{높이}' = 이후 글자 잉크 높이(아래 맞춤) ·
            줄 앞 '+N' = N px 들여쓰기 · 줄 앞 '>' = 오른쪽 맞춤 · '⇥' = 원래 틈(6px 넘는) 위치로 나눠 배치('=' 조각은 원본 유지)
  스타일: 원본 항목의 채움색·테두리색(색 번호)·칸 팔레트 그대로, 한 색 + 테두리 1px(원본 테두리색이 채움과 다를 때).
          글꼴 NotoSerifKR(잉크 높이 36 이상 Black, 그 밖 Bold), 폭이 넘치면 가로 압축(최소 70%) 뒤 크기 줄임.
  python tools/stg_kr.py <X|all>  → work/stg/kr_<X>.npz(세트별 새 색번호 그림) + 미리보기 work/stg/kr_preview_<X>.png
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import stg_blocks as S  # noqa: E402
import stg_items as I  # noqa: E402

FONT = r'C:\Windows\Fonts\NotoSerifKR-VF.ttf'
MIN_SQ = 0.70
SNAP = int(os.environ.get('SNAP', '1'))       # 1 = 가로만 8px 격자 · 2 = 가로세로
EDGE = int(os.environ.get('EDGE', '1'))       # 테두리 1px
X_SCALE = float(os.environ.get('X_SCALE', '1'))     # 장평
BIG_SCALE = float(os.environ.get('BIG_SCALE', '1'))   # 높이 36 이상 조각 배율
ITEM_FILL = {}
WEIGHT = None
# «표시 칸»으로 잘못 잡힌 큰 이름 괄호 」 세로 막대(4행 연속 외톨이 칸) — 되살리지 않고 지움.
#   3스테이지 결과 「呑竜」: 이름을 옮겨 그려서 원래 막대가 위에 남음(2026-10-18 실기 «돈류»). 항목 분해(stg_items)는 그대로 둬 번호 유지.
NOT_MARKER = {'C': {(37, 43), (38, 43), (39, 43), (40, 43)}, 'L': {(37, 40), (38, 40), (39, 40), (40, 40)}}
# 원본 조각 자리 그대로 그리기 {(스테이지, 항목): [(지정 글, 높이, x0, y0, x1, y1) 그룹 좌표]} — '{h~}' = 둘째 채움(흰), '{h}' = 첫째 채움(붉은)
#   6스테이지 중간 «高高度中継/滞空攻撃機「爆鐵」»: 흰 두 줄 x82~198(y10~31·33~54) + 붉은 이름 x202~326 y10~54 (2026-10-18 실기: 줄·이름 잘림)
CUSTOM = {('L', 9): [('{18~}고고도 중계', 18, 82, 10, 199, 32), ('{18~}부공 공격기', 18, 82, 33, 199, 55), ('{40}「바쿠잔」', 40, 202, 10, 327, 55)],
          # 6스테이지 격파·실패: 붉은 이름 x82~206 y2~45 · 흰 撃破(x210~254)/撃破失敗(x210~301) y26~46 — 따로 복사(2026-10-18 실기 «격파 잘림»)
          ('L', 12): [('{40}「바쿠잔」', 40, 82, 2, 207, 46), ('{18~}격파', 18, 210, 26, 255, 47)],
          ('L', 15): [('{40}「바쿠잔」', 40, 82, 2, 207, 46), ('{18~}공격 실패', 18, 210, 26, 302, 47)]}                                # 굵기 강제(인터레이스 화면은 높이를 반으로 그려서 판정이 어긋남)


def font(size, weight):
    f = ImageFont.truetype(FONT, size); f.set_variation_by_name(weight); return f


def glyph_mask(text, ink_h, weight=None):
    """잉크 높이(「한」 기준 글자 몸) ≈ ink_h 인 이진 마스크(위 기준 = 문장 안 가장 높은 글자, 아래 = 잉크)"""
    weight = weight or WEIGHT or (b'Black' if ink_h >= 36 else b'Bold')
    best = None
    for size in range(max(6, ink_h - 6), ink_h * 2):
        f = font(size, weight)
        bb = f.getbbox('한')
        if bb[3] - bb[1] >= ink_h:
            best = f; break
    f = best or font(ink_h, weight)
    w = int(f.getlength(text)) + 8; h = f.size * 2 + 8
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((4, 2), text, font=f, fill=255)
    a = np.array(im) > 110
    if not a.any():
        return np.zeros((ink_h, 1), bool), 0
    ys, xs = np.nonzero(a)
    ref = f.getbbox('한'); base = 2 + ref[3]              # 기준선(「한」 아래끝)
    top = min(ys.min(), 2 + ref[1])
    m = a[top:max(ys.max() + 1, base), xs.min():xs.max() + 1]
    return m, base - top                                  # 마스크, 위에서 기준선까지 거리


def line_mask(line):
    """'{h}' / '{h~}'(둘째 채움색) 조각 → [(글, 높이|None, 둘째색?)]"""
    parts = re.split(r'\{(\d+)(~|@\d+)?\}', line)
    segs = []
    if parts[0]:
        segs.append((parts[0], None, None))
    for k in range(1, len(parts), 3):
        if parts[k + 2]:
            segs.append((parts[k + 2], int(parts[k]), parts[k + 1]))
    return segs


def render_line(segs, default_h, gap=5):
    """조각들을 기준선 맞춰 가로로 이음 → 색 번호 층(0 = 없음, 1 = 첫째 채움, 2 = 둘째 채움)"""
    ms = []
    segs = [(t, (int(h * BIG_SCALE) if h and h >= 36 else h), a) for t, h, a in segs]   # 큰 이름만 줄임(타일 자리 절약)
    for t, h, alt in segs:                           # 색 층: 1 = 채움 · 2 = 둘째 채움(~) · 100+k = 항목 k 채움(@k)
        m, b = glyph_mask(t, h or default_h)
        ms.append((m, b, 2 if alt == '~' else (100 + int(alt[1:]) if alt else 1)))
    asc = max(b for m, b, c in ms); desc = max(m.shape[0] - b for m, b, c in ms)
    W = sum(m.shape[1] for m, b, c in ms) + gap * (len(ms) - 1)
    out = np.zeros((asc + desc, W), np.uint8); x = 0
    for m, b, c in ms:
        sub = out[asc - b:asc - b + m.shape[0], x:x + m.shape[1]]; sub[m] = c; x += m.shape[1] + gap
    if X_SCALE != 1:                                 # 장평(가로 배율) — 한글이 원문보다 길어 타일 자리가 모자랄 때
        out = squeeze(out, max(1, int(out.shape[1] * X_SCALE)))
    return out


def squeeze(m, w, h=None):
    """색 번호 층을 가로(와 세로) 줄임 — 최근접(색 번호 보존)"""
    h = h or m.shape[0]
    w = min(w, m.shape[1])
    if w == m.shape[1] and h == m.shape[0]:
        return m
    return np.array(Image.fromarray(m.astype(np.uint8)).resize((max(1, w), max(1, h)), Image.NEAREST))


def outline(m):
    p = np.pad(m, 1); o = np.zeros_like(p)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(p, dy, 0), dx, 1)
    return (o & ~p)[1:-1, 1:-1]


def load_spec(X):
    p = os.path.join(ROOT, 'work', 'text', 'stg_spec_%s.tsv' % X)
    sp = {}
    for ln in open(p, encoding='utf-8').read().splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        k, _, v = ln.partition('\t')
        sp[int(k)] = v.replace('\\n', '\n')
    return sp


def build(X):
    its, grp, ents, T = I.items(X)
    sp = load_spec(X)
    ITEM_FILL.clear(); ITEM_FILL.update({j: it['fill'] for j, it in enumerate(its)})
    missing = [j for j in range(len(its)) if j not in sp]
    if missing:
        raise SystemExit('%s 지정 없음: %s' % (X, missing))
    canv = {}                                              # grp → (원본 색번호, 새 색번호, 팔레트 행렬)
    for g, (r0, r1, k) in enumerate(grp):
        img = S.render_rows(ents, r0, r1, T[k])
        canv[g] = [img, img.copy(), I.pal_rows(ents, r0, r1)]
    markers = {}
    for g, (r0, r1, k) in enumerate(grp):
        markers[g] = I.marker_cells(ents, r0, r1)
    # 1) 지울 항목(지정 ≠ '=') 화소 지우기 — 항목 상자 안의 «그 항목 잉크»만(표시 칸 제외)
    for j, it in enumerate(its):
        if sp[j] == '=':
            continue
        g = it['grp']; img, new, pal = canv[g]
        box = new[it['y0']:it['y1'], it['x0']:it['x1']]
        keep = np.zeros_like(box, bool)
        if '⇥' in sp[j]:
            pass
        box[img[it['y0']:it['y1'], it['x0']:it['x1']] > 0] = 0
        for (r, x) in markers[g]:                          # 표시 칸은 되살림
            if (r, x) in NOT_MARKER.get(it['stage'], ()) or x in (10, 25, 43, 48):   # 「」 세로 막대 오판 열(결과 화면 큰 이름 괄호) — 되살리지 않음
                continue
            rr = (r - grp[g][0]) * 8
            new[rr:rr + 8, x * 8:x * 8 + 8] = img[rr:rr + 8, x * 8:x * 8 + 8]
    # 2) 그리기
    for j, it in enumerate(its):
        v = sp[j]
        if v in ('=', ''):
            continue
        g = it['grp']; img, new, pal = canv[g]
        if (X, j) in CUSTOM:                               # 원본 조각 자리 그대로(게임이 흰 줄·붉은 이름을 따로 복사)
            for txt, h, bx0, by0, bx1, by1 in CUSTOM[(X, j)]:
                m = render_line(line_mask(txt), h)
                if m.shape[1] > bx1 - bx0:
                    m = squeeze(m, bx1 - bx0)
                if m.shape[0] > by1 - by0:
                    m = squeeze(m, m.shape[1], by1 - by0)
                xx = bx0 + (bx1 - bx0 - m.shape[1]) // 2; yy = by0 + (by1 - by0 - m.shape[0]) // 2
                snap_, K_SNAP = globals()['SNAP'], None
                globals()['SNAP'] = 0
                place(new, pal, m, yy, xx, it['fill'], it['edge'], it['pal'], 0, it['alt'])
                globals()['SNAP'] = snap_
            continue
        # 오른쪽 한계: 이 항목 x1 과, 같은 줄 높이에 걸친 «지운» 항목들의 x1 중 큰 값 (+10%)
        if it['set'] == 'PRE' or os.environ.get('STRICT_ALL') == '1':
            right = (it['x1'] + 7) // 8 * 8            # 출격 전: 원래 글자 칸 끝까지만(게임이 그 칸 범위만 화면에 복사 — 넘치면 잘림)
        else:
            right = max(it['x1'], 352)                 # 결과 화면 등: 같은 줄 다음 항목 앞(없으면 화면 끝)
        for k2, it2 in enumerate(its):
            if k2 != j and it2['grp'] == g and sp[k2] != '' and it2['y0'] < it['y1'] and it2['y1'] > it['y0'] and it2['x0'] >= it['x1'] - 2:
                right = min(right, it2['x0'] - 6)
        right = max(right, it['x1'])
        lines = v.split('\n'); n = len(lines)
        hs = []
        rendered = []
        for ln in lines:
            ind = 0; right_al = False
            mm = re.match(r'^\+(\d+)', ln)
            if mm:
                ind = int(mm.group(1)); ln = ln[mm.end():]
            if ln.startswith('>'):
                right_al = True; ln = ln[1:]
            if ln.startswith('^'):                     # 위 맞춤(읽기 줄이 붙어 있던 큰 이름)
                right_al = 'top'; ln = ln[1:]
            dh = it['h'] if n == 1 else max(8, int(it['h'] / n) - 1)
            if '⇥' in ln:
                rendered.append(('tab', ln.split('⇥'), dh, ind, right_al)); hs.append(dh); continue
            ma2 = re.match(r'^(.*?)((?:\{\d+~?\})?「[^」]*」)(.*)$', ln) if ('「' in ln and not ln.startswith('@') and not ln.startswith('작전')) else None
            if ma2 and n == 1 and re.match(r'^\{(\d+)', ma2.group(2)) and int(re.match(r'^\{(\d+)', ma2.group(2)).group(1)) >= 30:   # 큰 이름(30px 이상)만
                g_ = it['grp']; src_ = canv[g_][0][it['y0']:it['y1'], it['x0']:it['x1']]
                cn_ = it['alt'] if re.match(r'^\{\d+~\}', ma2.group(2)) else it['fill']   # 큰 이름 색: ~ = 둘째 채움
                red_ = src_ == cn_
                if red_.sum() >= 40:
                    ys_, xs_ = np.nonzero(red_)
                    bb_ = (it['x0'] + xs_.min(), it['y0'] + ys_.min(), it['x0'] + xs_.max() + 1, it['y0'] + ys_.max() + 1)
                    rendered.append(('auto', (ma2.group(1), ma2.group(2), ma2.group(3), bb_), dh, ind, right_al)); hs.append(dh); continue
            ms_ = re.match(r'^@(\d+)\|(.*)§(.*)$', ln)
            if ms_:                                    # '@X|앞§뒤' = 앞은 X 에서 끝나게(오른쪽 맞춤), 뒤는 X 부터 — 게임이 뒤 덩어리를 따로 복사하는 줄
                ma_ = render_line(line_mask(ms_.group(2)), dh); mb_ = render_line(line_mask(ms_.group(3)), dh)
                rendered.append(('split', (int(ms_.group(1)), ma_, mb_), dh, ind, right_al)); hs.append(max(ma_.shape[0], mb_.shape[0])); continue
            m = render_line(line_mask(ln), dh)
            rendered.append(('m', m, dh, ind, right_al)); hs.append(m.shape[0])
        total = sum(hs); gapy = (it['h'] - total) / (n - 1) if n > 1 else 0
        y = it['y0']
        fill, edge = it['fill'], it['edge']
        for kind, m, dh, ind, right_al in rendered:
            if kind == 'auto':                         # 큰 「이름」 = 원래 빨간 글자 범위 안(게임이 그 범위를 따로 복사) · 앞 글은 그 앞, 뒤 글은 그 뒤
                pre_, nm_, post_, (bx0, by0, bx1, by1) = m
                hm = re.match(r'^\{(\d+)~?\}', nm_); Hn = int(hm.group(1)) if hm else dh
                mn = render_line(line_mask(nm_ if hm else '{%d~}' % dh + nm_), Hn)
                bw, bh = bx1 - bx0, by1 - by0
                if mn.shape[0] > bh:
                    mn = squeeze(mn, max(1, int(mn.shape[1] * bh / mn.shape[0])), bh)
                if mn.shape[1] > bw:
                    mn = squeeze(mn, bw) if mn.shape[1] * MIN_SQ <= bw else squeeze(mn, bw, int(mn.shape[0] * bw / (mn.shape[1] * MIN_SQ)))
                nx = bx0 + max(0, (bw - mn.shape[1]) // 2); ny = by0 + max(0, (bh - mn.shape[0]) // 2)
                snap_, globals()['SNAP'] = SNAP, 0
                place(new, pal, mn, ny, nx, fill, edge, it['pal'], grp[g][0], it['alt'])
                yb = it['y1']
                if pre_.strip():
                    mp = render_line(line_mask(pre_), dh)
                    lim_ = bx0 - 2 - it['x0']
                    if mp.shape[1] > lim_:
                        mp = squeeze(mp, lim_)
                    place(new, pal, mp, min(yb, by1) - mp.shape[0], bx0 - 2 - mp.shape[1], fill, edge, it['pal'], grp[g][0], it['alt'])
                if post_.strip():
                    mq = render_line(line_mask(post_), dh)
                    mk_ = re.search(r'@(\d+)', post_)
                    if mk_ and its[int(mk_.group(1))]['grp'] == g:     # 뒤 글 = 항목 k 의 원래 자리(게임이 그 덩어리를 따로 복사)
                        ik = its[int(mk_.group(1))]
                        lim_ = (ik['x1'] + 7) // 8 * 8 - ik['x0']
                        if mq.shape[1] > lim_:
                            mq = squeeze(mq, lim_)
                        place(new, pal, mq, ik['y1'] - mq.shape[0], ik['x0'], fill, edge, it['pal'], grp[g][0], it['alt'])
                    else:
                        lim_ = right - bx1 - 2
                        if mq.shape[1] > lim_ > 8:
                            mq = squeeze(mq, lim_)
                        place(new, pal, mq, min(yb, by1) - mq.shape[0], bx1 + 2, fill, edge, it['pal'], grp[g][0], it['alt'])
                globals()['SNAP'] = snap_
                y += dh + gapy; continue
            if kind == 'split':
                X_, ma_, mb_ = m
                hh_ = max(ma_.shape[0], mb_.shape[0])
                if ma_.shape[1] > X_ - it['x0'] - 2:
                    ma_ = squeeze(ma_, X_ - it['x0'] - 2)
                if mb_.shape[1] > right - X_:
                    mb_ = squeeze(mb_, right - X_)
                yb_ = int(round(y)) + (it['h'] - hh_ if n == 1 else 0)
                place(new, pal, ma_, yb_ + hh_ - ma_.shape[0], X_ - 2 - ma_.shape[1], fill, edge, it['pal'], grp[g][0], it['alt'])
                place(new, pal, mb_, yb_ + hh_ - mb_.shape[0], X_, fill, edge, it['pal'], grp[g][0], it['alt'])
                y += hh_ + gapy; continue
            if kind == 'tab':
                # 원래 줄 안 틈(6px 넘는)으로 나눈 조각 위치에 하나씩
                sub = img[int(y):int(y) + dh + 3, it['x0']:it['x1']] > 0
                cols = np.nonzero(sub.any(0))[0]; runs = [[cols[0], cols[0] + 1]]
                for c in cols[1:]:
                    if c - runs[-1][1] > 6:
                        runs.append([c, c + 1])
                    else:
                        runs[-1][1] = c + 1
                for q, t in enumerate(m):
                    a0, a1 = runs[q] if q < len(runs) else (runs[-1][1] + 8, runs[-1][1] + 208)
                    lim = (runs[q + 1][0] - 4) if q + 1 < len(runs) else (right - it['x0'])
                    if t == '=':                           # 원본 조각 복원(항목 전체 높이) — 마지막 조각이면 남은 조각 전부
                        last = runs[-1][1] if q == len(m) - 1 else a1
                        new[it['y0']:it['y1'], it['x0'] + a0:it['x0'] + last] = img[it['y0']:it['y1'], it['x0'] + a0:it['x0'] + last]
                        continue
                    if not t.strip():
                        continue
                    mk = squeeze(render_line(line_mask(t), dh), lim - a0)
                    place(new, pal, mk, int(y), it['x0'] + a0, fill, edge, it['pal'], grp[g][0], it['alt'])
                y += dh + gapy; continue
            avail = right - it['x0'] - ind
            if m.shape[1] > avail:
                if m.shape[1] * MIN_SQ <= avail:
                    m = squeeze(m, avail)
                else:                                       # 압축으로도 안 되면 높이도 줄임
                    sc = avail / (m.shape[1] * MIN_SQ)
                    m = squeeze(m, avail, int(m.shape[0] * sc))
            x = it['x1'] - m.shape[1] if right_al is True else it['x0'] + ind
            yy = int(round(y)) + (0 if (n > 1 or right_al == 'top') else max(0, (it['h'] - m.shape[0])))
            place(new, pal, m, yy, x, fill, edge, it['pal'], grp[g][0], it['alt'])
            y += m.shape[0] + gapy
    return its, grp, ents, T, canv


def place(new, pal, m, y, x, fill, edge, palv, r0, alt=None):
    """m = 색 번호 층(1 첫째 채움 · 2 둘째 채움). 테두리 1px = 원본 테두리색(채움과 다를 때)"""
    h, w = m.shape
    if SNAP:                                           # 8px 격자에 맞춤 — 같은 문구가 같은 타일을 쓰게(타일 자리 절약)
        x = (x + 4) // 8 * 8; y = (y + 4) // 8 * 8 if SNAP > 1 else y
    y = max(0, y); x = max(0, x)
    sub = new[y:y + h, x:x + w]; lay = m[:sub.shape[0], :sub.shape[1]]; mm = lay > 0
    if edge and edge != fill and EDGE:
        ol = outline(np.pad(mm, 1))[1:-1, 1:-1]
        sub[ol & ~mm] = edge
    sub[lay == 1] = fill
    sub[lay == 2] = alt if alt is not None else fill
    for v in set(np.unique(lay)) - {0, 1, 2}:
        sub[lay == v] = ITEM_FILL[int(v) - 100]
    # 새로 잉크가 들어간 칸의 팔레트 = 항목 팔레트
    ys, xs = np.nonzero(mm)
    for cy, cx in set(((y + a) // 8, (x + b) // 8) for a, b in zip(ys, xs)):
        if cy < pal.shape[0] and cx < 64:
            pal[cy, cx] = palv


def preview(X, its, grp, ents, T, canv):
    c = I.S.load_tiles  # noqa
    import read_lines as R
    cr = R.P.cram_of('s16')
    rgb = lambda e: np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)
    parts = []
    for g, (r0, r1, k) in enumerate(grp):
        img, new, pal = canv[g]
        opal = I.pal_rows(ents, r0, r1)
        def col(a, p):
            out = np.zeros(a.shape + (3,), np.uint8) + np.array((24, 8, 40), np.uint8)
            for r in range(a.shape[0] // 8):
                for x in range(64):
                    blk = a[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
                    cc = rgb(cr[((0x60 + p[r, x]) * 16 + blk) & 0x7FF]); cc[blk == 0] = (24, 8, 40)
                    out[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = cc
            return out[:, :512]
        row = np.concatenate([col(img, opal), np.full((img.shape[0], 4, 3), 128, np.uint8), col(new, pal)], 1)
        parts += [row, np.full((3, row.shape[1], 3), 90, np.uint8)]
    im = Image.fromarray(np.concatenate(parts)); im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
    p = os.path.join(ROOT, 'work', 'stg', 'kr_preview_%s.png' % X); im.save(p); return p


def main():
    xs = 'BOCASL' if sys.argv[1] == 'all' else sys.argv[1]
    for X in xs:
        its, grp, ents, T, canv = build(X)
        np.savez_compressed(os.path.join(ROOT, 'work', 'stg', 'kr_%s.npz' % X),
                            **{'new%d' % g: canv[g][1] for g in canv}, **{'pal%d' % g: canv[g][2] for g in canv})
        print(X, preview(X, its, grp, ents, T, canv))


if __name__ == '__main__':
    main()
