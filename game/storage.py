import json
import math
from pathlib import Path


class Storage:
    """프로젝트 내부 user_data에 설정과 개발용 필드 진행을 저장합니다."""
    def __init__(self, directory: Path):
        self.directory = directory

    def read(self, filename, default):
        try:
            data = json.loads((self.directory / filename).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else default
        except (OSError, ValueError):
            return default

    def write(self, filename, data):
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / filename
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def load_position(self):
        data = self.read("save.json", {})
        try:
            if data.get("version") not in (1, 2, 3, 4):
                return None
            x, y = float(data["x"]), float(data["y"])
            if not (math.isfinite(x) and math.isfinite(y)):
                return None
            if data.get("version") == 1:
                return (88.0, 288.0)
            if data.get("version") == 2:
                return x, y+136.0
            if data.get("version") == 3:
                return x/1.5, y/1.5+136.0
            return x, y
        except (KeyError, TypeError, ValueError):
            return None

    def save_position(self, x, y):
        self.write("save.json", {"version": 4, "scene": "dungeon_01", "x": x, "y": y})

    def animation_enabled(self):
        return self.read("settings.json", {}).get("animation", True) is not False

    def resolution(self):
        from game.config import RESOLUTIONS, WINDOW_WIDTH, WINDOW_HEIGHT
        value = self.read('settings.json', {}).get('resolution')
        return next((size for size in RESOLUTIONS if list(size) == value),
                    (WINDOW_WIDTH, WINDOW_HEIGHT))

    def save_settings(self, animation, resolution=None):
        data = self.read('settings.json', {})
        data['animation'] = bool(animation)
        if resolution is not None:
            data['resolution'] = list(resolution)
        self.write('settings.json', data)
