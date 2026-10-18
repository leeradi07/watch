# 투표 참여 플라이어 (A4)

Toss DESIGN.md([rohitg00/awesome-claude-design · toss.md](https://github.com/rohitg00/awesome-claude-design/blob/main/design-md/playful/toss.md))를 기반으로 한 비당파 투표 독려 전단입니다.

- `index.html` — 원본 아트보드 (A4, 794×1123px @96dpi). 브라우저에서 열면 도장이 "쾅" 찍히는 모션이 재생됩니다.
- `flyer.png` — 3배 해상도(2382×3369, 약 288dpi) 이미지
- `flyer.pdf` — A4 인쇄용 PDF
- `render.mjs` — PNG/PDF 재생성 스크립트 (`node election-flyer/render.mjs`, Playwright 필요)
- `fonts/` — Pretendard Variable (SIL OFL 1.1, `OFL.txt`)

## DESIGN.md에서 그대로 가져온 것

- 컬러: Toss Blue `#3182f6` 단일 브랜드 컬러, `#e8f3ff` 틴트 보조 버튼, 그레이 스케일 텍스트 토큰
- 타이포: Pretendard, 굵기 2단계(800/500), 큰 숫자 + 작은 단위(`4.12 수요일`), 숫자는 tabular-nums
- 컴포넌트: 버튼 radius 7px, 카드 radius 16px, hairline 구분선 리스트, 그라데이션 없는 flat fill

## 역동성을 위해 의도적으로 확장한 것

"플랫 벡터 일러스트" 규칙이 너무 정적이라, **컬러 규칙(단일 블루, 플랫 면)은 지키고 형태·구도로 에너지를 만들었습니다.**

- **사선으로 잘린 히어로 면** — 수평 그리드를 깨는 기울어진 경계
- **기표 도장(○+卜)** — 화면을 압도하는 크기로 기울여 배치, 러버 스탬프 잉크 질감(SVG turbulence)
- **경계를 뚫고 나오는 도장** — 파란 면에선 흰색, 흰 면으로 넘어가면 Toss Blue로 반전
- **임팩트 버스트 & 충격파 링** — 도장 중심에서 퍼지는 블루 계열 단색 쐐기
- **날아가는 투표용지 + 스피드 라인** — 충격으로 튕겨 나가는 방향성
- **잘린 거대 아웃라인 숫자 `4.12`** — 배경 레이어의 깊이감
- **모션** — 도장 slam → 버스트 → 용지 비산 순서의 진입 애니메이션 (`prefers-reduced-motion` 존중, `?static`으로 비활성화)

## 문구·일정 수정

일정은 제23대 국회의원선거(2028.4.12 수, 사전투표 4.7–4.8) 기준입니다. 배포 전 중앙선거관리위원회 공고로 확인하고, `index.html`의 `.chip`, `.cards`, `.rows` 텍스트를 수정한 뒤 `render.mjs`로 다시 내보내세요.
