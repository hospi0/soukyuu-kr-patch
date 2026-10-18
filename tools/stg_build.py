# -*- coding: utf-8 -*-
r"""게임 안 문구 한글 그림 → 실제 데이터(맵 SS_ST?.BIN + 문장 그림 세트) 재배치 (2026-10-17)
  입력: tools/stg_kr.py 결과(work/stg/kr_<X>.npz) · 출력: work/out/<원래 경로> (디스크에는 아직 안 씀)
  원칙: 빈자리 = 그 세트에서 «바뀐 칸만 쓰던» 타일뿐(맵이 안 가리키는 타일 = 코드가 쓰는 날짜 숫자 등 → 보호, 그룹 밖 칸이 가리키는 타일도 보호).
        출격 전(PRE, GF 압축) = 새 압축 ≤ 원래 압축 길이 · 결과/중간(CGB 무압축) = 타일 수 그대로.
        검산: 새 맵 + 새 타일로 다시 그린 세트 그룹 == 새 그림(화소 단위).
  python tools/stg_build.py <X|all>
"""
import collections
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402
import stg_blocks as S  # noqa: E402
import stg_items as I  # noqa: E402

OUT = os.path.join(ROOT, 'work', 'out')
# 출격 전 큰 이름 아래 읽기 줄(가타카나)이 «다음 세트 그룹 첫 행»으로 잘못 묶여 안 지워진 칸 → 빈칸(ec00 = 0번 빈 타일)으로 (2026-10-18 하스피 «돈류 밑 일본어 찌꺼기»)
#   C 35행 = ドンリュウ 아랫줄 + 34행 32칸 탁점 조각 · L 35행 = バクザン 아랫줄 + 34행 37칸 조각. 행 전체가 읽기 줄뿐(다른 글자 없음)
# 출격 전 세트 타일 0x01~0xCE = 코드가 날짜·시각을 쓰는 4×4 숫자(0~9)·年月日時分 글리프 — 맵 칸(«5000メートル» 등)이 같이 써도 절대 재사용 금지
#   (3스테이지에서 5000 을 다시 그리며 0·5 타일을 비워 새 글자로 덮음 → 연도 2056 의 0·5 가 깨짐, 2026-10-18)
PRE_CODE_TILES = 0xCF
EXTRA_BLANK = {'C': [(35, range(29, 39)), (34, [32])], 'L': [(35, range(30, 38)), (34, [37])]}


def tidx(e):
    return (e & 0xFFF) - 0xC00


def tile_bytes(blk):
    return bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())


def fit_pre(X, grp, ents, T, z):
    """출격 전(PRE): 게임이 «원래 잉크가 있던 칸»만 화면에 복사(2026-10-18 실기 «가»·«범» 잘림)
    → 항목마다 새 글자를 원래 잉크 칸 안으로 옮김(dx·dy)·필요하면 가로로 줄임. 못 맞추면 중단."""
    its = [it for it in I.items(X)[0] if it['set'] == 'PRE']
    newz = {g: z['new%d' % g].copy() for g, (r0, r1, k) in enumerate(grp) if k == 'PRE'}
    for g, new in newz.items():
        r0, r1, k = grp[g]; tiles = T[k]; nt = len(tiles) // 32
        ok = np.zeros(((r1 - r0), 64), bool)
        for r in range(r0, r1):
            for x in range(64):
                ti = tidx(ents[r * 64 + x])
                ok[r - r0, x] = ents[r * 64 + x] not in (0, 0xFFFF) and 0 <= ti < nt and any(tiles[ti * 32:ti * 32 + 32])
        allowed = np.repeat(np.repeat(ok, 8, 0), 8, 1)
        for it in [t for t in its if t['grp'] == g]:
            y0, y1 = max(0, it['y0'] - 10), min(new.shape[0], it['y1'] + 10)
            x0, x1 = max(0, it['x0'] - 16), min(new.shape[1], it['x1'] + 16)
            src = new[y0:y1, x0:x1].copy()
            if not src.any() or not (src.astype(bool) & ~allowed[y0:y1, x0:x1]).any():
                continue
            new[y0:y1, x0:x1] = 0
            best = None
            for sc in (1.0, 0.96, 0.92, 0.88, 0.84, 0.8):
                zone = src
                if sc < 1.0:
                    ys0, xs0 = np.nonzero(src); a_, b_ = xs0.min(), xs0.max() + 1
                    part = src[:, a_:b_]; nw = max(1, int(part.shape[1] * sc))
                    zone = np.zeros_like(src); zone[:, a_:a_ + nw] = part[:, (np.arange(nw) * part.shape[1] / nw).astype(int)]
                ys, xs = np.nonzero(zone)
                for dy in range(-6, 7):
                    for dx in range(-14, 15):
                        ny, nx = ys + dy, xs + dx
                        if ny.min() < 0 or nx.min() < 0 or ny.max() >= zone.shape[0] or nx.max() >= zone.shape[1]:
                            continue
                        bad = int((~allowed[y0:y1, x0:x1][ny, nx]).sum() + (new[y0:y1, x0:x1][ny, nx] > 0).sum())
                        cost = (bad, abs(dx) + abs(dy), -sc)
                        if best is None or cost < best[0]:
                            best = (cost, zone, dx, dy)
                if best[0][0] == 0:
                    break
            (bad, _, _), zone, dx, dy = best
            ys, xs = np.nonzero(zone)
            if bad:
                keep = allowed[y0:y1, x0:x1][ys + dy, xs + dx]
                print('  %s 항목 (%d,%d) 원래 칸 밖 %d화소 - 잘라냄' % (X, it['x0'], it['y0'], int((~keep).sum())))
                ys, xs = ys[keep], xs[keep]
            new[y0 + ys + dy, x0 + xs + dx] = zone[ys, xs]
        z['new%d' % g] = new


def build(X):
    path, sets = S.SETS[X]
    d, ents, n = S.load_map(path)
    grp, _, T = S.classify_rows(X)
    z = dict(np.load(os.path.join(ROOT, 'work', 'stg', 'kr_%s.npz' % X)))
    newents = list(ents)
    ingrp = {}
    for g, (r0, r1, k) in enumerate(grp):
        for r in range(r0, r1):
            ingrp[r] = (g, k)
    report = {}
    outputs = {}
    # fit_pre(X, grp, ents, T, z)   # 2026-10-18 시험 — 글자를 잘라내서 쓰지 않음
    for k, spec in sets.items():
        tiles = T[k]; nt = len(tiles) // 32
        TL = [tiles[i * 32:i * 32 + 32] for i in range(nt)]
        changed = {}
        for g, (r0, r1, kk) in enumerate(grp):
            if kk != k:
                continue
            new = z['new%d' % g]; pal = z['pal%d' % g]
            for r in range(r0, r1):
                for x in range(64):
                    e = ents[r * 64 + x]
                    if e in (0, 0xFFFF):
                        continue
                    blk = new[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8]
                    b = tile_bytes(blk)
                    ti = tidx(e)
                    same = 0 <= ti < nt and TL[ti] == b and (e >> 12) == pal[r - r0, x]
                    if not same:
                        changed[(r, x)] = (b, int(pal[r - r0, x]))
        keep = collections.Counter()
        for i, e in enumerate(ents):
            if e in (0, 0xFFFF):
                continue
            r, x = divmod(i, 64)
            gi = ingrp.get(r)
            if gi and gi[1] != k:
                continue                                  # 다른 세트 그룹 칸은 이 세트와 무관
            if (r, x) in changed:
                continue
            ti = tidx(e)
            if 0 <= ti < nt:
                keep[ti] += 1
        was = {tidx(ents[r * 64 + x]) for (r, x) in changed}
        free = sorted(i for i in was if 0 <= i < nt and not keep[i] and not (k == 'PRE' and i < PRE_CODE_TILES))
        blank = next((i for i in range(nt) if keep[i] and not any(TL[i]) and not (k == 'PRE' and i < PRE_CODE_TILES)), None)
        # PRE 코드 타일(날짜 글리프 등, < 0xCF)은 date_kr 가 나중에 덮어씀 → 같은 그림이어도 재사용 금지(2026-10-18 3스테이지 «가» 깨짐)
        have = {TL[i]: i for i in range(nt) if keep[i] and not (k == 'PRE' and i < PRE_CODE_TILES)}
        used_new = {}
        for (r, x), (b, p) in sorted(changed.items()):
            if not any(b) and blank is not None:
                ti = blank
            elif b in have:
                ti = have[b]
            elif b in used_new:
                ti = used_new[b]
            else:
                if not free:
                    need = len({bb for bb, _ in changed.values() if any(bb)} - set(have))
                    raise SystemExit('%s %s 타일 자리 부족: 필요 %d 빈자리 %d (바뀐칸 %d, 전체 %d)' % (X, k, need, len(used_new), len(changed), nt))
                ti = free.pop(0); TL[ti] = b; used_new[b] = ti
            newents[r * 64 + x] = (p << 12) | ((0xC00 + ti) & 0xFFF)
        nb = b''.join(TL)
        # 검산
        for g, (r0, r1, kk) in enumerate(grp):
            if kk != k:
                continue
            new = z['new%d' % g]
            for r in range(r0, r1):
                for x in range(64):
                    e = newents[r * 64 + x]
                    if e in (0, 0xFFFF):
                        continue
                    o = tidx(e) * 32
                    if not 0 <= o < len(nb):
                        continue
                    t = np.frombuffer(nb[o:o + 32], np.uint8); px = np.stack([t >> 4, t & 15], 1).ravel().reshape(8, 8)
                    if not (px == new[(r - r0) * 8:(r - r0) * 8 + 8, x * 8:x * 8 + 8]).all():
                        raise SystemExit('%s %s 검산 불일치 행 %d 칸 %d' % (X, k, r, x))
        if ':' in spec[2:]:
            fp, off = spec.rsplit(':', 1); off = int(off, 16)
            src = open(os.path.join(S.DISC, fp), 'rb').read()
            _, end = sglz.decode(src, off)
            comp = sglz.encode(nb)
            assert sglz.decode(comp, 0)[0] == nb
            if len(comp) > end - off:
                raise SystemExit('%s %s 압축 초과 %d > %d' % (X, k, len(comp), end - off))
            body = bytearray(outputs.get(fp, src))
            body[off:off + len(comp)] = comp
            outputs[fp] = bytes(body)
            report[k] = dict(바뀐칸=len(changed), 새타일=len(used_new), 남은빈자리=len(free), 원본압축=end - off, 새압축=len(comp))
        else:
            assert len(nb) == len(tiles)
            outputs[spec] = nb
            report[k] = dict(바뀐칸=len(changed), 새타일=len(used_new), 남은빈자리=len(free), 타일수=nt)
    for r, xs in EXTRA_BLANK.get(X, []):
        for x in xs:
            assert newents[r * 64 + x] not in (0, 0xFFFF)
            newents[r * 64 + x] = 0xEC00
    mb = bytearray(d); mb[4:4 + len(newents) * 2] = struct.pack('>%dH' % len(newents), *newents)
    outputs[path] = bytes(mb)
    for fp, data in outputs.items():
        p = os.path.join(OUT, fp); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
    return report, list(outputs)


def outside_cells(X):
    """새 글자 칸 중 «원래 항목 사각형(칸 단위)» 밖이면서 원래 빈칸이던 칸 — 게임은 원래 사각형만 복사하므로 잘리거나 찌꺼기(2026-10-18 하스피)"""
    B = (0, 0xEC00, 0xFFFF)
    path, _ = S.SETS[X]
    n = open(os.path.join(OUT, path), 'rb').read(); o = open(os.path.join(S.DISC, path), 'rb').read()
    N = struct.unpack('>%dH' % ((len(n) - 4) // 2), n[4:]); O = struct.unpack('>%dH' % ((len(o) - 4) // 2), o[4:])
    its, grp, _, _ = I.items(X); bad = []
    for g, (a, b, k) in enumerate(grp):
        rects = [(a + it['y0'] // 8, a + (it['y1'] - 1) // 8, it['x0'] // 8, (it['x1'] - 1) // 8) for it in its if it['grp'] == g]
        bad += [(k, r, x) for r in range(a, b) for x in range(44) if N[r * 64 + x] not in B and O[r * 64 + x] in B
                and not any(r0 <= r <= r1 and c0 <= x <= c1 for r0, r1, c0, c1 in rects)]
    return bad


def main():
    xs = 'BOCASL' if sys.argv[1] == 'all' else sys.argv[1]
    fail = False
    for X in xs:
        try:
            rep, outs = build(X)
            print(X, rep, '→', outs)
        except SystemExit as e:
            print('✗', e); fail = True
            continue
        bad = outside_cells(X)
        if bad:
            print('✗ %s 원래 칸 밖 %d칸: %s' % (X, len(bad), bad[:10])); fail = True
    if fail:
        raise SystemExit('★원래 칸 밖에 그린 칸이 있음 — 지정(stg_spec)을 고칠 것')


if __name__ == '__main__':
    main()
