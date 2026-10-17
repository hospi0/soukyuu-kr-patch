# -*- coding: utf-8 -*-
r"""메뉴류 «맵(BD 평문) + 그림(GF 압축)» 화면 한글화 — 항목 분해 · 지정 · 렌더 · 재배치 (2026-10-17)
  SCREENS[이름] = 맵(파일, 위치, 폭, 행 수) · 고칠 그림 세트(spec, VRAM) · 칸 번호 기준(chn = (v&0xFFF)|base) · 인터레이스(세로 2배) · 미리보기 스테이트/보조 팔레트
  다른 세트(제목·글꼴)를 가리키는 칸은 그대로. 빈자리 = 이 세트에서 «바뀐 칸만 쓰던» 타일(맵이 안 가리키는 타일은 보호).
  python tools/nbg_kr.py <화면> items   → work/nbg/<화면>_list.png · items.tsv (번호 목록)
  python tools/nbg_kr.py <화면> build   → 지정 work/text/nbg_spec_<화면>.tsv 로 렌더·재배치 → work/out/ · 미리보기 work/nbg/<화면>_preview.png
  지정 문법은 stg_kr 과 같음(빈칸·'='·\n·{h}·{h~}·{h@k}·+N·>·^·⇥).
"""
import collections
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import stg_items as I  # noqa: E402
import stg_kr as K  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc'); OUT = os.path.join(ROOT, 'work', 'out')
SCREENS = {
    # 연습 메뉴 NBG3 (메뉴 항목·조작 안내·詳細 머리) — PMENU 목차 1(BD 7800) + 목차 0(GF 6000)
    'pmenu3': dict(map=('PMENU/PMENU.BIN', 0xEFC0, 64, 256), pages=(2, 2), tiles=('PMENU/PMENU.BIN:16FC4', 0x60000), base=0x3000,
                   interlace=True, state='s6', palsup=7, aa=True, aa_edge=True,
                   wrap=[(368, 444, 512, 528, 0)]),
    # 기체 선택 NBG3 (プレイヤー1 · 기체 이름판 · 흐르는 띠) — JSELSP BD 6E00 @0x10E20 + GF 7800 @0x16E24 · 인터레이스 아님
    'jsel3': dict(map=('JSELSP.BIN', 0x10E20, 64, 192), tiles=('JSELSP.BIN:16E24', 0x78000), base=0x3000,
                  interlace=False, state='s9', palsup=6),   # 실행 중 페이지 A x0~16 조각을 페이지 B x512~528 로 옮겨 «LR…観る / …画面に戻る» 줄을 완성
    # 오프닝 데모 NBG3 (全機発進準備完了 · 本社 第三カタパルトビル · 射出まであと″秒) — JDEMO_0 BD 2000×3 @0x20108·0x22108·0x24108 + GF @0x26108 → VRAM 0x68000
    'jdemo3': dict(map=('TOFF/JDEMO_0.BIN', 0x20108, 64, 192), tiles=('TOFF/JDEMO_0.BIN:26108', 0x68000), base=0x3000,
                   interlace=False, state='s10', palsup=6, post='post_jdemo_sec', aa=True),
    # 경고문 NBG0 (このゲームはフィクションです…) — OPDEMO_T BD 2000 @0x18B10 + 팔레트 32 B @0x1AB10 + GF @0x1AB30 → VRAM 0x78000 (PNCN 0xC02F)
    'warn0': dict(map=('OPDEMO/OPDEMO_T.BIN', 0x18B10, 64, 64), tiles=('OPDEMO/OPDEMO_T.BIN:1AB30', 0x78000), base=0x3000,
                  interlace=False, state='s2', palsup=1, post='post_warn', aa=True),
    # 조작 설명(操作解説, 연습 스테이지 E) NBG3 — STGE_DAT 맵(칸 번호만, 64칸 폭) @0x32420 + GF @0x34CA0 → VRAM 0x60000
    'tut3': dict(map=('STG_E/STGE_DAT.BIN', 0x32420, 64, 81), tiles=('STG_E/STGE_DAT.BIN:34CA0', 0x60000), base=0x3000,
                 interlace=False, state='s18', palsup=6,
                 zones=[(0, 32, 352, 72)] + [(0, 72 + 24 * k, 352, 96 + 24 * k) for k in range(24)]),
    # 최고 득점 획득자 순위표(어트랙트) — RANK_DAT GF @0x1B160 → VRAM 0x60000 · NBG1 맵 @0x19160(位 칸, 이름·점수는 코드) · NBG3 맵 @0x594(머리 最高得点獲得者)
    'rank1': dict(map=('RANK_DAT.BIN', 0x19160, 64, 64), tiles=('RANK_DAT.BIN:1B160', 0x60000), base=0x3000,
                  interlace=False, state='s19', palsup=6, aa=True, black=True),
    'rank3': dict(map=('RANK_DAT.BIN', 0x594, 64, 64), tiles=('RANK_DAT.BIN:1B160', 0x60000), base=0x3000,
                  interlace=False, state='s19', palsup=6, aa=True),
    # 제목 메뉴 NBG3(発進·演習·設定 등) — TIT_PNT 맵 조각(64칸 폭) @0x37600~ + GF @0x286E8 → VRAM 0x60000 (PNCN 0xC0CC)
    'tit3': dict(map=('TITLE/TIT_PNT.BIN', 0x37600, 64, 248), tiles=('TITLE/TIT_PNT.BIN:286E8', 0x60000), base=0x3000,
                 interlace=True, state='m1', palsup=6, aa=True, black=True, fill_w=True, post='post_tit_ctrl', zones=[(352, 1056, 480, 1104), (352, 1104, 480, 1152), (352, 1152, 480, 1200), (352, 1200, 480, 1248)]
                 + [(0, 1024 + 32 * k, 89, 1056 + 32 * k) for k in range(14)] + [(89, 1024 + 32 * k, 192, 1056 + 32 * k) for k in range(8)]
                 + [(248, 962, 326, 992), (326, 962, 406, 992), (406, 962, 512, 992)]),
    # 설정·최고 득점 NBG1 — OPT_PNT 맵 4장 @0x4AD00(최고 득점)·0x4CD00·0x4ED00(설정)·0x50D00, PNCN 0xC0C8(칸 기준 0x2000, 보조 팔레트 6)
    #   그림 A = GF @0x4822C → VRAM 0x4D000 · 그림 B = GF @0x40178 → VRAM 0x56000
    'opt1a': dict(map=('TITLE/OPT_PNT.BIN', 0x4AD00, 64, 256), tiles=('TITLE/OPT_PNT.BIN:4822C', 0x4D000), base=0x2000,
                  interlace=False, state='s4', palsup=6),
    'opt1b': dict(map=('TITLE/OPT_PNT.BIN', 0x4AD00, 64, 256), tiles=('TITLE/OPT_PNT.BIN:40178', 0x56000), base=0x2000,
                  interlace=False, state='s4', palsup=6, aa=True),
    #   그림 C = GF @0x4432C → s4 VRAM 0x58000 (설정 화면 글자: 設定画面·메뉴·易1~8難·難度 이름·ステレオ/モノラル)
    'opt1c': dict(map=('TITLE/OPT_PNT.BIN', 0x4AD00, 64, 256), tiles=('TITLE/OPT_PNT.BIN:4432C', 0x58000), base=0x2000,
                  interlace=False, state='s4', palsup=6, aa=True, scrw=350),
}


def grid_order(c):
    """파일 안 칸 순서 → 화면 격자(가로 W, 세로 H) 위치 목록. pages=(가로, 세로) 이면 64×64 페이지를 A B / C D 로"""
    mp, moff, w, rows = c['map']
    pc, pr = c.get('pages', (1, 1))
    if (pc, pr) == (1, 1):
        return [divmod(i, w) for i in range(w * rows)], w, rows
    order = []
    for pg in range(pc * pr):
        py, px = divmod(pg, pc)
        for i in range(64 * 64):
            r, x = divmod(i, 64); order.append((py * 64 + r, px * 64 + x))
    return order, 64 * pc, 64 * pr


def load(name):
    c = SCREENS[name]
    mp, moff, w, rows = c['map']
    md = open(os.path.join(DISC, mp), 'rb').read()          # 원본은 언제나 디스크 원본에서(work/out 을 읽으면 두 번 고침)
    flat = list(struct.unpack('>%dH' % (w * rows), md[moff:moff + w * rows * 2]))
    order, W, H = grid_order(c)
    ents = [0] * (W * H)
    for k, (r, x) in enumerate(order):
        ents[r * W + x] = flat[k]
    c['_order'] = order; c['_W'] = W; c['_H'] = H
    spec, vram = c['tiles']
    fp, off = spec.rsplit(':', 1); off = int(off, 16)
    td = open(os.path.join(DISC, fp), 'rb').read()
    tiles, end = sglz.decode(td, off)
    return c, md, ents, tiles, (fp, off, end - off, td)


def tidx(c, e, nt):
    addr = (((e & 0xFFF) | c['base']) * 0x20) - c['tiles'][1]
    return addr // 32 if 0 <= addr < nt * 32 else None


def canvas(c, ents, tiles, w, rows):
    nt = len(tiles) // 32
    img = np.zeros((rows * 8, w * 8), np.uint8); mine = np.zeros((rows, w), bool)
    for i, e in enumerate(ents):
        t = tidx(c, e, nt)
        if t is None:
            continue
        r, x = divmod(i, w)
        a = np.frombuffer(tiles[t * 32:t * 32 + 32], np.uint8)
        img[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8); mine[r, x] = True
    return img, mine


def items_of(img, pal, zones=None):
    """줄(가로 투영, 2px 이하 행 = 경계) → 9px 넘는 틈으로 나눈 항목(4px 이하 조각 제외). zones=[(x0,y0,x1,y1)…] 이면 그 구역 안만"""
    if zones:
        out = []
        for zx0, zy0, zx1, zy1 in zones:
            m_ = np.zeros(img.shape, bool); m_[zy0:zy1, zx0:zx1] = True
            out += items_of(np.where(m_, img, 0), pal)
        return out
    ink = img > 0
    lab, n = I.label(ink)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if ys.max() - ys.min() < 4 and xs.max() - xs.min() < 4:
            ink[ys, xs] = False
    out = []; rows = ink.sum(1) > 2; y = 0
    while y < len(rows):
        if not rows[y]:
            y += 1; continue
        y0 = y
        while y < len(rows) and rows[y]:
            y += 1
        y1 = y; xs = np.nonzero(ink[y0:y1].any(0))[0]
        runs = [[xs[0], xs[0] + 1]]
        for x in xs[1:]:
            if x - runs[-1][1] > 9:
                runs.append([x, x + 1])
            else:
                runs[-1][1] = x + 1
        for x0, x1 in runs:
            if x1 - x0 < 6:
                continue
            sub = ink[y0:y1, x0:x1]; yy = np.nonzero(sub.any(1))[0]; a0, a1 = y0 + yy.min(), y0 + yy.max() + 1
            ys2, xs2 = np.nonzero(ink[a0:a1, x0:x1]); ys2 += a0; xs2 += x0
            vals = img[ys2, xs2]; pad = np.pad(ink, 1)
            edge_px = ~(pad[ys2, xs2 + 1] & pad[ys2 + 2, xs2 + 1] & pad[ys2 + 1, xs2] & pad[ys2 + 1, xs2 + 2])
            ec = collections.Counter(vals[edge_px]).most_common(1); fcs = collections.Counter(vals[~edge_px]).most_common()
            fc = fcs[:1] or ec
            alt = next((v for v, k in fcs[1:] if v != (ec[0][0] if ec else -1) and k >= 20), fc[0][0] if fc else 0)
            pc = collections.Counter(pal[ys2 // 8, xs2 // 8]).most_common(1)[0][0]
            out.append(dict(grp=0, set='M', r0=0, r1=0, x0=int(x0), y0=int(a0), x1=int(x1), y1=int(a1), h=int(a1 - a0),
                            fill=int(fc[0][0]), edge=int(ec[0][0]) if ec else 0, pal=int(pc), alt=int(alt)))
    return out


def list_items(name):
    c, md, ents, tiles, src = load(name); w, rows = c['_W'], c['_H']
    img, mine = canvas(c, ents, tiles, w, rows)
    pal = np.array([e >> 12 for e in ents]).reshape(rows, w)
    its = items_of(img, pal, c.get('zones'))
    os.makedirs(os.path.join(ROOT, 'work', 'nbg'), exist_ok=True)
    rws = []
    for j, it in enumerate(its):
        cc = img[it['y0']:it['y1'], it['x0']:it['x1']]
        im = Image.fromarray(np.where(cc > 0, 0, 255).astype(np.uint8)).convert('RGB')
        if c['interlace']:
            im = im.resize((im.width * 2, im.height), Image.NEAREST)
        lab = Image.new('RGB', (110, max(im.height, 14)), (40, 40, 90))
        ImageDraw.Draw(lab).text((3, 1), '%d h%d (%d,%d)' % (j, it['h'], it['x0'], it['y0']), fill=(255, 255, 0))
        row = Image.new('RGB', (110 + im.width, lab.height), (255, 255, 255)); row.paste(lab, (0, 0)); row.paste(im, (110, 0)); rws.append(row)
    for k in range(0, len(rws), 45):
        part = rws[k:k + 45]; W = max(r.width for r in part); H = sum(r.height + 2 for r in part)
        o = Image.new('RGB', (W, H), (150, 150, 150)); y = 0
        for r in part:
            o.paste(r, (0, y)); y += r.height + 2
        o.save(os.path.join(ROOT, 'work', 'nbg', '%s_list_%d.png' % (name, k // 45)))
    print(name, '항목', len(its))
    return its


def aa_cov(ln, dh, vs):
    """고해상도(안티에일리어싱) 덮임 0~1 — 4배로 그려 줄임. {높이} 지정도 4배. 인터레이스(vs=2)면 세로는 2배 해상도 그대로"""
    import re as _re
    ln4 = _re.sub(r'\{(\d+)', lambda mo: '{%d' % (int(mo.group(1)) * 4), ln)
    m4 = (K.render_line(K.line_mask(ln4), dh * 4) > 0).astype(float)
    fy = 4 // vs
    H = m4.shape[0] // fy * fy; W = m4.shape[1] // 4 * 4
    m4 = m4[:H, :W]
    return m4.reshape(H // fy, fy, W // 4, 4).mean((1, 3))


def aa_fit(cov, w, h=None):
    from PIL import Image as _I
    a = _I.fromarray((cov * 255).astype(np.uint8)).resize((max(1, w), h or cov.shape[0]), _I.LANCZOS)
    return np.asarray(a).astype(float) / 255


def aa_put(new, npal, cov, y, x, fill, palv, c, crb, snap=True, edge=None, vs=1):
    """덮임 → 화소마다 «바탕·채움 섞은 색»에 가장 가까운 그 팔레트(16색) 번호. edge 주면 먼저 1px 테두리(인터레이스면 세로 2px)"""
    if snap and K.SNAP:
        x = (x + 4) // 8 * 8; y = (y + 4) // 8 * 8 if K.SNAP > 1 else y
    y = max(0, y); x = max(0, x)
    if edge is not None and edge != fill:
        import cv2
        oc = cv2.dilate((cov * 255).astype(np.uint8), np.ones((1 + 2 * vs, 3), np.uint8)).astype(float) / 255
        oc = np.pad(oc, ((vs, vs), (1, 1)))
        aa_put(new, npal, oc, y - vs, x - 1, edge, palv, c, crb, snap=False)
    P = np.array([[((e & 31) << 3), (((e >> 5) & 31) << 3), (((e >> 10) & 31) << 3)] for e in
                  (crb[((c['palsup'] * 16 + palv) * 16 + i) & 0x7FF] for i in range(16))], float)
    fc = P[fill]
    for yy, xx in zip(*np.nonzero(cov > 0.1)):
        Y, X = y + yy, x + xx
        if Y >= new.shape[0] or X >= new.shape[1]:
            continue
        a = cov[yy, xx]; cur = new[Y, X]
        if cur == 0 and a < 0.35:
            continue
        bg = P[cur] if cur else np.zeros(3)
        col = bg * (1 - a) + fc * a
        new[Y, X] = 1 + int(np.argmin(((P[1:] - col) ** 2).sum(1)))
        npal[Y // 8, X // 8] = palv
    return y, x


CTRL_KR = ['샷·웹 사용', '봄버 발사', '웹 종류 전환', '샷 연사', '웹만 사용', '화면 줌 인', '화면 줌 아웃', '왼쪽으로 조금 이동',
           '오른쪽으로 조금 이동', '웹 왼쪽 회전', '웹 오른쪽 회전', '아날로그로 이동', '아날로그로 웹 회전', '아날로그로 좌우 이동', '아날로그로 화면 줌']


def post_tit_ctrl(c, img, new, npal, crb):
    """조작 설정 상자 15개(TIT_PNT 시트 x192~352 · y994+32k): 상자 15개 같은 자리 다수결 = 깨끗한 사선 줄무늬 바탕 → 가운데 어두운 글자(중간색)"""
    X0, X1, Y0, N = 194, 352, 994, 15
    stack = np.stack([img[Y0 + 32 * k:Y0 + 32 * k + 32, X0:X1] for k in range(N)])
    clean = np.zeros(stack.shape[1:], stack.dtype)
    for y in range(stack.shape[1]):
        for x in range(stack.shape[2]):
            vv_ = [int(v_) for v_ in stack[:, y, x] if int(v_) in (1, 2, 4, 5)]   # 줄무늬·테두리 색만(글자색 제외)
            clean[y, x] = collections.Counter(vv_).most_common(1)[0][0] if vv_ else collections.Counter(stack[:, y, x].tolist()).most_common(1)[0][0]
    pv = int(npal[(Y0 + 8) // 8, (X0 + 40) // 8])
    lum = lambda z: sum(((crb[((c['palsup'] * 16 + pv) * 16 + int(z)) & 0x7FF] >> s_) & 31) for s_ in (0, 5, 10))
    txtc = collections.Counter()
    for k in range(N):                                   # 원래 글자색 = 상자 안에서 바탕(clean)과 다른 화소의 최다·최명
        d_ = stack[k] != clean
        txtc.update(stack[k][d_].tolist())
    cand = [z for z, _ in txtc.most_common(6)]
    light = max(cand, key=lum); dark = min(cand, key=lum)
    for k, t in enumerate(CTRL_KR):
        y = Y0 + 32 * k
        new[y:y + 32, X0:X1] = clean
        K.WEIGHT = b'Black'
        cov = aa_cov(t, 11, 2); K.WEIGHT = None
        if cov.shape[1] > X1 - X0 - 16:
            cov = aa_fit(cov, X1 - X0 - 16)
        aa_put(new, npal, cov, y + 4 + (24 - cov.shape[0]) // 2, X0 + (X1 - X0 - cov.shape[1]) // 2, light, pv, c, crb, snap=False, edge=dark, vs=2)


def post_jdemo_sec(c, img, new, npal, crb):
    """오프닝 데모 «″秒» 깃발: 秒(x322~343·y1070~1087) 지우기 → 깃발 안 사선 줄무늬는 1069 행에서 대각선으로 이어 복원, 깃발 밖은 투명 → 「초」"""
    Y0, X0, X1 = 1069, 321, 343
    reg = img[1070:1088, 320:344]
    fill = collections.Counter(reg[(reg > 0)].tolist()).most_common(1)[0][0]
    pv = int(npal[1076 // 8, 330 // 8])
    lumz = lambda z: sum(((crb[((c['palsup'] * 16 + pv) * 16 + z) & 0x7FF] >> s_) & 31) for s_ in (0, 5, 10))
    lo = img[1079:1088, 320:344]; nb0 = np.zeros(lo.shape, bool)       # 깃발 밖 秒 화소 중 빈칸과 맞닿은 것 = 테두리 색
    for dy_, dx_ in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nb0 |= np.roll(np.roll(lo == 0, dy_, 0), dx_, 1)
    edge = collections.Counter(lo[(lo > 0) & nb0].tolist()).most_common(1)[0][0]
    fill = collections.Counter(lo[(lo > 0) & ~nb0].tolist()).most_common(1)[0][0]
    for y in range(1070, 1088):
        for x in range(320, 343):
            if y <= 1078 and x == 320:
                new[y, x] = 6 if y <= 1075 else img[1075, 320]
            elif y <= 1078:
                new[y, x] = img[Y0, x - (y - Y0)]
            else:
                new[y, x] = 0
    K.WEIGHT = b'Black'
    cov = aa_cov('초', 15, 1); K.WEIGHT = None
    aa_put(new, npal, cov, 1071, 324, int(fill), pv, c, crb, snap=False)   # 테두리 없이 고해상도
    # «射出まで» 뒤 줄무늬 띠(y1065~1078 · x160~231, 왼쪽 테두리 6): 사선 칸((x−y) mod 16)별 줄무늬 색 최빈값 → 한글 안 그린 자리만
    by0, by1, bx0, bx1 = 1065, 1079, 161, 232
    band = img[by0:by1, bx0:bx1]
    votes = collections.defaultdict(collections.Counter)
    for yy in range(by1 - by0):
        for xx in range(bx1 - bx0):
            v_ = int(band[yy, xx])
            if v_ in (2, 7, 14):
                votes[(xx + bx0 - (yy + by0)) % 16][v_] += 1
    for yy in range(by0, by1):
        if new[yy, 160] == 0:
            new[yy, 160] = 6
        for xx in range(bx0, bx1):
            if new[yy, xx] == 0:
                k_ = (xx - yy) % 16
                new[yy, xx] = votes[k_].most_common(1)[0][0] if votes[k_] else 2
    if os.environ.get('DBG'):
        for yy in range(1062, 1090):
            print(yy, ''.join('.' if v_ == 0 else '%X' % v_ for v_ in new[yy, 296:350]))


WARN_KR_FLAT = '이 게임은 픽션입니다.실재하는 인물,사건,단체 등과는 일절 관계가 없습니다.'   # kr_menu.tsv 경고문
WARN_KR = ['이 게임은 픽션입니다.', '실재하는 인물,사건,단체', '등과는 일절 관계가', '없습니다.']


def post_warn(c, img, new, npal, crb):
    """경고문: 글자 영역(y17~112 · x70~340)만 비우고(아래 눈금자 보존) 원래 줄 자리(y17·41·65·89, 높이 22)에 WARN_KR 줄(문장부호 자리에서 직접 끊음)로 그림.
    색 = 흰 채움 1 + 회색 가장자리 3(원본 안티에일리어싱 흉내)"""
    Y0, LH, X0, X1 = 17, 24, 73, 335
    new[Y0:Y0 + LH * 4, 70:340] = 0
    pv = int(npal[Y0 // 8, X0 // 8])
    K.WEIGHT = b'Black'
    lines = WARN_KR                                       # 줄은 문장부호 자리에서 직접 끊음
    assert len(lines) <= 4 and ''.join(lines).replace(' ', '') == WARN_KR_FLAT.replace(' ', ''), lines
    for t in lines:
        wd_ = K.render_line(K.line_mask(t), 23).shape[1]
        assert wd_ <= X1 - X0, (t, wd_)
    for q, t in enumerate(lines):
        cov = aa_cov(t, 22, 1)
        aa_put(new, npal, cov, Y0 + q * LH - 1, X0, 1, pv, c, crb, snap=False)
    K.WEIGHT = None
    print('  경고문 줄', lines)


def build(name):
    c, md, ents, tiles, (fp, off, olen, td) = load(name); w, rows = c['_W'], c['_H']
    img, mine = canvas(c, ents, tiles, w, rows)
    pal = np.array([e >> 12 for e in ents]).reshape(rows, w)
    its = items_of(img, pal, c.get('zones'))
    sp = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'nbg_spec_%s.tsv' % name), encoding='utf-8').read().splitlines():
        if ln.strip() and not ln.startswith('#'):
            k, _, v = ln.partition('\t'); sp[int(k)] = v.replace('\\n', '\n')
    miss = [j for j in range(len(its)) if j not in sp]
    if miss:
        raise SystemExit('지정 없음 %s' % miss)
    K.ITEM_FILL.clear(); K.ITEM_FILL.update({j: it['fill'] for j, it in enumerate(its)})
    new = img.copy(); npal = pal.copy()
    for j, it in enumerate(its):                          # 지우기
        if sp[j] == '=' or sp[j][:2] in ('#B', '#S', '#P', '#T'):
            continue
        box = new[it['y0']:it['y1'], it['x0']:it['x1']]; box[img[it['y0']:it['y1'], it['x0']:it['x1']] > 0] = 0
    vs = 2 if c['interlace'] else 1
    import pm_detail as P
    crb = P.cram_of(c['state'])
    def is_text_px(idx, pv):                               # 흰색·회색(채도 낮고 밝음) = 글자
        e = crb[((c['palsup'] * 16 + pv) * 16 + idx) & 0x7FF]
        r, g, bb = (e & 31) * 8, ((e >> 5) & 31) * 8, ((e >> 10) & 31) * 8
        return max(r, g, bb) - min(r, g, bb) < 40 and max(r, g, bb) > 70
    # 버튼: 모든 버튼 띠를 모으고, 글자 없는 구간이 가장 긴 띠에서 행마다 줄무늬 한 주기를 떼어 반복 → 깨끗한 바탕
    bands_all = []
    for j, it in enumerate(its):
        v = sp[j]
        if not v.startswith('#B'):
            continue
        labels = [t[2:] if t.startswith('#B') else t for t in v.split('\n')]
        reg = img[it['y0']:it['y1'], it['x0']:it['x1']]
        rowink = (reg > 0).sum(1) > 0; yy = 0; bands = []
        while yy < len(rowink):
            if not rowink[yy]:
                yy += 1; continue
            a0 = yy
            while yy < len(rowink) and rowink[yy]:
                yy += 1
            bands.append((it['y0'] + a0, it['y0'] + yy))
        for (b0, b1), lab in zip(bands, labels):
            pv = int(npal[(b0 + b1) // 16, (it['x0'] + it['x1']) // 16])
            src = img[b0:b1, it['x0']:it['x1']]
            txt = np.vectorize(lambda q: bool(q > 0 and is_text_px(int(q), pv)))(src)
            bands_all.append(dict(b0=b0, b1=b1, x0=it['x0'], x1=it['x1'], lab=lab, pv=pv, src=src, txt=txt))
    if bands_all:
        def longest_clean(bd):
            col = bd['txt'][:, 4:-4].any(0); best = (0, 0); run = 0
            for x, t in enumerate(col):
                run = 0 if t else run + 1
                if run > best[0]:
                    best = (run, x + 4 - run + 1)
            return best
        ref = max(bands_all, key=lambda bd: longest_clean(bd)[0])
        rl, rx = longest_clean(ref)
        src = ref['src']
        best, P_ = -1, 16
        for per in range(8, min(48, rl)):
            sc = (src[:, rx:rx + rl - per] == src[:, rx + per:rx + rl]).mean()
            if sc > best:
                best, P_ = sc, per
        H_, W_ = src.shape
        clean = src.copy()
        for y in range(H_):
            seg = src[y, rx:rx + P_]
            for x in range(3, W_ - 3):
                clean[y, x] = seg[(x - rx) % P_]
        print('  버튼 바탕: 기준 띠 %d 행 · 깨끗한 구간 %d px · 줄무늬 주기 %d' % (ref['b0'], rl, P_))
    for bd in bands_all:
        b0, b1 = bd['b0'], bd['b1']; h_ = b1 - b0; w_ = bd['x1'] - bd['x0']
        sub = new[b0:b1, bd['x0']:bd['x1']]
        cl = clean[:h_, :w_] if clean.shape[0] >= h_ and clean.shape[1] >= w_ else bd['src']
        # 글자가 있던 범위(±2px)만 복원 줄무늬로 — 나머지는 원본 그대로(타일 공유 유지)
        tx_ = np.nonzero(bd['txt'].any(0))[0]; ty_ = np.nonzero(bd['txt'].any(1))[0]
        if len(tx_):
            keep_ = np.ones(cl.shape, bool)
            keep_[max(0, ty_.min() - 2):ty_.max() + 3, max(3, tx_.min() - 2):min(cl.shape[1] - 3, tx_.max() + 3)] = False
            cl = np.where(keep_, bd['src'][:cl.shape[0], :cl.shape[1]], cl)
        sub[:cl.shape[0], :cl.shape[1]] = cl
        txt = bd['txt']; src = bd['src']; pv = bd['pv']
        tx = np.nonzero(txt.any(0))[0]; ty = np.nonzero(txt.any(1))[0]
        th = ty.max() - ty.min() + 1 if len(ty) else h_ - 6
        fillc = collections.Counter(src[txt]).most_common(1)[0][0] if txt.any() else 1
        darkc = min(set(int(q) for q in np.unique(src) if q), key=lambda q: sum(((crb[((c['palsup'] * 16 + pv) * 16 + q) & 0x7FF] >> s_) & 31) for s_ in (0, 5, 10)))
        K.WEIGHT = b'Bold'
        vs_ = 2 if c['interlace'] else 1
        wavail = (tx.max() - tx.min() + 1) if len(tx) else w_ - 8
        if c.get('aa'):
            m = aa_cov(bd['lab'], th // vs_, vs_); K.WEIGHT = None
            if m.shape[1] > wavail:
                m = aa_fit(m, wavail)
        else:
            m = K.render_line(K.line_mask(bd['lab']), th // vs_); K.WEIGHT = None
            if c['interlace']:
                m = np.repeat(m, 2, axis=0)
            if m.shape[1] > wavail:
                m = K.squeeze(m, wavail)
        gx = bd['x0'] + (tx.min() if len(tx) else 4) + (wavail - m.shape[1]) // 2
        gy = b0 + (ty.min() if len(ty) else 3) + (th - m.shape[0]) // 2
        if c.get('aa'):
            aa_put(new, npal, m, gy, gx, int(fillc), pv, c, crb, snap=False, edge=int(darkc), vs=vs_)
        else:
            K.place(new, npal, m, gy, gx, int(fillc), int(darkc), pv, 0, int(fillc))
    for j, it in enumerate(its):                          # 단색 상자 아이콘(#S): 줄마다 글자 화소 → 그 줄 바탕색, 가운데 글자
        v = sp[j]
        if not v.startswith('#S'):
            continue
        labels = [t[2:] if t.startswith('#S') else t for t in v.split('\n')]
        n = len(labels); hh = (it['y1'] - it['y0']) / n
        xcommon = None
        # 줄 구간 = 실제 흰 글자 행 덩어리(3등분하면 상자 윗부분이 윗줄에 섞임) — 개수가 안 맞으면 등분
        pv0 = int(npal[(it['y0'] + it['y1']) // 16, (it['x0'] + it['x1']) // 16])
        def _w(z):
            e = crb[((c['palsup'] * 16 + pv0) * 16 + int(z)) & 0x7FF]; return z > 0 and min((e & 31) * 8, ((e >> 5) & 31) * 8, ((e >> 10) & 31) * 8) > 170
        wr = np.vectorize(_w)(img[it['y0']:it['y1'], it['x0']:it['x1']]).any(1)
        bands = []; yq = 0
        while yq < len(wr):
            if wr[yq]:
                s_ = yq
                while yq < len(wr) and wr[yq]:
                    yq += 1
                bands.append((it['y0'] + s_, it['y0'] + yq))
            else:
                yq += 1
        bands = [bd_ for bd_ in bands if bd_[1] - bd_[0] > 4]
        if len(bands) != n:
            bands = [(int(it['y0'] + q * hh), int(it['y0'] + (q + 1) * hh)) for q in range(n)]
        else:
            bands = [(a_ - 1, b_ + 1) for a_, b_ in bands]
        for q, lab in enumerate(labels):
            b0, b1 = bands[q]
            src = img[b0:b1, it['x0']:it['x1']]
            pv = int(npal[(b0 + b1) // 16, (it['x0'] + it['x1']) // 16])
            def rgb_of(z):
                e = crb[((c['palsup'] * 16 + pv) * 16 + int(z)) & 0x7FF]; return (e & 31) * 8, ((e >> 5) & 31) * 8, ((e >> 10) & 31) * 8
            bright = np.vectorize(lambda z: bool(z > 0 and min(rgb_of(z)) > 170))(src)       # 밝은 흰색 = 글자 몸
            colorful = np.vectorize(lambda z: bool(z > 0 and max(rgb_of(z)) - min(rgb_of(z)) > 90))(src)
            tx = np.nonzero(bright.any(0))[0]; ty = np.nonzero(bright.any(1))[0]
            if not len(tx):
                continue
            if q == 0:                                  # 첫 줄은 화살표 아이콘이 섞임 → 아래 줄들의 글자 시작 x 사용
                b0n, b1n = int(it['y0'] + hh), int(it['y1'])
                bb = np.vectorize(lambda z: bool(z > 0 and min(rgb_of(z)) > 170))(img[b0n:b1n, it['x0']:it['x1']])
                xs_ = np.nonzero(bb.any(0))[0]; xcommon = xs_.min() if len(xs_) else tx.min()
            tx = tx[tx >= (xcommon if xcommon is not None else 0)]
            txt = np.zeros_like(bright); txt[ty.min():ty.max() + 1, tx.min():tx.max() + 1] = True
            boxc = collections.Counter(src[colorful & txt]).most_common(1)
            if boxc and boxc[0][1] < 0.12 * txt.sum():
                boxc = []
            txt &= ~(colorful & (src == (boxc[0][0] if boxc else -1)))                     # 상자색은 남김
            # 글자 덩어리 = 글자 화소가 많은 열 구간(왼쪽 화살표 등은 제외)
            x0t = tx.min()
            box = (slice(None), slice(x0t, tx.max() + 1))
            reg = src[box]; tt = txt[box]
            xe_ = min(it['x1'] - it['x0'], tx.max() + 4)
            sub = new[b0:b1, it['x0'] + x0t:it['x0'] + xe_]
            boxrows = (colorful & (src == (boxc[0][0] if boxc else -1))).any(1)
            fillbg = np.where(boxrows[:, None], boxc[0][0] if boxc else 0, 0)[:, :1]
            sub[:] = np.broadcast_to(fillbg, sub.shape)     # 글자 구역 통째로(어두운 그림자 점까지) — 상자 행은 상자색
            fillc = collections.Counter(src[bright]).most_common(1)[0][0]
            darkc = min(set(int(z) for z in np.unique(src) if z), key=lambda z: sum(((crb[((c['palsup'] * 16 + pv) * 16 + z) & 0x7FF] >> s_) & 31) for s_ in (0, 5, 10)))
            th = ty.max() - ty.min() + 1
            K.WEIGHT = b'Black'
            m = K.render_line(K.line_mask(lab), th // (2 if c['interlace'] else 1)); K.WEIGHT = None
            if c['interlace']:
                m = np.repeat(m, 2, axis=0)
            wav = tx.max() - x0t + 1
            if m.shape[1] > wav:
                m = K.squeeze(m, wav)
            elif m.shape[1] < wav and m.shape[1] * 2.5 >= wav:     # 원래 글자 폭까지 가로로 늘림(파란 상자 꽉 차게)
                m = m[:, (np.arange(wav) * m.shape[1] // wav)]
            K.place(new, npal, m, b0 + ty.min() + (th - m.shape[0]) // 2, it['x0'] + x0t, int(fillc), int(darkc), pv, 0, int(fillc))   # 왼쪽 맞춤(원본 세 줄이 같은 x)
    def rgb3(z, pv):
        e = crb[((c['palsup'] * 16 + pv) * 16 + int(z)) & 0x7FF]; return (e & 31) * 8, ((e >> 5) & 31) * 8, ((e >> 10) & 31) * 8
    for j, it in enumerate(its):                          # 이름판(#P 왼쪽 작은 줄들|큰 이름) · 도장(#T 큰 글|작은 글)
        v = sp[j]
        if v[:2] not in ('#P', '#T'):
            continue
        y0_, y1_, x0_, x1_ = it['y0'], it['y1'], it['x0'], it['x1']
        box = new[y0_:y1_, x0_:x1_]; src = img[y0_:y1_, x0_:x1_]
        pv = int(npal[(y0_ + y1_) // 16, (x0_ + x1_) // 16])
        vals = collections.Counter(src[src > 0].ravel().tolist())
        bright = max(vals, key=lambda z: sum(rgb3(z, pv)))
        colorful = max(vals, key=lambda z: max(rgb3(z, pv)) - min(rgb3(z, pv)))
        left, _, right_ = v[2:].partition('|')
        if v.startswith('#P'):
            bg = 0 if (src == 0).mean() > 0.3 else vals.most_common(1)[0][0]   # 바탕이 투명(0)이면 0
            keep_top = left.strip() == '='                 # 왼쪽 위 번호 줄(S.O.Q-…)은 원본 화소 그대로
            box[(box > 0)] = bg                            # 판 전체를 바탕색으로
            if keep_top:
                # 번호 줄 = 위쪽 절반 중 큰 이름(가장 채도 높은 색) 왼쪽
                cols_big = np.nonzero((src == colorful).any(0))[0]
                bx = cols_big.min() - 2 if len(cols_big) else (x1_ - x0_) // 2
                hh_ = (y1_ - y0_) // 2
                box[:hh_, :bx] = src[:hh_, :bx]
            H_ = y1_ - y0_
            # 큰 이름: 오른쪽, 높이 ≈ 판의 85%, 첫 글자 주황(가장 채도 높은 색)·나머지 흰색
            if right_:
                K.WEIGHT = b'Black'
                parts = [K.render_line(K.line_mask(ch), int(H_ * 0.95)) for ch in right_]
                K.WEIGHT = None
                gap_ = 2; W_ = sum(m.shape[1] for m in parts) + gap_ * (len(parts) - 1)
                xx = x1_ - 3 - W_
                for q, m in enumerate(parts):
                    K.place(new, npal, m, y0_ + (H_ - m.shape[0]) // 2, xx, colorful if q == 0 else bright, 0, pv, 0, colorful if q == 0 else bright)
                    xx += m.shape[1] + gap_
                limit = x1_ - 6 - W_
            else:
                limit = x1_ - 4
            ls = [] if left.strip() == '=' else [t for t in left.split('\n') if t]
            for q, t in enumerate(ls):
                K.WEIGHT = b'Bold'
                m = K.render_line(K.line_mask(t), int(H_ * 0.32)); K.WEIGHT = None
                if m.shape[1] > limit - x0_ - 3:
                    m = K.squeeze(m, limit - x0_ - 3)
                K.place(new, npal, m, y0_ + 2 + q * (H_ // max(1, len(ls))), limit - m.shape[1], bright, 0, pv, 0, bright)
        else:                                              # 도장: 테두리(바깥 5px) 남기고 안쪽 빨간 글자 지움
            inner = box[5:-5, 5:-5]; isrc = src[5:-5, 5:-5]
            bgi = collections.Counter(isrc[(isrc > 0) & (isrc != colorful)].ravel().tolist()).most_common(1)
            redish = np.vectorize(lambda z: bool(z > 0 and max(rgb3(z, pv)) - min(rgb3(z, pv)) > 80))(isrc)
            if (isrc == 0).mean() > 0.3:
                inner[:] = 0                               # 바탕이 투명 → 테두리 안쪽 전체 비움(잔티 없음)
            else:
                inner[redish] = bgi[0][0] if bgi else 0
            H_ = y1_ - y0_ - 10; W_ = x1_ - x0_ - 10
            K.WEIGHT = b'Black'
            m = K.render_line(K.line_mask(left), int(H_ * 0.7)); K.WEIGHT = None
            if m.shape[1] > W_ - 6:
                m = K.squeeze(m, W_ - 6)
            K.place(new, npal, m, y0_ + 6, x0_ + 5 + (W_ - m.shape[1]) // 2, colorful, 0, pv, 0, colorful)
            if right_:
                K.WEIGHT = b'Bold'
                m2 = K.render_line(K.line_mask(right_), max(6, int(H_ * 0.15))); K.WEIGHT = None
                if m2.shape[1] > W_ - 6:
                    m2 = K.squeeze(m2, W_ - 6)
                K.place(new, npal, m2, y1_ - 6 - m2.shape[0], x0_ + 5 + (W_ - m2.shape[1]) // 2, colorful, 0, pv, 0, colorful)
    for j, it in enumerate(its):                          # 그리기
        v = sp[j]
        if v in ('=', '') or v[:2] in ('#B', '#S', '#P', '#T'):
            continue
        right = max(it['x1'], w * 8 - 8)
        for k2, it2 in enumerate(its):
            if k2 != j and sp[k2] != '' and it2['y0'] < it['y1'] and it2['y1'] > it['y0'] and it2['x0'] >= it['x1'] - 2:
                right = min(right, it2['x0'] - 6)
        right = max(right, it['x1'])
        lines = v.split('\n'); n = len(lines); y = it['y0']
        for ln in lines:
            ind = 0; al = None
            if ln.startswith('+'):
                k3 = 1
                while k3 < len(ln) and ln[k3].isdigit():
                    k3 += 1
                ind = int(ln[1:k3]); ln = ln[k3:]
            if ln.startswith('<'):                         # '<N' = 왼쪽으로 N px 넓혀 시작(좁은 칸 — 易→쉬움)
                k3 = 1
                while k3 < len(ln) and ln[k3].isdigit():
                    k3 += 1
                ind = -int(ln[1:k3]); ln = ln[k3:]
            if ln.startswith('>'):
                al = 'R'; ln = ln[1:]
            dh = (it['h'] if n == 1 else max(8, it['h'] // n - 1)) // vs
            if ln.startswith('!'):                         # '!' = 원래 글자 칸 끝(8px 올림)까지만 — 코드가 칸 범위로 복사하는 줄(설정 메뉴 강조)
                right = min(right, (it['x1'] + 7) // 8 * 8); ln = ln[1:]
            fixed_ = None
            if ln.startswith('@'):                         # '@x,x,…' = ⇥ 조각 시작 x(절대) 직접 지정 — 코드가 칸 범위로 떼어 쓰는 값(ステレオ/モノラル)
                k3 = ln.index('|'); fixed_ = [int(z) for z in ln[1:k3].split(',')]; ln = ln[k3 + 1:]
            gapt = 6
            if ln.startswith('%'):                         # '%N' = ⇥ 조각 나눌 틈 기준(기본 6px 초과)
                k3 = 1
                while k3 < len(ln) and ln[k3].isdigit():
                    k3 += 1
                gapt = int(ln[1:k3]); ln = ln[k3:]
            if '⇥' in ln:                                  # 원래 틈(gapt px 넘는)으로 나눈 조각 자리에 하나씩 — '=' 조각은 원본 복원
                sub_ = img[it['y0']:it['y1'], it['x0']:it['x1']] > 0
                cols = np.nonzero(sub_.any(0))[0]; runs = [[cols[0], cols[0] + 1]]
                for c_ in cols[1:]:
                    if c_ - runs[-1][1] > gapt:
                        runs.append([c_, c_ + 1])
                    else:
                        runs[-1][1] = c_ + 1
                pcs = ln.split('⇥')
                if fixed_:
                    ends_ = fixed_[1:] + [(it['x1'] + 7) // 8 * 8]
                    runs = [[x_ - it['x0'], e_ - it['x0'] - 1] for x_, e_ in zip(fixed_, ends_)]
                for q, t in enumerate(pcs):
                    a0, a1 = runs[q] if q < len(runs) else (runs[-1][1] + 8, runs[-1][1] + 208)
                    lim = (runs[q + 1][0] - 4) if q + 1 < len(runs) and q + 1 < len(pcs) else (right - it['x0'])
                    if fixed_:
                        lim = runs[q][1] if q < len(runs) else lim
                    if c.get('scrw'):                       # 화면 폭 넘기지 않게(설정 «어려움»)
                        lim = min(lim, c['scrw'] - it['x0'])
                    if t == '=':
                        last = runs[-1][1] if q == len(pcs) - 1 else a1
                        new[it['y0']:it['y1'], it['x0'] + a0:it['x0'] + last] = img[it['y0']:it['y1'], it['x0'] + a0:it['x0'] + last]
                        continue
                    if not t.strip():
                        continue
                    if c.get('aa'):
                        mk = aa_cov(t, dh, vs)
                        if mk.shape[1] > lim - a0:
                            mk = aa_fit(mk, lim - a0)
                    else:
                        mk = K.render_line(K.line_mask(t), dh)
                        if vs == 2:
                            mk = np.repeat(mk, 2, axis=0)
                        if mk.shape[1] > lim - a0:
                            mk = K.squeeze(mk, lim - a0)
                    pr_ = img[it['y0']:it['y1'], it['x0'] + a0:it['x0'] + (a1 if q < len(runs) else a0 + 1)]     # 조각 색 = 그 원래 조각의 최다 색
                    cnt_ = collections.Counter(pr_[pr_ > 0].tolist()); tot_ = sum(cnt_.values())
                    lum_ = lambda z: sum(((crb[((c['palsup'] * 16 + it['pal']) * 16 + z) & 0x7FF] >> s_) & 31) for s_ in (0, 5, 10))
                    cand_ = [z for z, k_ in cnt_.items() if k_ >= 0.15 * tot_]
                    fq = max(cand_, key=lum_) if cand_ and q < len(runs) else it['fill']   # 조각 색 = 15% 넘게 쓰인 색 중 가장 밝은 것
                    pp_ = it['pal']
                    if q < len(runs):                       # 조각 팔레트 = 원래 조각 칸들의 최다 팔레트(難 칸만 흰 팔레트 등)
                        cc_ = pal[it['y0'] // 8:(it['y1'] + 7) // 8, (it['x0'] + a0) // 8:(it['x0'] + a1 + 7) // 8]
                        pp_ = collections.Counter(cc_.ravel().tolist()).most_common(1)[0][0]
                    if c.get('aa'):
                        aa_put(new, npal, mk, y + max(0, it['h'] - mk.shape[0]) // 2, it['x0'] + a0, fq, pp_, c, crb)
                    else:
                        K.place(new, npal, mk, y + max(0, it['h'] - mk.shape[0]) // 2, it['x0'] + a0, fq, it['edge'], pp_, 0, fq)
                y += dh * vs; continue
            big = it['h'] >= 36 and n == 1
            K.WEIGHT = b'Black' if (big or c.get('black')) else None
            avail = right - it['x0'] - ind
            cov = None
            if c.get('aa'):
                cov = aa_cov(ln, dh, vs); K.WEIGHT = None
                if c.get('black'):                       # 원본 획 굵기 맞춤(가로 1px)
                    cov = np.minimum(1, cov + np.pad(cov, ((0, 0), (1, 0)))[:, :-1])
                if cov.shape[1] > avail:
                    cov = aa_fit(cov, avail) if cov.shape[1] * K.MIN_SQ <= avail else aa_fit(cov, avail, int(cov.shape[0] * avail / (cov.shape[1] * K.MIN_SQ)))
                m = (cov >= 0.5).astype(np.uint8)
            else:
                m = K.render_line(K.line_mask(ln), dh)
                K.WEIGHT = None
                if vs == 2:
                    m = np.repeat(m, 2, axis=0)
                if m.shape[1] > avail:
                    m = K.squeeze(m, avail) if m.shape[1] * K.MIN_SQ <= avail else K.squeeze(m, avail, int(m.shape[0] * avail / (m.shape[1] * K.MIN_SQ)))
            x = it['x1'] - m.shape[1] if al == 'R' else it['x0'] + ind
            yy = y + (max(0, it['h'] - m.shape[0]) // 2 if n == 1 else 0)
            if big:                                    # 큰 제목: 가로 1px 굵게 + 오른쪽 아래 그림자(테두리색) + 채움
                m = np.maximum(m, np.pad(m, ((0, 0), (1, 0)))[:, :-1])
                if cov is not None:
                    cov = np.maximum(cov, np.pad(cov, ((0, 0), (1, 0)))[:, :-1])
                src_ = img[it['y0']:it['y1'], it['x0']:it['x1']]           # 그림자 색 = 원본 채움 화소의 오른쪽 아래(+2,+2) 자리 색 최빈값
                sh_ = src_[2 * vs:, 2:][(src_[:-2 * vs, :-2] == it['fill']) & (src_[2 * vs:, 2:] != it['fill']) & (src_[2 * vs:, 2:] > 0)]
                shc = collections.Counter(sh_.tolist()).most_common(1)[0][0] if len(sh_) else it['edge']
                if cov is not None and c.get('fill_w'):    # 원래 잉크 가로 범위와 똑같이
                    cov = aa_fit(cov, it['x1'] - it['x0'] - 8); m = (cov >= 0.5).astype(np.uint8); x = it['x0'] + 2   # 굵게 1px·그림자 2px 까지 원래 범위 안
                    yy = it['y0'] + max(0, (it['h'] - cov.shape[0]) // 2)
                elif K.SNAP:                               # 격자 맞춤은 채움 위치에만 — 그림자를 따로 맞추면 8px 옆으로 밀려 막대가 됨
                    x = (x + 4) // 8 * 8; yy = (yy + 4) // 8 * 8 if K.SNAP > 1 else yy
                snap_, K.SNAP = K.SNAP, 0
                K.place(new, npal, (m >= max(1, int(m.max()) // 2)).astype(np.uint8), yy + 2 * vs, x + 2, shc, 0, it['pal'], 0, shc)   # 진한 화소만
                if cov is not None:
                    aa_put(new, npal, cov, yy, x, it['fill'], it['pal'], c, crb, snap=False)
                else:
                    K.place(new, npal, m, yy, x, it['fill'], 0, it['pal'], 0, it['alt'])   # 그림자 다음 채움(place 는 덮어씀)
                K.SNAP = snap_
            elif cov is not None and c.get('fill_w'):     # 원래 잉크 가로 범위와 똑같이(게임이 비어 있지 않은 칸만 복사하는 화면)
                cov = aa_fit(cov, it['x1'] - it['x0'])
                aa_put(new, npal, cov, yy, it['x0'], it['fill'], it['pal'], c, crb, snap=False, edge=(it['edge'] if (K.EDGE and c.get('aa_edge')) else None), vs=vs)
            elif cov is not None:
                aa_put(new, npal, cov, yy, x, it['fill'], it['pal'], c, crb, edge=(it['edge'] if (K.EDGE and c.get('aa_edge')) else None), vs=vs)
            else:
                K.place(new, npal, m, yy, x, it['fill'], it['edge'], it['pal'], 0, it['alt'])
            y += m.shape[0] + (it['h'] - m.shape[0] * n) // max(1, n - 1) if n > 1 else 0
    for (wy0, wy1, sx0, sx1, dx0) in c.get('wrap', []):   # 페이지 경계 넘는 줄: 넘친 부분을 원래 조각 자리로
        new[wy0:wy1, dx0:dx0 + (sx1 - sx0)] = new[wy0:wy1, sx0:sx1]
        new[wy0:wy1, sx0:sx1] = img[wy0:wy1, sx0:sx1]
        npal[wy0 // 8:(wy1 + 7) // 8, dx0 // 8:(dx0 + sx1 - sx0) // 8] = npal[wy0 // 8:(wy1 + 7) // 8, sx0 // 8:sx1 // 8]
    if c.get('post'):                                     # 화면별 국소 손질
        globals()[c['post']](c, img, new, npal, crb)
    if os.environ.get('NBGDBG'):
        np.save(os.path.join(ROOT, 'work', 'nbg', '%s_new.npy' % name), new); np.save(os.path.join(ROOT, 'work', 'nbg', '%s_npal.npy' % name), npal)
    # 재배치
    nt = len(tiles) // 32; TL = [tiles[i * 32:i * 32 + 32] for i in range(nt)]
    newents = list(ents); changed = {}
    for i, e in enumerate(ents):
        r, x = divmod(i, w)
        if not mine[r, x]:
            if (new[r * 8:r * 8 + 8, x * 8:x * 8 + 8] > 0).any() and not (img[r * 8:r * 8 + 8, x * 8:x * 8 + 8] > 0).any():
                pass
            continue
        blk = new[r * 8:r * 8 + 8, x * 8:x * 8 + 8]; b = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
        if TL[tidx(c, e, nt)] != b or (e >> 12) != npal[r, x]:
            changed[(r, x)] = (b, int(npal[r, x]))
    keep = collections.Counter(tidx(c, e, nt) for i, e in enumerate(ents) if tidx(c, e, nt) is not None and divmod(i, w) not in changed)
    was = {tidx(c, ents[r * w + x], nt) for (r, x) in changed}
    free = sorted(t for t in was if not keep[t])
    have = {TL[t]: t for t in range(nt) if keep[t]}; used = {}
    freeset = set(free)
    for (r, x), (b, p) in sorted(changed.items()):        # 1단계 제자리: 원래 번호 그대로(코드가 고정 번호로 떼어 쓰는 칸 — 설정 값 ステレオ·숫자)
        t0 = tidx(c, ents[r * w + x], nt)
        if b not in have and b not in used and t0 in freeset:
            freeset.discard(t0); free.remove(t0); TL[t0] = b; used[b] = t0
    for (r, x), (b, p) in sorted(changed.items()):
        if b in have:
            t = have[b]
        elif b in used:
            t = used[b]
        else:
            if not free:
                need = len({bb for bb, _ in changed.values()} - set(have))
                raise SystemExit('%s 타일 자리 부족: 필요 %d 빈자리 %d' % (name, need, len(used)))
            t = free.pop(0); freeset.discard(t); TL[t] = b; used[b] = t
        addr = c['tiles'][1] + t * 32
        newents[r * w + x] = (p << 12) | ((addr // 0x20) & 0xFFF)
    nb = b''.join(TL); comp = sglz.encode(nb); assert sglz.decode(comp, 0)[0] == nb
    if len(comp) > olen:
        raise SystemExit('%s 압축 초과 %d > %d' % (name, len(comp), olen))
    mp, moff = c['map'][0], c['map'][1]
    outs = {}
    base_of = lambda f: open(os.path.join(OUT, f), 'rb').read() if os.path.exists(os.path.join(OUT, f)) else open(os.path.join(DISC, f), 'rb').read()
    tdn = bytearray(base_of(fp)); tdn[off:off + len(comp)] = comp; outs[fp] = tdn   # 쓸 때는 다른 화면이 고친 부분 위에 합침
    mdn = bytearray(base_of(mp)) if mp != fp else outs[fp]
    # 맵은 «이 화면이 바꾼 칸만» 합침 — 같은 맵을 쓰는 다른 그림 세트 화면(opt1b·opt1c 등)의 변경을 지우지 않게
    for k_, (r, x) in enumerate(c['_order']):
        if newents[r * w + x] != ents[r * w + x]:
            struct.pack_into('>H', mdn, moff + k_ * 2, newents[r * w + x])
    outs[mp] = mdn
    for k2, data in outs.items():
        pth = os.path.join(OUT, k2); os.makedirs(os.path.dirname(pth), exist_ok=True); open(pth, 'wb').write(bytes(data))
    # 미리보기(원본|새것) — 인터레이스면 가로 2배로 비율 맞춤
    import pm_detail as P
    cr = P.cram_of(c['state']); sup = c['palsup']
    rgb = lambda e: np.stack([(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3], -1).astype(np.uint8)
    def col(a, pp):
        o = np.zeros(a.shape + (3,), np.uint8) + np.array((30, 10, 30), np.uint8)
        for r in range(a.shape[0] // 8):
            for x in range(a.shape[1] // 8):
                blk = a[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
                if blk.any():
                    cc = rgb(cr[((sup * 16 + pp[r, x]) * 16 + blk) & 0x7FF]); cc[blk == 0] = (30, 10, 30); o[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = cc
        return o
    ys = np.nonzero((img > 0).any(1) | (new > 0).any(1))[0]; y1 = min(img.shape[0], ys.max() + 4) if len(ys) else img.shape[0]
    a = col(img[:y1], pal); b2 = col(new[:y1], npal)
    pim = Image.fromarray(np.concatenate([a, np.full((y1, 6, 3), 128, np.uint8), b2], 1))
    if c['interlace']:
        pim = pim.resize((pim.width * 2, pim.height), Image.NEAREST)
    pim.save(os.path.join(ROOT, 'work', 'nbg', '%s_preview.png' % name))
    print(name, dict(바뀐칸=len(changed), 새타일=len(used), 남은빈자리=len(free), 압축=(len(comp), olen)))


if __name__ == '__main__':
    nm, act = sys.argv[1], sys.argv[2]
    list_items(nm) if act == 'items' else build(nm)
