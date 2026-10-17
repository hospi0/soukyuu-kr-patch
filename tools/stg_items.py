# -*- coding: utf-8 -*-
r"""게임 안 문구 «낱말 덩어리» 목록 (2026-10-17)
  스테이지 맵(SS_ST?.BIN)의 행 묶음(세트 판정: stg_blocks.classify_rows) → 64열 전체를 그려 잉크를 가로 6px·세로 1px 로 이어 붙인 연결 영역 = 덩어리.
  덩어리마다 위치(픽셀)·높이·채움색/테두리색(색 번호)·칸 팔레트를 뽑아 work/stg/items_<X>.tsv, 번호 붙인 그림 work/stg/items_<X>.png
  python tools/stg_items.py <X|all>
"""
import collections
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import stg_blocks as S  # noqa: E402


GAP = 9                                            # 줄 안에서 이보다 넓은 틈 = 다른 항목(띄어쓰기 하나 ≈ 10px)


def marker_cells(ents, r0, r1):
    """좌우가 빈칸(문장 그림 아님)인 외톨이 칸이 같은 열에서 4행 넘게 이어지면 표시 칸"""
    lone = set()
    for r in range(r0, r1):
        for x in range(64):
            if S.is_text(ents[r * 64 + x]) and not (x > 0 and S.is_text(ents[r * 64 + x - 1])) and not (x < 63 and S.is_text(ents[r * 64 + x + 1])):
                lone.add((r, x))
    out = set()
    for (r, x) in lone:
        run = [q for q in range(r - 4, r + 5) if (q, x) in lone]
        if len(run) >= 4:
            out.add((r, x))
    return out


def label(mask):
    """4-연결 성분 번호(간단 BFS)"""
    h, w = mask.shape; lab = np.zeros((h, w), int); n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not lab[y, x]:
                n += 1; st = [(y, x)]; lab[y, x] = n
                while st:
                    cy, cx = st.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n; st.append((ny, nx))
    return lab, n


def pal_rows(ents, r0, r1):
    p = np.zeros((r1 - r0, 64), int)
    for r in range(r0, r1):
        for x in range(64):
            p[r - r0, x] = ents[r * 64 + x] >> 12
    return p


def items(X):
    """줄(가로 투영) → 줄 안 16px 넘는 틈으로 나눈 항목. 4px 이하 작은 조각(48열 점선 등)은 뺌"""
    grp, ents, T = S.classify_rows(X)
    out = []
    for g, (r0, r1, k) in enumerate(grp):
        img = S.render_rows(ents, r0, r1, T[k])
        ink = img > 0
        lab, n = label(ink)
        for i in range(1, n + 1):                      # 작은 조각 제거
            ys, xs = np.nonzero(lab == i)
            if ys.max() - ys.min() < 4 and xs.max() - xs.min() < 4:
                ink[ys, xs] = False
        for (r, x) in marker_cells(ents, r0, r1):        # 표시용 외톨이 칸(EC01/EC39/EC73/ECAA 열) — 글자 아님, 손대지 않음
            ink[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8] = False
        pals = pal_rows(ents, r0, r1)
        rows = ink.sum(1) > 2; y = 0                   # 잉크 2화소 이하 행 = 줄 경계(줄끼리 맞닿은 블록 대비)
        while y < len(rows):
            if not rows[y]:
                y += 1; continue
            y0 = y
            while y < len(rows) and rows[y]:
                y += 1
            y1 = y
            cols = ink[y0:y1].any(0); xs = np.nonzero(cols)[0]
            runs = [[xs[0], xs[0] + 1]]
            for x in xs[1:]:
                if x - runs[-1][1] > GAP:
                    runs.append([x, x + 1])
                else:
                    runs[-1][1] = x + 1
            for x0, x1 in runs:
                if x1 - x0 < 10:                       # 남은 표시 조각
                    continue
                sub = ink[y0:y1, x0:x1]; yy = np.nonzero(sub.any(1))[0]
                a0, a1 = y0 + yy.min(), y0 + yy.max() + 1
                ys, xs2 = np.nonzero(ink[a0:a1, x0:x1]); ys += a0; xs2 += x0
                vals = img[ys, xs2]
                pad = np.pad(ink, 1)
                edge_px = ~(pad[ys, xs2 + 1] & pad[ys + 2, xs2 + 1] & pad[ys + 1, xs2] & pad[ys + 1, xs2 + 2])
                ec = collections.Counter(vals[edge_px]).most_common(1)
                fcs = collections.Counter(vals[~edge_px]).most_common()
                fc = fcs[:1] or ec
                # 둘째 채움색: 첫째와 다르고 테두리색도 아닌 것 중 가장 흔한 것(흰 작은 글자 + 빨간 큰 이름 같은 항목)
                alt = next((v for v, c in fcs[1:] if v != (ec[0][0] if ec else -1) and c >= 20), fc[0][0] if fc else 0)
                pc = collections.Counter(pals[ys // 8, xs2 // 8]).most_common(1)[0][0]
                out.append(dict(stage=X, grp=g, set=k, r0=r0, r1=r1, x0=int(x0), y0=int(a0), x1=int(x1), y1=int(a1),
                                h=int(a1 - a0), fill=int(fc[0][0]), edge=int(ec[0][0]) if ec else 0, pal=int(pc), alt=int(alt)))
    return out, grp, ents, T


def sheet(X, its, grp, ents, T):
    parts = []
    for g, (r0, r1, k) in enumerate(grp):
        img = S.render_rows(ents, r0, r1, T[k])
        im = Image.fromarray(np.where(img > 0, 0, 255).astype(np.uint8)).convert('RGB')
        im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        for j, it in enumerate(its):
            if it['grp'] != g:
                continue
            dr.rectangle((it['x0'] * 2, it['y0'] * 2, it['x1'] * 2 - 1, it['y1'] * 2 - 1), outline=(255, 0, 0))
            dr.text((it['x0'] * 2 + 1, max(0, it['y0'] * 2 - 1)), str(j), fill=(0, 0, 255))
        lab = Image.new('RGB', (60, im.height), (60, 60, 60)); ImageDraw.Draw(lab).text((2, 2), '%s %d\n%s' % (X, r0, k), fill=(255, 255, 0))
        row = Image.new('RGB', (60 + im.width, im.height)); row.paste(lab, (0, 0)); row.paste(im, (60, 0))
        parts.append(row)
    W = max(p.width for p in parts); H = sum(p.height + 4 for p in parts)
    o = Image.new('RGB', (W, H), (120, 120, 120)); y = 0
    for p in parts:
        o.paste(p, (0, y)); y += p.height + 4
    o.save(os.path.join(ROOT, 'work', 'stg', 'items_%s.png' % X))


def main():
    xs = 'BOCASL' if sys.argv[1] == 'all' else sys.argv[1]
    for X in xs:
        its, grp, ents, T = items(X)
        with open(os.path.join(ROOT, 'work', 'stg', 'items_%s.tsv' % X), 'w', encoding='utf-8') as f:
            f.write('번호\t세트\t행\tx0\ty0\tx1\ty1\t높이\t채움\t테두리\t팔레트\n')
            for j, it in enumerate(its):
                f.write('%d\t%s\t%d-%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n' % (j, it['set'], it['r0'], it['r1'] - 1, it['x0'], it['y0'], it['x1'], it['y1'], it['h'], it['fill'], it['edge'], it['pal']))
        sheet(X, its, grp, ents, T)
        print(X, '덩어리', len(its))


if __name__ == '__main__':
    main()


def listing(X):
    """항목마다 잘라 «번호 | 그림» 으로 세로 목록 → work/stg/list_<X>_<n>.png (40개씩)"""
    its, grp, ents, T = items(X)
    rows = []
    for j, it in enumerate(its):
        img = S.render_rows(ents, it['r0'], it['r1'], T[it['set']])
        c = img[it['y0']:it['y1'], it['x0']:it['x1']]
        im = Image.fromarray(np.where(c > 0, 0, 255).astype(np.uint8)).convert('RGB')
        sc = max(1, min(2, 60 // max(1, im.height)))
        im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
        lab = Image.new('RGB', (70, max(im.height, 16)), (40, 40, 90)); ImageDraw.Draw(lab).text((3, 2), '%d %s h%d' % (j, it['set'][0], it['h']), fill=(255, 255, 0))
        row = Image.new('RGB', (70 + max(im.width, 10), lab.height), (255, 255, 255)); row.paste(lab, (0, 0)); row.paste(im, (70, 0))
        rows.append(row)
    for k in range(0, len(rows), 40):
        part = rows[k:k + 40]
        W = max(r.width for r in part); H = sum(r.height + 2 for r in part)
        o = Image.new('RGB', (W, H), (150, 150, 150)); y = 0
        for r in part:
            o.paste(r, (0, y)); y += r.height + 2
        o.save(os.path.join(ROOT, 'work', 'stg', 'list_%s_%d.png' % (X, k // 40)))
