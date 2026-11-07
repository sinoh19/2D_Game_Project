# 유니티 최종 적용 에셋만 사용

- 배치 소품: CandleStand_Animated(몸체+6프레임 불꽃), GrandDoor_Cutout, KnightStatue_Cutout.
- 다른 초안 창문·현수막·가구·상자·뼈·횃불은 배치와 로딩 목록에서 제외. 이전 파일은 백업 용도로 보관.
- 지형: Unity Terrain1x1 Tile.asset의 m_Sprite GUID를 따라 최종 StraightMatchedToSteps PNG 및 Steps master를 복사.
- 배경: OriginalBackground1x1 Tile → WallTileSprite.asset → Continuous-Stone-Wall.png의 원본 Sprite 영역 사용.
- Sprite 영역·피벗·타일 반전 행렬 및 불꽃 타이밍 보존. 이미지 재생성·재색칠 없음.
- 상세 출처: assets/dungeon/approved-import.json 및 sources.json.
