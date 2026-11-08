# 튜토리얼 슬라임 — 대기 이미지

- 캔버스32×32, 몸체 약28×20, 2×2 픽셀 단위, 6색, 투명 PNG.
- 왼쪽을 보는 초록 슬라임. 그림 좌상단 기준 발 위치(16,30).
- 현재는 대기 이미지 한 장이며 몬스터 행동·충돌·맵 배치는 아직 연결하지 않았습니다.
- 내장 이미지 생성 도구로 원본을 제작한 뒤 광택 가장자리를 제거하고 게임 규격과 고정 팔레트로 정리했습니다.

## Generation prompt

Create ONE production-ready small SLIME MONSTER sprite for a640x360 native resolution medieval dungeon SIDE-SCROLLING2D pixel game. Input images are STYLE/PIXEL DENSITY references only; do not depict a chair or knight. Single idle green slime, simple low flattened dome of jelly, broad rounded base resting FLAT on ground, slight asymmetric squash, facing subtly LEFT toward player, two very simple dark eyes with a watchful neutral expression. Approachable tutorial enemy, not mascot/cartoon illustration. Intended NATIVE SPRITE CANVAS32x32logicalpixels, visible body approximately28wide x20high, bottom contact atrow29, margin2px sides. STRICTLY coarse pixel art: build at16x16 logical working grid then enlarge exactly2x nearest-neighbor to32x32, every pixel cluster is2x2; no isolated1px sparkles or thin outlines. LIMITED SIX FLAT COLORS TOTAL: dark muted forest-green outline, dark green shade, moss-green main body, olive-green secondary lit area, small pale sage highlight, near-black eyes. Restrained dark muted colors matching dungeon scene and attached sprites. Jelly volume from ONE broad blocky shaded underside and ONE SMALL2x4pixel light patch atupperleft; NOT a glossy multihighlight rendered slime. Stepped crisp square silhouette, low detail, no gradient/antialias/blur/dithering/noise. No limbs, weapons, crown, accessories, teeth, text, ground, cast shadow, environment or UI. Fully TRANSPARENT background outside silhouette; one centered isolated sprite only.