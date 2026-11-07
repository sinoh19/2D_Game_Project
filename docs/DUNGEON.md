# 횡스크롤 던전
기준 시야 640×360, 월드 2560×360(가로 4화면). 전체 화면은 네이티브 타깃에서 완성한 뒤 정수 2배로 표시합니다.
방향키 이동, SPACE 점프, C 공격, ESC 저장 후 메인.
배치와 충돌은 assets/dungeon/dungeon_01.json, 애니메이션은 character.json에서 수정합니다.
사용 중인 아트는 assets/dungeon/native640에 있으며, 유니티에서 최종 적용된 문·조명·기사 갑옷과 Tile 에셋을 기준으로 픽셀 규격을 정리했습니다.
자세한 크기는 ART_STANDARD.md, 변환 기록은 assets/native640-manifest.json을 참고하세요.
적·투사체와 턴제 전투는 후속 구현 단계입니다.