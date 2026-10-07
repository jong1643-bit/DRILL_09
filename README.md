# pico2d 애니메이션 뷰어

[PRD.md](PRD.md)에 따라 구현한 단일 파일 애니메이션 뷰어입니다.

## 실행

검증 환경은 Windows, Python 3.11.9, pico2d 1.5.1입니다.

```powershell
cd C:\DRILL_09
py character_runs_esc.py
```

다른 작업 폴더에서도 `py C:\DRILL_09\character_runs_esc.py`로 실행할 수 있습니다. 이미지는 소스 파일의 폴더에서 찾습니다. 다른 환경에서 pico2d가 없다면 `py -m pip install pico2d==1.5.1`로 검증한 버전을 설치합니다.

- 방향키: 상하좌우 이동. 두 축을 함께 누르면 대각선 이동.
- 좌우 이동: 바라보는 방향 변경. 상하 이동: 마지막 좌우 방향 유지.
- 이동 중: 달리기 애니메이션. 정지 또는 경계에 막힘: 대기 애니메이션.
- 마우스: 손 모양 커서 표시.
- ESC 또는 창 닫기: 종료.

이동 속도는 200px/s, 애니메이션은 10fps입니다. 전체 100×100 프레임이 화면 안에 머무릅니다. `character.png`는 PRD의 외형 참고 자산이며 실제 출력에는 `animation_sheet.png`를 사용합니다.

## 검증

```powershell
py -m unittest discover -s tests -v
py tests/verify_sdl.py
```

첫 명령은 23개 자동 회귀 테스트를 실행합니다. 두 번째는 실제 pico2d 창을 잠시 열어 32개 프레임, SDL 입력·창 상태·커서·종료, 전체 실행 루프 및 다른 폴더에서의 실행을 검증합니다. 출력 PNG는 Git에서 제외된 `.venv/previews/`에 저장합니다. 테스트 파일은 개발 검증용이며 실행 프로그램은 `character_runs_esc.py` 한 파일입니다.

단계별 개발과 검증 결과는 [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)에 기록했습니다.
