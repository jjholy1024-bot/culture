# CultureZero 진행 기록

기획서: [CultureZero_기획서.md](CultureZero_기획서.md) · 작업 가이드라인: [CLAUDE.md](CLAUDE.md)

---

## 완료된 작업

### 1. 외교부 공공데이터 API 조사 (6개 중 5개 연동, 1개 제외)
공공데이터포털(data.go.kr) 서비스키로 실제 호출해서 응답 구조를 확인함. 기획서엔 응답 필드가 미확정 상태였는데, 직접 호출해서 다음을 확정함.

| API | 상태 | 비고 |
|---|---|---|
| `TravelWarningServiceV3` (여행경보) | ✅ 연동 | HTTPS만 됨. `iso_code`(3자리)가 마스터 키 |
| `AccidentService` (사건사고 예방정보) | ✅ 연동 | ISO코드 없음 → 한글 국가명으로 조인(197/198 매칭, 마카오 1건 제외) |
| `CountryFlagService2` (국기 이미지) | ✅ 연동 | `country_iso_alp2`(2자리) 사용 → pycountry로 3자리 변환 |
| `LocalContactService2` (현지연락처) | ✅ 연동 | 2자리 코드, 위와 동일 변환 |
| `CountryNoticeService` (공지사항) | ✅ 연동되나 현재 0건 | 실시간 등록된 공지가 없는 상태. `notice_url`은 0404.go.kr 목록 페이지로 폴백 |
| `CountrySafetyService3` (안전공지) | ❌ 제외 | 호출 시도했으나 "Unexpected errors" 응답, 사용자 확인 후 MVP 스코프에서 제외 합의 |

**ISO 코드 매핑**: `TravelWarningServiceV3`의 197개국을 마스터 리스트로 삼고, `pycountry`로 2자리↔3자리 변환. 유일한 예외는 코소보(`XK`→`XKX`, ISO 3166-1 공식 코드 아님, 수동 매핑). `CountryFlagService2`의 `EU`(유럽연합 깃발)는 국가가 아니라서 제외.

**국가 좌표**: 5개 API 어디에도 위경도가 없어서 `mledoze/countries`(GitHub 공개 데이터셋)에서 197개국 좌표를 가져와 `collect_data.py` 안에 정적 테이블로 박아둠.

### 2. 여행경보 단계 로직 (실데이터 기반으로 검증·수정)
- API 필드의 실제 값을 직접 찍어봐서 확정: `attention`="여행유의", `control`="여행자제", `limita`="철수권고"(기획서의 "출국권고"와 동일 개념), `ban_yna`="여행금지"
- **버그 발견·수정**: 처음엔 `attention`/`control`/`limita`/`ban_yna` 풀필드만 봤는데, 알제리 등 "일부 지역만 해당 단계"인 나라는 `_partial` 필드(`attention_partial` 등)에만 값이 들어있어서 전부 "없음"으로 잘못 표시되는 버그가 있었음. 풀필드와 partial 필드를 모두 체크하도록 수정 후 재검증 완료.
- 한 국가에 여러 지역별 단계가 동시에 존재할 수 있어서, `travel_alert.regions` 배열에 지역별로 전부 저장하고, 지도 핀/상단 배지는 그 중 **가장 높은 단계**를 대표값(`alert_level`)으로 사용 (사용자 확정 사항).
- 기획서 색상표엔 "여행자제/출국권고/여행금지" 3단계만 있었는데, 실제 공식 체계엔 1단계 "여행유의"(남색)가 별도로 있어서 5단계 색상표로 확장(사용자 확정): 없음(초록) / 여행유의(남색) / 여행자제(노랑) / 철수권고(주황) / 여행금지(빨강). 특별여행주의보(보라)는 별도 API 필요해서 MVP에서 제외(사용자 확정).
- 현재 197개국 분포: 없음 51 / 여행유의 42 / 여행자제 32 / 철수권고 47 / 여행금지 25

### 3. local_contacts / accident_info 처리 방식 (기획서와 다르게 결정)
기획서 예시는 `{"office": "...", "phone": "..."}` 같은 깔끔한 구조였지만, 실제 API 응답은 국가마다 제각각인 자유 형식 HTML 텍스트(대사관/영사관/문화원 섹션이 나라마다 다름)였음. 긴급연락처 전화번호를 정규식/AI로 잘못 파싱하면 안전사고로 직결될 수 있어서, **원본 HTML을 그대로 저장하고 프론트에서 그대로 렌더링**하는 방식으로 결정(사용자 확정). JSON 필드명: `accident_info_html`, `local_contact_html`.

### 4. culture_ai 생성: Claude API → Gemini API로 전환
처음엔 Claude API(Anthropic)로 진행했으나 크레딧 부족(`credit balance is too low`)으로 막혀서, 사용자 요청으로 **Gemini API**(`gemini-flash-lite-latest`, GlobalRecruit과 동일 모델)로 전환함. REST 직접 호출 방식(SDK 미설치, `requests`만 사용), GlobalRecruit의 `collect_data.py` 패턴과 동일.

### 5. 데이터 수집 스크립트 (`collect_data.py`)
- `.env`에서 `PUBLIC_DATA_SERVICE_KEY`, `GOOGLE_API_KEY` 로드
- 5개 API를 국가별 반복 호출이 아니라 **전체 1회 호출**(`numOfRows` 크게) 후 파이썬에서 ISO 기준으로 조인 → API 호출 횟수 최소화
- 국기 이미지는 `public/images/{ISO3}.{확장자}`로 다운로드, 이미 존재하면 스킵(캐싱)
- `culture_ai`는 기존 JSON 파일에 이미 값이 있으면 재생성 안 함(캐싱, GlobalRecruit과 동일 패턴)
- 출력: `public/data/countries.json`(메인 화면용 경량 목록), `public/data/countries/{ISO3}.json`(상세 브리핑용)
- 실행 검증 완료: 197개국 전부 정상 생성, 이미지 197/197 다운로드 성공

**현재 상태**: culture_ai Gemini 생성 진행 중(백그라운드). 마지막 확인 시 197개국 중 114개국 완료. 스크립트는 캐싱되므로 중단되어도 다시 돌리면 이어서 처리됨.

### 6. 프론트엔드 (`index.html`, `style.css`, `main.js`)
GlobalRecruit(`public_data/`)과 톤 통일, 메인 컬러만 `#1E8E6E`(초록)로 차별화. Vanilla JS, Leaflet 지도, 프레임워크 없음.

- **화면 1(메인)**: 검색창(자동완성 드롭다운) + 인기국가 칩(10개국 하드코딩: JPN/USA/FRA/GBR/THA/VNM/CHN/AUS/DEU/ITA, 추후 조정 가능) + 지도/리스트 토글. 지도 핀은 `alert_level` 색상으로 표시, 범례 포함.
- **화면 2(로딩)**: 단계별 체크리스트 연출(여행경보→사건사고→연락처→문화 순으로 표시, 실제 fetch는 한 번에 끝나지만 UX상 단계 표시)
- **화면 3(결과)**: 국기+국가명+여행경보 배지, 카드 6개(2단 그리드, 외교부 데이터/AI 생성 배지로 출처 구분), 하단 공지사항 링크·공유(클립보드 복사)·PDF 저장(`window.print()`)
- URL 쿼리스트링(`?country=ISO`)으로 딥링크 지원, 공유 버튼이 이 URL을 복사함

**프론트 검증 상태**: HTTP 레벨 체크 완료(모든 HTML/CSS/JS/JSON/이미지 200 응답, `main.js` 문법 오류 없음(JavaScriptCore로 확인), `index.html`의 모든 id가 `main.js`에서 정확히 참조됨). **단, 실제 브라우저 화면을 스크린샷으로 직접 확인은 못 함** — 이 환경에 스크린캡처 권한이 없고, Safari "Allow JavaScript from Apple Events" 설정도 키 입력 자동화 차단으로 못 켰음. `localhost:8765`로 로컬 서버를 띄워 Safari에 열어뒀으니 사용자가 직접 한 번 확인 필요.

---

## 다음 작업

1. **culture_ai 생성 완료 확인** — 백그라운드 작업이 끝났는지 확인하고, 누락된 국가 있으면 `python3 collect_data.py` 재실행(캐싱되므로 완료된 국가는 건너뜀)
2. **브라우저 직접 확인** — 사용자가 `localhost:8765`에서 지도 핀/검색자동완성/결과화면 정상 동작 확인
3. **지도 기능 보강** — 현재는 기본 Leaflet 핀 표시만 되어 있음. 추가 작업 필요(클러스터링, 줌 레벨별 핀 크기, 클릭 시 미리보기 팝업 등 구체 요구사항은 미정 — 작업 시작 전 확인 필요)
4. **즐겨찾기 기능 추가** — 현재 미구현. GlobalRecruit의 `localStorage` 기반 즐겨찾기 패턴(`gri_favorites` 키, 하트 아이콘 토글) 참고 가능. 국가 카드/칩에 즐겨찾기 버튼 추가 + 즐겨찾기만 모아보는 탭/필터 필요(구체 UX는 미정 — 작업 시작 전 확인 필요)
5. **GitHub Pages 배포 설정** — 아직 미착수. GlobalRecruit은 GitHub Actions로 데이터 파이프라인 자동화(`*.github/workflows/data_pipeline.yml`, 매일 새벽 2시) + GitHub Pages 정적 배포 구조였음. CultureZero도 동일 패턴 적용 예정이나, 이 폴더는 아직 git 저장소가 아님(`git init` 필요)

## 참고 사항
- `.env`에 `PUBLIC_DATA_SERVICE_KEY`, `GOOGLE_API_KEY` 들어있음(`.gitignore`에 포함되어 커밋 안 됨)
- `requirements.txt`: `requests`, `python-dotenv`, `pycountry`
- 데이터 재수집은 `cd 문화 && python3 collect_data.py`
