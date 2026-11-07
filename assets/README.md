# 에셋 레이어

## 배경 애니메이션

- `title/background_sheet.png`: **UI가 없는** 오두막·숲 배경. 320×180 프레임 24개, 6열×4행.
- `title/background_still.png`: UI가 없는 첫 프레임.
- `title/animation.json`: 8fps / 3초 반복 설정.

기존 오두막·연기·왼쪽 숲 프레임은 유지하고, UI가 가렸던 오른쪽 숲을 복원했습니다.
오른쪽 잎에는 작은 반복 움직임을 주고 목재 기둥과 수풀은 고정합니다.

## UI 버튼 — 배경과 별도

- `ui/start.png`: 게임 시작
- `ui/continue.png`: 이어하기
- `ui/settings.png`: 설정
- `ui/exit.png`: 게임 종료

각 버튼은 투명 배경의 79×27 PNG입니다. 기존 버튼의 글씨·테두리를 그대로 추출했으며, 바깥에 2픽셀 여백이 있습니다.
`game/resources.py`의 `draw_title()`이 배경을 그리고, `draw_menu()`가 이 PNG들을 위에 그립니다.
`game/config.py`의 `MENU_BUTTONS`를 변경하면 클릭 영역과 표시 위치가 함께 이동합니다.
UI 이미지를 수정해도 배경 스프라이트시트를 다시 만들 필요가 없습니다.

`title/archive_before_ui_split/`의 파일은 분리 이전의 합성본 백업이며 실행 중에는 사용하지 않습니다.
