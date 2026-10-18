# -*- coding: utf-8 -*-
r"""특별 설정(TOK_PNT) 메뉴를 «원래 타일 번호 제자리»로 (2026-10-18)
  강조 표시 = 게임이 원래 맵 무늬(칸마다 원래 타일 번호)로 같은 GF(0x209C4, VRAM 0x78000 에 한 벌 더)를 NBG3 에 흰색으로 덮어 그림.
  → 메뉴 칸은 원래 타일 번호를 그대로 쓰고 그 타일에 새 그림을 넣어야 강조가 깨지지 않음. 원래 빈칸에는 잉크 금지(줄마다 위치를 옮겨 맞춤).
  입력: nbg_kr tok1 의 새 그림(NBGDBG=1 → work/nbg/tok1_new.npy). 머리·단위 칸도 같은 방식(빈칸에 잉크면 자유 타일).
  출력: work/out/TITLE/TOK_PNT.BIN 의 맵(0x33600)·GF(0x209C4) 제자리 · 검산(다시 그린 그림 == 새 그림, 메뉴 칸 = 원래 번호)
  python tools/tok_inplace.py
"""
import collections
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import nbg_kr as NK  # noqa: E402

MAP, GF, W, ROWS, BASE = 0x33600, 0x209C4, 64, 80, 0x880


def main():
    c = NK.SCREENS['tok1']
    o = open(os.path.join(ROOT, 'work', 'disc', 'TITLE', 'TOK_PNT.BIN'), 'rb').read()
    O = list(struct.unpack('>%dH' % (W * ROWS), o[MAP:MAP + W * ROWS * 2]))
    T, oend = sglz.decode(o, GF); nt = len(T) // 32
    TL = [T[i * 32:i * 32 + 32] for i in range(nt)]
    tid = lambda e: (e & 0xFFF) - BASE
    blank = lambda e: not (0 <= tid(e) < nt) or not any(TL[tid(e)])
    new = np.load(os.path.join(ROOT, 'work', 'nbg', 'tok1_new.npy')).copy()
    # 원래 그림
    orig = np.zeros_like(new)
    for i, e in enumerate(O):
        r, x = divmod(i, W)
        if r * 8 + 8 <= orig.shape[0] and not blank(e):
            a = np.frombuffer(TL[tid(e)], np.uint8).astype(int)
            orig[r * 8:r * 8 + 8, x * 8:x * 8 + 8] = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
    # 1) 메뉴·단위 구역: 새 잉크가 «원래 잉크 칸» 안에만 오도록 이동(dx,dy 탐색)
    menu_cells = set()
    for zx0, zy0, zx1, zy1 in c['zones'][1:]:
        zone = new[zy0:zy1, zx0:zx1].copy(); new[zy0:zy1, zx0:zx1] = 0
        allowed = np.zeros((zy1 - zy0, zx1 - zx0), bool)
        for y in range(zy0, zy1, 1):
            for x in range(zx0, zx1):
                r, cx = y // 8, x // 8
                allowed[y - zy0, x - zx0] = not blank(O[r * W + cx])
        best = None
        src = zone
        for sc in (1.0, 0.95, 0.9, 0.85, 0.8):
            if sc < 1.0:                                  # 가로로 줄여 다시(최근접 — 색 번호 보존)
                ys0, xs0 = np.nonzero(src)
                x0_, x1_ = xs0.min(), xs0.max() + 1
                part = src[:, x0_:x1_]; nw = max(1, int(part.shape[1] * sc))
                idx = (np.arange(nw) * part.shape[1] / nw).astype(int)
                zone = np.zeros_like(src); zone[:, x0_:x0_ + nw] = part[:, idx]
            best = None
            for dy in range(-6, 7):
                for dx in range(-12, 13):
                    ys, xs = np.nonzero(zone)
                    ny, nx = ys + dy, xs + dx
                    if ny.min() < 0 or nx.min() < 0 or ny.max() >= zone.shape[0] or nx.max() >= zone.shape[1]:
                        continue
                    bad = int((~allowed[ny, nx]).sum())
                    cost = (bad, abs(dx) + abs(dy))
                    if best is None or cost < best[0]:
                        best = (cost, dx, dy)
            if best[0][0] == 0:
                break
        (bad, _), dx, dy = best
        if bad:
            raise SystemExit('구역 %s: 원래 빈칸에 잉크 %d화소 남음(dx%d dy%d) — 글자를 줄일 것' % ((zx0, zy0), bad, dx, dy))
        ys, xs = np.nonzero(zone)
        new[zy0 + ys + dy, zx0 + xs + dx] = zone[ys, xs]
        for y in range(zy0, zy1):
            for x in range(zx0, zx1, 8):
                menu_cells.add((y // 8, x // 8))
    # 2) 칸별 타일: 원래 잉크 칸은 원래 번호 제자리, 그 밖(머리 등)에서 충돌·빈칸 잉크면 자유 타일
    need = {}
    for r in range(ROWS):
        for x in range(W):
            if r * 8 + 8 > new.shape[0]:
                continue
            blk = new[r * 8:r * 8 + 8, x * 8:x * 8 + 8]
            if (blk == orig[r * 8:r * 8 + 8, x * 8:x * 8 + 8]).all():
                continue
            need[(r, x)] = bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())
    refs = collections.defaultdict(list)
    for i, e in enumerate(O):
        if not blank(e):
            refs[tid(e)].append(divmod(i, W))
    newmap = list(O); fixed = {}
    for t, cells in refs.items():
        contents = {need.get(cl, TL[t]) if not (need.get(cl) is not None and not any(need[cl])) else None for cl in cells}
        contents.discard(None)
        if len(contents) <= 1:
            fixed[t] = contents.pop() if contents else None
    # 모든 칸이 빈칸이 된 원래 타일: 메뉴 칸 타일은 «비움»(강조 사본이 원래 번호로 그림 → 옛 조각이 남으면 드러남), 그 밖만 자유 타일
    menu_t = {t for t, cells in refs.items() if any(cl in menu_cells for cl in cells)}
    free = []
    for t, v in fixed.items():
        if v is None:
            if t in menu_t:
                TL[t] = bytes(32)
            else:
                free.append(t)
    used_free = {}
    blank_e = O[0]
    for (r, x), b in sorted(need.items()):
        e = O[r * W + x]
        if not any(b):
            newmap[r * W + x] = (e & 0xF000) | BASE if not blank(e) else e
            continue
        t = tid(e)
        if not blank(e) and fixed.get(t) == b:
            TL[t] = b; continue
        if (r, x) in menu_cells:
            raise SystemExit('메뉴 칸 %s 제자리 불가(원래 빈칸이거나 공유 충돌)' % ((r, x),))
        if b in used_free:
            nt_ = used_free[b]
        else:
            if not free:
                raise SystemExit('자유 타일 부족')
            nt_ = free.pop(0); TL[nt_] = b; used_free[b] = nt_
        newmap[r * W + x] = (e & 0xF000 if not blank(e) else 0x1000) | ((BASE + nt_) & 0xFFF)
    nb = b''.join(TL)
    # 검산: 새 맵 + 새 타일 == 새 그림
    for i, e in enumerate(newmap):
        r, x = divmod(i, W)
        if r * 8 + 8 > new.shape[0]:
            continue
        t = tid(e)
        px = np.zeros((8, 8), int)
        if 0 <= t < nt:
            a = np.frombuffer(nb[t * 32:t * 32 + 32], np.uint8).astype(int); px = np.stack([a >> 4, a & 15], 1).ravel().reshape(8, 8)
        if not (px == new[r * 8:r * 8 + 8, x * 8:x * 8 + 8]).all():
            raise SystemExit('검산 불일치 %s' % ((r, x),))
        if (r, x) in menu_cells and not blank(O[i]) and px.any() and newmap[i] != O[i]:
            raise SystemExit('메뉴 칸 번호 바뀜 %s' % ((r, x),))
    comp = sglz.encode(nb); assert sglz.decode(comp, 0)[0] == nb
    assert len(comp) <= oend - GF, ('압축 초과', len(comp), oend - GF)
    out = bytearray(o)
    out[GF:GF + len(comp)] = comp
    out[MAP:MAP + W * ROWS * 2] = struct.pack('>%dH' % (W * ROWS), *newmap)
    p = os.path.join(ROOT, 'work', 'out', 'TITLE', 'TOK_PNT.BIN'); open(p, 'wb').write(bytes(out))
    print('제자리 완료 · 자유 타일 사용', len(used_free), '· 압축', len(comp), '/', oend - GF)


if __name__ == '__main__':
    main()
