# -*- coding: utf-8 -*-
"""세가 PRS(LZ77) 해제 — 후보 시험용(2026-10-17). prs_dec(data, start) → (풀린 바이트, 끝 위치)"""


def prs_dec(src, i=0, limit=1 << 22):
    out = bytearray(); bits = 0; ctl = 0

    def bit():
        nonlocal bits, ctl, i
        if bits == 0:
            ctl = src[i]; i += 1; bits = 8
        b = ctl & 1; ctl >>= 1; bits -= 1
        return b
    while len(out) < limit:
        if bit():
            out.append(src[i]); i += 1; continue
        if bit():
            lo, hi = src[i], src[i + 1]; i += 2
            off = ((hi << 5) | (lo >> 3)) - 0x2000
            if off == -0x2000:
                break
            n = lo & 7
            n = src[i] + 1 if n == 0 else n + 2
            if (lo & 7) == 0:
                i += 1
        else:
            n = (bit() << 1 | bit()) + 2
            off = src[i] - 0x100; i += 1
        for _ in range(n):
            out.append(out[len(out) + off])
    return bytes(out), i
