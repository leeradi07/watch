# 선거 플라이어 (A4)

Toss DESIGN.md([rohitg00/awesome-claude-design · toss.md](https://github.com/rohitg00/awesome-claude-design/blob/main/design-md/playful/toss.md)) 기반 플라이어입니다.

| 시안 | 소스 | 출력 |
| --- | --- | --- |
| **A. 회장 단독** — 배동윤 후보 + 4대 약속 | `index.html` | `flyer.png` / `flyer.pdf` |
| **B. 회장단 6인** — 회장 + 부회장 후보 5인 + 4대 약속 | `team.html` | `team.png` / `team.pdf` |
| (참고) 비당파 투표 참여 안내 | `turnout.html` | `turnout.png` / `turnout.pdf` |

- PNG는 3배 해상도(2382×3369, 약 288dpi), PDF는 A4 인쇄용입니다.
- HTML을 브라우저로 열면 진입 모션이 재생됩니다 (`?static`으로 끄기, `prefers-reduced-motion` 존중).
- `shared/flyer.css` · `shared/flyer.js` — A·B 공통 토큰, 공약 카드, 모션, 초등학교 일러스트, 아이콘
- `render.mjs` — 모든 시안 PNG/PDF 재생성 (`node election-flyer/render.mjs`, Playwright 필요)
- `assets/candidate.webp` — 회장 후보 사진 누끼 (로컬 rembg `birefnet-portrait`로 배경 제거)
- `fonts/` — Pretendard Variable (SIL OFL 1.1, `OFL.txt`)

## 초등학교 배경

`shared/flyer.js`의 `#school`에 벡터로 그린 장면입니다: 시계탑 중앙 현관이 있는 4층 교사동, 창문 그리드(일부 불 켜진 창), 국기게양대, 나무, 트랙과 축구 골대가 있는 운동장, 뒤편 산·도시 실루엣.
히어로의 사선 경계와 같은 각도로 `skewY(-8)` 기울여 원근감과 속도감을 줍니다. 모든 색은 Toss Blue 계열 단색입니다.

## 시안 B — 부회장 사진 넣기

`team.html`의 `.team` 안 카드 5장이 부회장 후보 자리입니다. 사진이 준비되면:

1. 배경 제거 또는 정사각 크롭한 사진을 `assets/vp1.webp` … `vp5.webp`로 저장
2. 각 카드의 `<div class="avatar ph">…</div>`를 `<div class="avatar"><img src="assets/vp1.webp" alt=""></div>`로 교체
3. `<p class="n ph">이름</p>`을 실제 이름으로 바꾸고 `ph` 클래스 제거
4. `node election-flyer/render.mjs`

## DESIGN.md에서 그대로 가져온 것

- 컬러: Toss Blue `#3182f6` 단일 브랜드 컬러, `#e8f3ff` 틴트, 그레이 스케일 텍스트 토큰
- 타이포: Pretendard, 굵기 2단계(800/500), tabular-nums
- 컴포넌트: 카드 radius 16px, 아이콘 타일 radius 12px, 모달급 소프트 섀도(`0 8px 24px`), 그라데이션 없는 flat fill

## 역동성을 위해 의도적으로 확장한 것

- **사선으로 잘린 히어로 면** + 경계 컷 라인
- **후보 인물 + 오프셋 실루엣** — 딥블루 단색 그림자로 튀어나오는 입체감
- **임팩트 버스트 & 충격파 링** — 후보 머리 뒤에서 퍼지는 단색 쐐기
- **날아가는 공약 아이콘 타일** — 열쇠·사이렌·편지·청진기(4대 약속)
- **기울어진 학교 장면** — 사선과 같은 각도로 원근감
- **(B) 계단식 부회장 카드** — 사선 경계를 따라 한 칸씩 올라가며 히어로와 정보 영역을 연결
