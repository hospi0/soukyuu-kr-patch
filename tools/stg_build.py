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


def tidx(e):
    return (e & 0xFFF) - 0xC00


def tile_bytes(blk):
    return bytes(((blk[:, 0::2] << 4) | blk[:, 1::2]).astype(np.uint8).ravel())


def build(X):
    path, sets = S.SETS[X]
    d, ents, n = S.load_map(path)
    grp, _, T = S.classify_rows(X)
    z = np.load(os.path.join(ROOT, 'work', 'stg', 'kr_%s.npz' % X))
    newents = list(ents)
    ingrp = {}
    for g, (r0, r1, k) in enumerate(grp):
        for r in range(r0, r1):
            ingrp[r] = (g, k)
    report = {}
    outputs = {}
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
        free = sorted(i for i in was if 0 <= i < nt and not keep[i])
        blank = next((i for i in range(nt) if keep[i] and not any(TL[i])), None)
        have = {TL[i]: i for i in range(nt) if keep[i]}
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
    mb = bytearray(d); mb[4:4 + len(newents) * 2] = struct.pack('>%dH' % len(newents), *newents)
    outputs[path] = bytes(mb)
    for fp, data in outputs.items():
        p = os.path.join(OUT, fp); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
    return report, list(outputs)


def main():
    xs = 'BOCASL' if sys.argv[1] == 'all' else sys.argv[1]
    for X in xs:
        try:
            rep, outs = build(X)
            print(X, rep, '→', outs)
        except SystemExit as e:
            print('✗', e)


if __name__ == '__main__':
    main()
