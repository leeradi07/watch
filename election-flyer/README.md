# 선거 플라이어 (A4)

Toss DESIGN.md([rohitg00/awesome-claude-design · toss.md](https://github.com/rohitg00/awesome-claude-design/blob/main/design-md/playful/toss.md)) 기반 플라이어 2종입니다.

| 파일 | 내용 |
| --- | --- |
| `index.html` → `flyer.png` / `flyer.pdf` | **부산교총 회장선거 · 배동윤 후보 4대 약속** |
| `turnout.html` → `turnout.png` / `turnout.pdf` | 비당파 투표 참여 안내 (제23대 국회의원선거) |

- PNG는 3배 해상도(2382×3369, 약 288dpi), PDF는 A4 인쇄용입니다.
- HTML을 브라우저로 열면 진입 모션이 재생됩니다 (`?static`으로 끄기, `prefers-reduced-motion` 존중).
- `render.mjs` — PNG/PDF 재생성 (`node election-flyer/render.mjs`, Playwright 필요)
- `assets/candidate.webp` — 후보 사진 누끼 (로컬 rembg `birefnet-portrait` 모델로 배경 제거)
- `fonts/` — Pretendard Variable (SIL OFL 1.1, `OFL.txt`)

## DESIGN.md에서 그대로 가져온 것

- 컬러: Toss Blue `#3182f6` 단일 브랜드 컬러, `#e8f3ff` 틴트, 그레이 스케일 텍스트 토큰
- 타이포: Pretendard, 굵기 2단계(800/500), 큰 숫자 + 작은 단위, tabular-nums
- 컴포넌트: 버튼 radius 7px, 카드 radius 16px, 아이콘 타일 radius 12px, 그라데이션 없는 flat fill

## 역동성을 위해 의도적으로 확장한 것

"플랫 벡터 일러스트" 규칙이 너무 정적이라, **컬러 규칙(단일 블루, 플랫 면)은 지키고 형태·구도로 에너지를 만들었습니다.**

- **사선으로 잘린 히어로 면** + 경계 컷 라인 — 수평 그리드를 깨는 기울기
- **후보 인물 + 오프셋 실루엣** — 딥블루 단색 그림자로 화면에서 튀어나오는 입체감
- **임팩트 버스트 & 충격파 링** — 후보 머리 뒤에서 퍼지는 블루 계열 단색 쐐기
- **날아가는 공약 아이콘 타일** — 열쇠·사이렌·편지·청진기(4대 약속)가 스피드 라인과 함께 튕겨 나감
- **기표 도장(○+卜)** — 러버 스탬프 잉크 질감, 경계를 넘어가면 흰색→Toss Blue로 반전

## 수정 방법

문구는 `index.html`의 `.hero-copy`(이름·슬로건)와 `.pledge` 카드에 있습니다. 기호·선거일·연락처 등이 정해지면 `.chip`이나 `.foot`에 추가한 뒤 `render.mjs`로 다시 내보내세요.
