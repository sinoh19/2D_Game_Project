# Project workflow

- This is the Python + pico2d game project, not a Unity runtime project.
- Repository: https://github.com/sinoh19/2D_Game_Project . The working branch tracks the existing `origin/main`.
- The user has requested ongoing Git commits and GitHub updates. After completing a meaningful authorized change, run relevant checks, review the diff, commit the intended changes, and push to this repository. Do not force-push or overwrite remote history. If the remote advanced, integrate its changes before pushing.
- Preserve the existing planning presentations and video in the repository.
- Do not commit `.venv/`, `user_data/`, caches, temporary captures, secrets or API tokens.
- Render at 640x360 logical resolution and present at 1280x720 with nearest-neighbor scaling. Terrain grid is 32x32; individual assets do not all have to be 640x360.
- Keep the existing controls: arrows to move, Space to jump, C to attack, E to interact, Esc to save/return. The debug skip button starts a fresh closed-gate run; Continue restores saved progress.
- Relevant baseline check: `.venv/Scripts/python.exe main.py --self-check`. Use additional targeted checks for collision, gate state, or transitions when changing those systems.
- Preserve source art and existing animation timing when changing rendering. Keep runtime paths relative to the project.

- Editable map source is `maps/dungeon_01.tmj` plus external `.tsj` palettes. Keep the legacy dungeon JSON as the asset/animation library; edit map placement in Tiled source. New painted terrain uses automatic collision, migrated manual layers retain separate collision objects. Run `tests/test_tiled_map.py` when changing the loader or editor maps. Do not rerun `tools/migrate_legacy_map.py` over user-edited maps. `.tools/` and Tiled session state stay untracked.
