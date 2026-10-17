# -*- coding: utf-8 -*-
r"""창궁홍련대 배포 묶음 — dist/SoukyuuGurentai_KR_<VER>/ : 트랙 01 xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat (2026-10-17)
  검증: 원본 트랙 01 → xdelta 적용 → md5 = 빌드 결과(work/build) md5.
  python tools/make_dist.py   (먼저 python tools/build_disc.py)
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROMNAME = 'Soukyuu Gurentai (Japan) (Rev A)'
SRC = os.path.join(r'C:\claude\roms\ss', ROMNAME)
BUILD = os.path.join(ROOT, 'work', 'build')
NAME = 'SoukyuuGurentai_KR_' + VER
TITLE = '창궁홍련대 (세가 새턴 일본판 Rev A) 한글 패치 ' + VER
TRACKS = 52


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


HEAD = """{tracks}개의 트랙으로 이루어진 {rom} 의
트랙 1번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.
"""

BODY = """

[ 적용 방법 ]

  1) 원본 트랙 01 파일을 이 폴더에 복사
       "{bin}"
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 01 이름으로 바꿔 넣고, 나머지 트랙과 cue 는 그대로 쓰세요
     (트랙 01 크기는 원본과 같습니다)

  직접 적용:
    xdelta.exe -d -s "원본 트랙 01" "{patch}" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 출격 전 작전 설명·게임 중 문구·결과 화면·이어하기(6스테이지 전부), 날짜 글자
  - 연습 메뉴(버튼·작전 패널·기체/작전 상세 18장·조종사 카드·배너·작전 카드·기체 사양표)
  - 기체 선택 화면, 오프닝 데모 문구, 경고문, 저장 안내 7장
  - 설정 화면(난이도 이름 8개 포함)·최고 득점·순위표, 제목 메뉴, 음향 시험 곡명, 조작 설명
  - 제목 로고는 원본 그대로이고, 아래 읽기 줄만 "창궁홍련대" 로 바꿨습니다
  - 영어(PLAYER-1·HI-SCORE·조작 설정의 영문 항목 등)는 원본 그대로입니다


[ 알려진 점 ]

  - 아직 끝까지 실기로 확인하지 못했습니다. 글자가 잘리거나 잔상이 남는 곳이 있으면 알려 주세요.
  - 조작 설정 화면 머리 "操作設定" 은 아직 일본어입니다.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
if not exist "%~dp0{bin}" (
  echo   [오류] 원본 트랙 01 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
"%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
  pause & exit /b 1
)
echo   완료: "{kbin}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    b = ROMNAME + ' (Track 01).bin'
    src = os.path.join(SRC, b); out = os.path.join(BUILD, b)
    patch = NAME + '.xdelta'; pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, out, pp], check=True)
    chk = os.path.join(d, '_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
    o, want, got = md5(src), md5(out), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    kbin = ROMNAME + ' (Track 01) [KR].bin'
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    readme = (TITLE + '\n' + '=' * 60 + '\n\n' + HEAD.format(tracks=TRACKS, rom=ROMNAME, o=o, d=want)
              + BODY.format(bin=b, patch=patch))
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(
        BAT.format(bin=b, patch=patch, kbin=kbin).replace('\n', '\r\n').encode('cp949'))
    zp = shutil.make_archive(d, 'zip', os.path.dirname(d), NAME)
    print('원본md5 %s → 패치md5 %s · %s %d B' % (o, want, patch, os.path.getsize(pp)))
    print('zip', zp, os.path.getsize(zp), md5(zp))
    for f in sorted(os.listdir(d)):
        print('  %-50s %12d' % (f, os.path.getsize(os.path.join(d, f))))


if __name__ == '__main__':
    main()
