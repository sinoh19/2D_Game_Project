# 튜토리얼 슬라임 — 대기 이미지

- 캔버스32×32, 몸체 약28×20, 2×2 픽셀 단위, 6색, 투명 PNG.
- 왼쪽을 보는 초록 슬라임. 그림 좌상단 기준 발 위치(16,30).
- 대기 이미지와 이동용 제자리 점프 루프가 있으며, 몬스터 행동·충돌·맵 배치는 아직 연결하지 않았습니다.
- 내장 이미지 생성 도구로 원본을 제작한 뒤 광택 가장자리를 제거하고 게임 규격과 고정 팔레트로 정리했습니다.

## Generation prompt

Create ONE production-ready small SLIME MONSTER sprite for a640x360 native resolution medieval dungeon SIDE-SCROLLING2D pixel game. Input images are STYLE/PIXEL DENSITY references only; do not depict a chair or knight. Single idle green slime, simple low flattened dome of jelly, broad rounded base resting FLAT on ground, slight asymmetric squash, facing subtly LEFT toward player, two very simple dark eyes with a watchful neutral expression. Approachable tutorial enemy, not mascot/cartoon illustration. Intended NATIVE SPRITE CANVAS32x32logicalpixels, visible body approximately28wide x20high, bottom contact atrow29, margin2px sides. STRICTLY coarse pixel art: build at16x16 logical working grid then enlarge exactly2x nearest-neighbor to32x32, every pixel cluster is2x2; no isolated1px sparkles or thin outlines. LIMITED SIX FLAT COLORS TOTAL: dark muted forest-green outline, dark green shade, moss-green main body, olive-green secondary lit area, small pale sage highlight, near-black eyes. Restrained dark muted colors matching dungeon scene and attached sprites. Jelly volume from ONE broad blocky shaded underside and ONE SMALL2x4pixel light patch atupperleft; NOT a glossy multihighlight rendered slime. Stepped crisp square silhouette, low detail, no gradient/antialias/blur/dithering/noise. No limbs, weapons, crown, accessories, teeth, text, ground, cast shadow, environment or UI. Fully TRANSPARENT background outside silhouette; one centered isolated sprite only.

## 이동 애니메이션

- `move.png`: 32×32 프레임8개를 가로로 이은256×32 투명 시트.
- `move.json`: 8fps·1초 루프, 프레임 사각형과 발 위치.
- `move.gif`: 원본32px 투명 GIF. `move-preview.gif`: 확인용8배 확대 GIF.
- `move_frames/`: 개별 투명 PNG. 원본6색·2×2픽셀 단위를 유지합니다.
- 제자리 눌림 → 도약 → 작은 점프 → 착지 → 회복입니다. 실제 좌우 이동은 게임이 별도로 처리합니다.
- PixelLab animate_image의 움직임 초안을 검토한 뒤, 분리된 바닥 그림자와 모양 변화를 없애기 위해 승인된 idle 이미지 기반의 발 고정 키포즈로 다듬었습니다. 첫·끝 자세는 원본 idle과 같습니다.
- 애니메이션 생성 요청: squash low and wide, stretch on takeoff, small airborne hop, fall and soft landing, recover to the exact first pose; horizontal center fixed, baseline30, no particles/background.
