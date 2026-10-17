# -*- coding: utf-8 -*-
r"""스테이지별로 «타일 자리에 들어가는» 렌더 설정 찾기 (2026-10-17) — 선호 순서대로 시험해 첫 성공을 work/stg/fit.json 에 기록
  순서: 테두리 있음 → 없음, 장평 1.0 → 0.80, 큰 이름 1.0 → 0.9 · 격자 맞춤 가로세로(SNAP=2)
  python tools/stg_fit.py [X…]
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORDER = [(e, x, b) for e in tuple(int(v) for v in os.environ.get("FIT_EDGES", "1,0").split(",")) for x in (1.0, 0.95, 0.9, 0.85, 0.8) for b in (1.0, 0.9)]
fp = os.path.join(ROOT, 'work', 'stg', 'fit.json')
fit = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
for X in (sys.argv[1:] or list('BOCASL')):
    for e, x, b in ORDER:
        env = dict(os.environ, SNAP='2', EDGE=str(e), X_SCALE=str(x), BIG_SCALE=str(b), PYTHONIOENCODING='utf-8')
        subprocess.run([sys.executable, os.path.join(HERE, 'stg_kr.py'), X], env=env, capture_output=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'stg_build.py'), X], env=env, capture_output=True, text=True, encoding='utf-8')
        ok = not r.stdout.startswith('✗')
        print(X, 'EDGE', e, 'X', x, 'BIG', b, '성공' if ok else r.stdout.strip()[:90], flush=True)
        if ok:
            fit[X] = dict(EDGE=e, X_SCALE=x, BIG_SCALE=b, SNAP=2, 결과=r.stdout.strip()); break
    else:
        fit[X] = dict(실패=True)
    json.dump(fit, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
