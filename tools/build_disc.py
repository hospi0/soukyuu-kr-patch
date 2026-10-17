# -*- coding: utf-8 -*-
r"""창궁홍련대 시험 빌드 — work/out/ 의 바뀐 파일을 트랙 01(MODE1/2352)에 넣는다 (2026-10-17)
  파일 기록·EDC/ECC = 블루 시드 tools/iso.py patch()(제자리, 넘치면 끝으로 — 이 프로젝트 출력은 모두 원래 크기).
  원본: C:\claude\roms\ss\Soukyuu Gurentai (Japan) (Rev A)\ → work/build/ (트랙 01 새로 + 오디오 트랙 복사 + cue)
  python tools/build_disc.py
"""
import glob
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\blueseed-kr-patch\tools')
import iso  # noqa: E402

SRC = r'C:\claude\roms\ss\Soukyuu Gurentai (Japan) (Rev A)'
NAME = 'Soukyuu Gurentai (Japan) (Rev A)'
OUT = os.path.join(ROOT, 'work', 'out'); DISC = os.path.join(ROOT, 'work', 'disc')
BUILD = os.path.join(ROOT, 'work', 'build')


def main():
    files = {}
    for p in sorted(glob.glob(os.path.join(OUT, '**', '*'), recursive=True)):
        if not os.path.isfile(p):
            continue
        rel = os.path.relpath(p, OUT).replace(os.sep, '/')
        new = open(p, 'rb').read(); old = open(os.path.join(DISC, rel), 'rb').read()
        if new == old:
            continue
        assert len(new) == len(old), (rel, len(new), len(old))   # 이 프로젝트는 모두 제자리(크기 같음)
        files['/' + rel.upper()] = new
    print('넣을 파일', len(files))
    os.makedirs(BUILD, exist_ok=True)
    t1 = os.path.join(BUILD, NAME + ' (Track 01).bin')
    moved = iso.patch(os.path.join(SRC, NAME + ' (Track 01).bin'), t1, files)
    assert not moved, moved
    for f in sorted(glob.glob(os.path.join(SRC, '*'))):
        b = os.path.basename(f)
        if '(Track 01)' in b:
            continue
        d = os.path.join(BUILD, b)
        if not os.path.exists(d) or os.path.getsize(d) != os.path.getsize(f):
            shutil.copyfile(f, d)
    # 검산: 이미지에서 다시 읽은 파일 = 출력 파일
    with open(t1, 'rb') as fh:
        E = {nm: (l, s) for nm, l, s, _, _ in iso.entries(fh)}
        for nm, data in files.items():
            l, s = E[nm]
            assert iso.read_user(fh, l, (s + 2047) // 2048)[:s] == data, nm
    print('검산 통과 · 트랙 01 md5', hashlib.md5(open(t1, 'rb').read()).hexdigest())
    print('빌드:', BUILD)


if __name__ == '__main__':
    main()
