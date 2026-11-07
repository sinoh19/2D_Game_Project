"""용병 일기: Python + pico2d 진입점."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="용병 일기 — pico2d")
    parser.add_argument("--self-check", action="store_true", help="숨겨진 창에서 실행 점검")
    parser.add_argument("--capture", type=Path, help="점검 화면을 BMP로 저장")
    parser.add_argument("--map", type=Path, help="실행할 Tiled .tmj 맵")
    args = parser.parse_args()
    from game.app import App
    if args.self_check:
        from game.self_check import run
        run(args.capture, args.map)
    else:
        App(map_path=args.map).run()


if __name__ == "__main__":
    main()
