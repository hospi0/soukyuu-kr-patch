# -*- coding: utf-8 -*-
r"""창궁홍련대 «GF» 리소스 압축 해제 (0SSSOQ.BIN 0x06004D54 역해석, 2026-10-17 정적 추적)
  리소스 묶음(TITLE/*_PNT.BIN 등): 전역 표(0x060B59B8 가 가리키는 곳) 항목 8B = [종류 u16 'BD'|'CD'|'GF'|'GP'][u16][데이터 포인터 u32]
  GF 데이터 = 스트림. 제어 바이트 c(부호 있음):
     c == 0           → 끝
     c  > 0           → 다음 c 바이트 그대로
     c  < 0           → 길이 n = c & 0x7F, 다음 바이트 d → 풀린 데이터의 (지금 − d − 1) 에서 n 바이트 복사(겹침 허용)
  호출부 0x06051880: 고리 버퍼(크기 = 인수 R5)에 풀어 DMA 로 VRAM 에 옮김 — 결과는 이어 붙이면 같다.
"""


def decode(src, i=0, limit=1 << 22):
    out = bytearray()
    while len(out) < limit:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c
        else:
            n = c & 0x7F; d = src[i]; i += 1
            p = len(out) - d - 1
            for k in range(n):
                out.append(out[p + k])
    return bytes(out), i


def encode(data):
    """최적 분할(DP) 압축 — 리터럴 묶음 1..127(비용 1+L) · 복사 길이 2..127 거리 1..256(비용 2) · 끝 0.
    겹침 복사 허용(거리 < 길이). 결과는 decode() 로 원본과 바이트 일치."""
    n = len(data)
    # 각 위치의 최장 일치 (길이, 거리)
    best = [(0, 0)] * n
    heads = {}
    for i in range(n):
        if i + 2 <= n:
            key = data[i:i + 2]
            cand = heads.get(key)
            bl = bd = 0
            if cand:
                for j in reversed(cand):
                    d = i - j
                    if d > 256:
                        break
                    L = 0
                    while L < 127 and i + L < n and data[j + L] == data[i + L]:
                        L += 1
                    if L > bl:
                        bl, bd = L, d
                        if L == 127:
                            break
                cand.append(i)
                if len(cand) > 300:
                    del cand[:len(cand) - 256]
            else:
                heads[key] = [i]
            best[i] = (bl, bd)
    INF = 1 << 60
    cost = [INF] * (n + 1); cost[n] = 0
    choice = [None] * (n + 1)
    for i in range(n - 1, -1, -1):
        c0 = INF; ch = None
        for L in range(1, min(127, n - i) + 1):
            c = 1 + L + cost[i + L]
            if c < c0:
                c0, ch = c, ('L', L)
        bl, bd = best[i]
        for L in range(2, bl + 1):
            c = 2 + cost[i + L]
            if c < c0:
                c0, ch = c, ('M', L, bd)
        cost[i] = c0; choice[i] = ch
    out = bytearray(); i = 0
    while i < n:
        ch = choice[i]
        if ch[0] == 'L':
            L = ch[1]; out.append(L); out += data[i:i + L]; i += L
        else:
            _, L, d = ch; out.append(0x80 | L); out.append(d - 1); i += L
    out.append(0)
    return bytes(out)
