# 배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼

**RE:ACT · 울산대학교 에너지화학공학부 · 2026 UoU 창의적 종합설계 경진대회**

Ti₂C MXene 표면 말단기(-O, -F, -OH) 조성에 따른 CO₂ / H₂O / SO₂ 흡착 거동을
DFT 계산 결과로부터 산출·시각화하고, GPR 기반 Active Learning으로 조성 공간을
스캔해 유망 조성을 탐색하는 웹 플랫폼이다. (Streamlit + Plotly + scikit-learn, Python 3.10)

## 데이터 무결성 원칙 (최우선)

- 에너지 값은 **코드에 하드코딩하지 않는다.** 오직 `data/energies.csv`에서만 읽는다.
- 값이 없으면 임의값·더미·가상 데이터로 채우지 않고 **"데이터 없음(pending)"** 으로 표시한다.
- **가상 데이터·성능 수치·고객 사례·수상/인증 문구·임의 팀원 이름을 만들어 넣지 않는다.**
- 모든 숫자에는 출처(`source_file`)와 `calc_group`이 따라붙는다.
- 서로 다른 `calc_group`의 값은 **절대 섞어서 계산하지 않는다.**
- 새 데이터는 코드 수정 없이 **CSV 행 추가 또는 앱 내 업로드/파일 검사기**로만 반영된다.
- CSV 쓰기는 **백업 + 감사 로그 + 원자적 쓰기(실패 시 롤백)** 를 거친다.

## 카테고리 구조 (사이드바 내비게이션)

- **홈** — Overview: 히어로·시나리오 3카드·파이프라인·KPI·조성 커버리지·기능 둘러보기
- **분석**
  - 정방향 검증: 표면/가스 선택 → E_ad(큰 숫자)·해석 배지·계산 과정·선택성 지표
  - 표면 비교: 2~4개 표면×가스 막대·표, 불가 항목 사유 pill, CSV/PNG
  - 경쟁 흡착 비교: 가스별 그룹 막대, 선택성, 계산 커버리지 매트릭스
- **설계**
  - 배가스 조건 설정: 시나리오 메모(물리 모델 미반영) + 우선순위 슬라이더(정렬 전용)
  - 역방향 추천: 조성 커버리지 삼각도, 잠금/활성, Pareto·우선순위 가중 정렬
- **데이터**
  - 데이터 레지스트리: 검색/필터·calc_group 그룹·상태 배지·CSV 업로드·신뢰 원칙
  - .out 파일 검사기: QE 출력 파싱·CSV 대조·행 후보→확인(백업+감사+원자적 추가)
  - 계산 작업 관리: 34건 계획(jobs.csv)·편집·진행 현황·예상 잔여 시간
  - 무결성 점검: 자동 검사(중복/조건/누락/suspect/재현성/status)·스냅샷 SHA-256
- **모델**
  - 모델 품질: LOOCV MAE/RMSE/R²·예측-실측 parity plot (충분할 때만)
  - 잠금 해제 로드맵: 지표별 현재/7·결정적 다음 후보
- **자료**
  - 방법론: 수식(LaTeX)·계산 조건(계획값, 대조 필요)·설계·한계
  - 용어집: 용어 검색
  - 리포트 내보내기: HTML/Markdown(스냅샷 해시 포함)·CSV 번들(zip)
  - 팀·프로젝트 소개: RE:ACT·목표·가설

각 페이지 상단에 "카테고리 › 페이지" 브레드크럼을 표시한다.
사이드바 하단에 데이터 상태 진행바 3줄(0/7)과 **발표 모드** 토글이 있다.

## 시작 화면

앱 첫 진입 시 사이드바 없는 전체 화면(어두운 그라데이션 + 흐르는 분자 패턴).
"플랫폼 시작하기"를 누르면 Overview로 이동하고(`st.session_state["entered"]`),
사이드바의 "← 시작 화면으로"로 복귀한다. 상태 스트립 수치는 core 함수 결과를 그대로 쓴다.

## 구조

```
project/
  app.py                 # Streamlit UI (한국어) — 16개 페이지 라우팅, 표시 전담
  .streamlit/config.toml # 테마(라이트 기본, 딥 틸) + toolbarMode=minimal
  ui/                    # 표현 레이어 (core와 분리)
    branding.py            # RE:ACT 워드마크·프로젝트/대회 정보·로고 조건부
    landing.py             # 시작 화면
    nav.py                 # 카테고리 내비 구조·아이콘
    tokens.py theme.py components.py charts.py illustrations.py glossary.py
  core/                  # 순수 계산 로직 (Streamlit 비의존, pytest 대상)
    units.py loader.py energetics.py metrics.py composition.py registry.py
    gpr.py quality.py export.py
    qe_parser.py           # QE .out 파싱 (실패 시 추정 없이 사유)
    datafiles.py           # 원자적 쓰기·백업·감사 로그·SHA-256
    integrity.py           # 무결성 자동 검사 규칙
    jobs.py                # 작업 계획(34건)·동기화·ETA
    roadmap.py             # 결정적 잠금 해제 규칙
    report.py              # HTML/Markdown 리포트 생성
  data/
    energies.csv           # 에너지 (유일한 에너지 출처)
    geometry.csv           # Δd 입력 (z_before/z_after). 현재 값 없음 → Δd pending
    composition_map.csv    # 표면 → [xO, xF, xOH] 매핑
    jobs.csv               # 계산 작업 목록
    backup/ audit_log.csv  # CSV 변경 시 자동 생성
  tests/                 # pytest (fixtures 포함)
```

## 데이터 입력 방법

1. **CSV 직접 편집**: `data/energies.csv`에 행 추가. 기존 10개 값은 변경 금지.
   선택 컬럼(`n_atoms, ecutwfc, ecutrho, kpoints, nspin, vdw, converged, pseudos`)은
   추가 가능하고 빈 값 허용.
2. **앱 내 업로드**: 데이터 레지스트리에서 스키마 검증을 통과한 CSV만 반영.
3. **.out 파일 검사기**: QE 출력을 파싱해 CSV에 없는 파일을 행 후보로 생성 →
   미리보기 → 확인 버튼을 눌러야 반영(백업·감사 로그·원자적 쓰기).

## 실행

```bash
pip install -r requirements.txt
pytest -q              # 테스트 (core는 Streamlit 없이 실행)
streamlit run app.py   # 앱 실행
```

## 지표 정의 / 단위

- `E_ad = E_adsorbed − (E_clean + E_molecule)` — 세 값이 모두 존재하고 calc_group이 같을 때만 계산.
- `P(CO2/H2O) = E_ads(H2O) − E_ads(CO2)`, `P(CO2/SO2) = E_ads(SO2) − E_ads(CO2)`
- `Δd_surface = |mean(z_after) − mean(z_before)|` (SO₂ 한정)
- `1 Ry = 13.6057 eV` (화면에는 eV·Ry 모두 표시)
- `E_ad`가 -3 eV 미만 또는 +0.5 eV 초과이면 **suspect** 경고.

## 현재 데이터(calc_group=A)로 기대되는 동작

- H₂O 단독 분자 에너지가 없으므로 H₂O 관련 항목과 **모든 P 지수는 pending**.
- `Δd`는 geometry 값이 없으므로 pending.
- Ti2C_FH는 H의 OH 환산이 미확정이라 조성 미매핑 → GPR 학습 제외.
- 유효 학습 표면이 7개 미만이라 **역방향 추천의 GPR 모델은 비활성(잠금)**.

## 주의 사항

- 이 플랫폼은 **가상 데이터를 생성하지 않는다.** 데이터가 없는 기능은 "대기/잠금"으로 표시된다.
- 방법론 페이지의 계산 조건은 **보고서 계획값**이며 실제 `.out` 값과 대조가 필요하다.
- GPR의 σ는 보정된 불확실성이 아니라 **참고용 상대 지표**다.
