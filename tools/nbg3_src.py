# -*- coding: utf-8 -*-
r"""NBG3 글자층(16색 8×8, 1워드 PNCN) 출처 찾기 (2026-10-17)
  스테이트의 NBG3 맵에서 쓰인 칸 → 그 칸들의 VRAM 범위가 어느 GF 리소스(풀린 결과)와 같은지,
  화면 맵 줄(비어 있지 않은 32칸)이 어느 파일 / 풀린 리소스 안에 있는지.
  python tools/nbg3_src.py s12 s13 s14 ...
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sglz  # noqa: E402

DISC = os.path.join(ROOT, 'work', 'disc')


def all_streams():
    """모든 파일에서 GF 표 항목이 가리킬 수 있는 곳 대신 — 파일 전체를 2바이트마다 시도하면 느리므로 MAP.BIN 표 + 파일 앞 목차만"""
    out = []
    files = {}
    for r, _, fs in os.walk(DISC):
        for f in fs:
            p = os.path.join(r, f); files[os.path.relpath(p, DISC).replace(os.sep, '/')] = open(p, 'rb').read()
    return files


def main():
    files = all_streams()
    for st in sys.argv[1:]:
        D = os.path.join(ROOT, 'work', 'mem', st)
        V = open(os.path.join(D, 'VDP2_VRAM.bin'), 'rb').read()
        r = open(os.path.join(D, 'VDP2_REGS.bin'), 'rb').read()
        reg = lambda o: struct.unpack_from('>H', r, o)[0]
        pncn = reg(0x36); mp = reg(0x4C) & 0xFF; mpof = (reg(0x3C) >> 12) & 7
        base = (mpof * 64 + mp) * 0x2000 if False else mp * 0x2000      # 16색·1워드·8×8 → 맵 1면 = 64×64×2 = 0x2000
        ents = struct.unpack_from('>4096H', V, base)
        sup = pncn & 0x3FF
        cells = set()
        rows = []
        for y in range(32):
            row = ents[y * 64:y * 64 + 64]
            if any(row[:44]):
                rows.append((y, row))
            for v in row[:44]:
                if v:
                    cells.add(((sup >> 2) & 0x1C) << 10 | (v & 0x3FF) if False else (v & 0xFFF))
        print('== %s  PNCN %04X 맵 0x%05X  칸 %d개  번호 %s~%s' % (st, pncn, base, len(cells),
              hex(min(cells)) if cells else '-', hex(max(cells)) if cells else '-'))
        # 맵 줄을 파일에서 찾기 (원본 그대로 / 바이트 뒤집힘)
        hit = 0
        for y, row in rows:
            nz = [i for i, v in enumerate(row[:44]) if v]
            a, b = nz[0], nz[-1] + 1
            if b - a < 4:
                continue
            pat = struct.pack('>%dH' % (b - a), *row[a:b])
            for k, d in files.items():
                i = d.find(pat)
                if i >= 0:
                    print('   줄 %2d 칸 %2d..%2d → %s 0x%X (평문)' % (y, a, b, k, i)); hit += 1; break
        if not hit:
            print('   맵 줄 평문 없음 — 압축되었거나 코드가 그림')


if __name__ == '__main__':
    main()
