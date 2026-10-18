# -*- coding: utf-8 -*-
r"""이어하기 한글 결과를 work/out/ 의 파일로 (2026-10-17) — 맵(MAP0~GF 시작 전까지)·GF(원래 자리, 원래 길이 이하) 제자리
  python tools/cont_write.py [X…]
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import cont_kr as C, sglz
OUT = os.path.join(ROOT, 'work', 'out')
for X in (sys.argv[1:] or list('BOCASL')):
    C.main.__globals__['sys'].argv = ['cont_kr.py', X]
    C.main()                                             # 새 그림(npy) 다시 만들기 — 현재 설정
    path, go, tips = C.STAGES[X]
    mbytes, tiles, comp, rep = C.rebuild(X)
    src = os.path.join(OUT, path)
    d = bytearray(open(src if os.path.exists(src) else os.path.join(C.DISC, path), 'rb').read())
    orig_end = sglz.decode(open(os.path.join(C.DISC, path), 'rb').read(), go)[1]   # 디스크 원본 기준(out 은 이미 짧아졌을 수 있음)
    assert len(comp) <= orig_end - go, (X, len(comp), orig_end - go)
    head = C.MAP_HEAD.get(X, go - 0x1680)                # 맵 = 머리 줄부터 GF 시작 전까지만(2스테이지는 마지막 칸이 GF 와 겹침)
    orig = open(os.path.join(C.DISC, path), 'rb').read()
    d[:head] = orig[:head]                               # ★머리 앞은 맵이 아님(물체 표·팔레트) — 예전 판이 덮어쓴 것 되돌림(2026-10-18 크래시)
    d[head:go] = mbytes[head - C.MAP0:go - C.MAP0]
    assert 0xFFFF not in struct.unpack('>%dH' % ((go - head) // 2), bytes(d[head:head + (go - head) // 2 * 2])) or X == 'O'
    d[go:go + len(comp)] = comp
    assert sglz.decode(bytes(d), go)[0] == tiles
    os.makedirs(os.path.dirname(os.path.join(OUT, path)), exist_ok=True)
    open(os.path.join(OUT, path), 'wb').write(bytes(d))
    print(X, path, rep)
