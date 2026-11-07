from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
NATIVE_WIDTH, NATIVE_HEIGHT = 640, 360
SCALE = 2
WINDOW_WIDTH, WINDOW_HEIGHT = NATIVE_WIDTH * SCALE, NATIVE_HEIGHT * SCALE
TARGET_FPS = 60
TITLE = "용병 일기 | Python + pico2d"

# 640×360 기준 왼쪽 위 좌표 (left, top, right, bottom).
MENU_BUTTONS = (
    (478, 92, 627, 137),
    (478, 158, 627, 203),
    (478, 224, 627, 269),
    (478, 290, 627, 335),
)
MENU_LABELS = ("게임 시작", "이어하기", "설정", "게임 종료")

# 독립된 투명 UI 이미지. 그리기와 클릭 위치는 MENU_BUTTONS를 공유합니다.
MENU_IMAGE_FILES = ("start.png", "continue.png", "settings.png", "exit.png")

# 오프닝 카메라: 기준 화면 640x360 화면의 왼쪽 위 기준 창문 중심.
OPENING_WINDOW = (270.0, 280.0)
OPENING_DURATION = 4.2
OPENING_FADE_START = 3.2
OPENING_MAX_ZOOM = 12.0

# 검은 화면 대화. 대사는 JSON에서, 표시 속도는 여기서 수정합니다.
DIALOGUE_SCRIPT = ROOT / "data" / "opening_dialogue.json"
DIALOGUE_CHARACTERS_PER_SECOND = 22.0
OPENING_DIALOGUE_DELAY = 0.35

# 대화 본문 폰트 크기 (640×360 기준 픽셀, 표시 시 SCALE배).
DIALOGUE_FONT_SIZE = 18

# 대화 뒤 책 장면: 나타나는 시간 / 닫힌 상태 유지 시간.
BOOK_FADE_IN_SECONDS = 0.45
BOOK_CLOSED_HOLD_SECONDS = 0.75

# 펼친 책을 보여준 뒤, 타일이 검은 뒷면으로 회전했다가 필드를 드러냅니다.
# 펼침 애니메이션의 35% 지점부터 타일 전환을 겹칩니다.
BOOK_TRANSITION_PROGRESS = 0.35
TILE_FLIP_COLUMNS = 16
TILE_FLIP_ROWS = 9
TILE_FLIP_SECONDS = 0.65
TILE_FLIP_STAGGER_SECONDS = 0.55
TILE_FLIP_BLACK_SECONDS = 0.3

# 개발 중 메인/인트로 우측 상단에서 새 던전으로 바로 진입.
DEBUG_SKIP_ENABLED = True
DEBUG_SKIP_BOUNDS = (536, 8, 631, 29)

# Tiled에서 저장한 맵을 실행 시 직접 읽습니다.
DEFAULT_TILED_MAP = ROOT / "maps" / "dungeon_01.tmj"
