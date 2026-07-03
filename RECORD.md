# CultureZero 진행 기록

기획서: [CultureZero_기획서.md](CultureZero_기획서.md) · 작업 가이드라인: [CLAUDE.md](CLAUDE.md)

**라이브 URL**: https://yyj0609.github.io/culture/
**GitHub 레포**: https://github.com/yyj0609/culture

---

## 완료된 작업

### 1. 외교부 공공데이터 API 조사 (6개 중 5개 연동, 1개 제외)
공공데이터포털(data.go.kr) 서비스키로 실제 호출해서 응답 구조를 확인함.

| API | 상태 | 비고 |
|---|---|---|
| `TravelWarningServiceV3` (여행경보) | ✅ 연동 | HTTPS만 됨. `iso_code`(3자리)가 마스터 키 |
| `AccidentService` (사건사고 예방정보) | ✅ 연동 | ISO코드 없음 → 한글 국가명으로 조인(197/198, 마카오 제외) |
| `CountryFlagService2` (국기 이미지) | ✅ 연동 | `country_iso_alp2`(2자리) → pycountry로 3자리 변환 |
| `LocalContactService2` (현지연락처) | ✅ 연동 | 위와 동일 변환 |
| `CountryNoticeService` (공지사항) | ✅ 연동, 현재 0건 | 공지 없을 때 0404.go.kr 목록으로 폴백 |
| `CountrySafetyService3` (안전공지) | ❌ 제외 | "Unexpected errors" 응답, MVP 스코프 외 합의 |

**ISO 코드 매핑**: TravelWarningServiceV3(197개국)을 마스터로, pycountry로 ISO2↔ISO3 변환. 코소보(`XK`→`XKX`) 수동 매핑, EU 깃발 제외.
**국가 좌표**: `mledoze/countries`(공개 데이터셋)에서 197개국 위경도를 collect_data.py 정적 테이블로 내장.

### 2. 여행경보 단계 로직
- API 실데이터로 필드 매핑 확정: attention="여행유의", control="여행자제", limita="철수권고", ban_yna="여행금지"
- `_partial` 필드 누락 버그 수정 (일부지역만 경보인 나라가 "없음"으로 잘못 표시되던 문제)
- **national_level**: 전국 단위 단계(폴리곤 색 기준) / **alert_level**: 전체 최고 단계(배지·리스트 기준) 분리
- 5단계 색상: 없음(초록)/여행유의(남색)/여행자제(노랑)/철수권고(주황)/여행금지(빨강). 특별여행주의보는 MVP 제외 합의.
- 197개국 분포: 없음 51 / 여행유의 42 / 여행자제 32 / 철수권고 47 / 여행금지 25

### 3. 데이터 처리 결정사항
- **HTML 렌더링**: local_contact_html / accident_info_html을 구조화 파싱 대신 원본 HTML 렌더링 (긴급연락처 전화번호 파싱 오류 방지). `html.parser` 기반 새니타이저 적용 (style/class 제거, truncated HTML 안전 처리).
- **HTML truncation 버그**: 러시아·헝가리 연락처 HTML이 API에서 중간에 잘려서 왔음 → 새니타이저가 안전하게 처리.
- **국기 이미지 경로**: `public/images/{ISO3}.{ext}` 형식, 초기 `public/` 누락 버그 패치 완료.

### 4. culture_ai 필드 (Gemini `gemini-flash-lite-latest`)
- **etiquette**: 문화·예절 (3~4문장)
- **local_laws**: 현지 법률·경범죄·주의사항 (2~3문장) — 초기 `business_tip`에서 변경, 197개국 재생성 완료
- **phrases**: 유용한 현지어 표현 5개
- 캐싱: 기존 값 있으면 건너뜀. 브라우저 캐시 무효화: `?v=YYYYMMDD` 날짜 쿼리 파라미터.

### 5. 데이터 수집 스크립트 (`collect_data.py`)
- `.env`에서 `PUBLIC_DATA_SERVICE_KEY`, `GOOGLE_API_KEY` 로드 (키 하드코딩 없음)
- 5개 API 전체 1회 호출 후 ISO 기준 조인 (API 호출 최소화)
- 국기 이미지·world_borders.geojson·culture_ai 모두 캐싱 (이미 있으면 스킵)
- 세계 국경선 GeoJSON: Natural Earth 50m (196개국, `public/data/world_borders.geojson`)

### 6. 프론트엔드 (`index.html`, `style.css`, `main.js`)
GlobalRecruit과 톤 통일, 메인 컬러 `#1E8E6E`(초록). Vanilla JS + Leaflet, 프레임워크 없음.

- **화면 1(메인)**: 검색창(자동완성) + 전체/즐겨찾기 탭 + 인기국가 칩 + 지도/리스트 토글
  - 지도: 반투명 choropleth (national_level 기준 폴리곤 색) + 일부지역 경보 `!` 아이콘
  - 범례 클릭 → 지도 색칠 단계(전국 경보 단계 기준, `national_level || alert_level`)별 필터 및 국가 수 집계
  - 팝업: 클릭 시 미리보기(일부지역 경보 요약 + 문화 한줄 팁 lazy-load)
  - 즐겨찾기: localStorage, 탭 필터, 하트 버튼
- **화면 2(로딩)**: 단계별 체크리스트 연출
- **화면 3(결과)**: 국기+국가명+경보 배지+즐겨찾기 하트, 카드 6개 (외교부 데이터/AI 생성 배지 구분), 하단 공지사항 링크·공유·PDF 저장
- URL 딥링크(`?country=ISO3`) 지원
- 카드 구성: 🛡️ 사건사고 예방정보 / 🚦 여행경보 상세 / 📞 긴급 연락처 / 🤝 문화·예절 / ⚖️ 현지 법률 및 주의사항 / 💬 유용한 현지 표현

### 7. GitHub Pages 배포 완료
- **라이브**: https://yyj0609.github.io/culture/
- **GitHub Actions** (`.github/workflows/data_pipeline.yml`): 매일 KST 02:00 자동 실행, Secrets에서 두 키 주입
- GitHub Secrets: `PUBLIC_DATA_SERVICE_KEY`, `GOOGLE_API_KEY` 등록 완료
- `requirements.txt`: `requests`, `python-dotenv`, `pycountry`

### 8. 배포 후 버그 수정 (2차 세션)

#### 대만 국기 흰 네모
- **원인**: MOFA CountryFlagService2 API가 대만(TWN)에 대해 188 bytes 빈 GIF 반환 (정치적 이유)
- **수정**: `collect_data.py`에 500 bytes 미만 파일 검증 로직 추가 + `flagcdn.com` fallback
- **수정**: `TWN.json`, `countries.json`의 `flag_image` 직접 패치 → `https://flagcdn.com/w40/tw.png`

#### 코소보 초록 핀 제거
- **원인**: XKX가 Natural Earth GeoJSON에 미수록 → 폴백 원 마커로 표시, `national_level="없음"`이라 초록색
- **수정**: 폴백 마커 루프 완전 삭제. `!` 아이콘 루프에 `if (!coveredIso.has(c.iso_code)) return;` 추가

#### 미니팝업 "불러오는 중" 고착 (5번 시도 끝에 해결)
- **원인**: DOM querySelector로 팝업 내부 요소 직접 접근 시 Leaflet 렌더 타이밍에 따라 null 반환
- **수정**: `layer.on('popupopen', async () => {...})` + `layer.getPopup()?.setContent(popupHTML(c, buildPopupExtra(detail)))` — Leaflet API로 팝업 전체 교체 (DOM 탐색 불필요)
- **구조**: `popupHTML(c, extra)` → extra=undefined이면 "불러오는 중", extra=''이면 섹션 숨김, extra=문자열이면 표시
- **헬퍼**: `buildPopupExtra(detail)` → 일부지역 경보 요약 + 문화 한줄 팁 HTML 반환

#### 리스트 빠른 스크롤 끊김
- **수정**: 리스트 뷰 국기 이미지에 `loading="lazy"` 추가

#### 친구 PR 병합 (feat/legend-filter-by-map-color)
- 범례 필터 기준을 `alert_level` → `national_level || alert_level` (지도 색상 기준)으로 변경
- `getFilteredCountries()`, `renderLegend()` 카운트 모두 `national_level || alert_level` 기준으로 통일

### 9. 지도 개선 (3차 세션)

#### 지도 타일
- 초기 OSM → CartoDB light (OSM이 GitHub Pages에서 400 반환) → Wikimedia → OSM 복구
- **최종**: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (파란 바다, OSM 원본)
- OSM 400 에러는 일시적 현상이었음 (Referer 포함 curl 테스트 → 200 확인)

#### 지도 크기 및 초기 뷰
- `style.css`: `#map { height: 520px }` → **850px**
- `main.js`: `setView([20, 10], 2)` → `setView([10, 10], 2)` (북극·남극 모두 표시)
- 850px + center [10, 10] + zoom 2 기준 가시 범위: 북위 ~83° ↔ 남위 ~80° (전 대륙 표시)

#### 러시아·캐나다 미니팝업 잘림 수정
- **근본 원인**: Leaflet `popup.setContent()` 후 내장 `_adjustPan`이 pan 애니메이션 도중 호출되어 위치 계산 충돌
- **수정**: `POPUP_OPTIONS = { autoPan: false }` 로 내장 autoPan 비활성화
- **수정**: `panForPopup(popup)` 함수 직접 구현 — `popup._container.getBoundingClientRect()`로 실제 위치 읽어서 `panBy()` 호출
  - 버그 1: 처음엔 `popup.getElement()` 사용 → Leaflet DivOverlay에서 항상 null 반환 → `popup._container`로 수정
  - 버그 2: `setTimeout(10ms)`로 호출 → DOM 레이아웃 완료 전 실행 → `requestAnimationFrame`으로 교체
- `panForPopup`은 초기 팝업 열릴 때 1회, `setContent` 후 1회 총 2회 호출

#### 브라우저 캐시 문제 해결
- `index.html`에 `?v=20260702c` 캐시버스터 추가 (`style.css`, `main.js` 양쪽)
- `index.html` 자체는 항상 새로 받아오므로 JS/CSS도 강제 갱신됨

### 10. 여행경보 전국 기준 통일 및 HTML 엔티티 중복 이스케이프 버그 해결 (4차 세션)
- **개선**: 상세 정보 페이지의 여행경보 배지 및 리스트 뷰 카드의 여행경보 배지 표시 기준을 전체 지역 최고 경보(`alert_level` / `level`)에서 **전국 기준 경보**(`national_level`)로 변경하여 지도 렌더링 기준과 일치시켰습니다.
- **수정**: 태국처럼 특정 일부 지역에만 철수권고 등이 발령되고 전국 기준으로는 "없음"인 국가들이 메인 지도(초록색)와 리스트/상세 뷰 배지에서 다르게 표현되던 불일치 문제를 해결하였습니다.
- **안내**: 상세 페이지의 "여행경보 단계 상세" 카드에서 전국 기준과 일부 지역 최고 경보 단계가 다를 경우 노출되는 안내 문구(`nationalNote`)를 상황에 맞춰 알맞게 변경하여 보여주도록 개선하였습니다.
- **버그 해결 (HTML 엔티티)**: 태국(`THA.json` 내 `2&amp;middot;3단계`)처럼 API 응답 상에서 HTML 엔티티가 중복 이스케이프(`&amp;middot;`)되어 사용자 화면에 깨져 나오는 문제를 분석하고 해결하였습니다.
  - **백엔드**: [collect_data.py](file:///D:/public_data/culture/collect_data.py) 내 `area` 파싱 부분에 `html.unescape` 루프를 적용하여 데이터 수집 시점에 완벽히 복원되도록 보완했습니다.
  - **프론트엔드**: [main.js](file:///D:/public_data/culture/main.js)에 `decodeHTMLEntities` 함수를 구현하여 단일 및 중복 이스케이프된 HTML 엔티티(`&middot;`, `&eacute;`, `&bull;`, `&ccedil;` 등)를 브라우저 단에서도 완벽히 해석하도록 처리하였습니다.
- **캐시**: `index.html` 내 `main.js` 호출부의 캐시버스터를 `?v=20260703e`로 업데이트하였습니다.

---

## 참고 사항
- 로컬 데이터 재수집: `python3 collect_data.py`
- 로컬 서버: `python3 -m http.server 8765` → http://localhost:8765
- `.env`는 `.gitignore`에 포함되어 커밋되지 않음. GitHub Actions는 Secrets로 대체.
- 레포 이름 변경(culture → CultureZero) 원하면: GitHub → Settings → General → Repository name
- JS/CSS 수정 후 배포 시 `index.html`의 `?v=` 버전 문자열도 업데이트할 것
