# 배가스 맞춤형 Ti₂C MXene 표면 설계 플랫폼

**RE:ACT · 울산대학교 에너지화학공학부 · 2026 UoU 창의적 종합설계 경진대회**
(Streamlit + Plotly + scikit-learn, Python 3.10, 한국어 UI)

Ti₂C MXene 표면 구성(–O, –F, –OH 비율)에 대한 CO₂·H₂O·SO₂ DFT 지표를 보여 주고,
어떤 구성을 먼저 검토할지 분류하며, 다음에 계산할 구성을 추천하는 웹 도구입니다.
기능·계산 규칙의 기준 문서는 `MXene_플랫폼_구현명세_최종.pdf` 입니다.

## 적용 범위 (PDF 1장)

이 도구의 값은 **0 K, 저피복(셀당 1분자) 조건의 DFT 상대 비교 지표**입니다.
실제 포집량이나 혼합기체 선택도를 예측하지 않으며, 실험 전에 후보를 좁히는 용도입니다.
(문구는 `core/scope.py` 한 곳에서 관리하고 결과 화면 상단·내보내기에만 표시합니다.)

## 데이터 무결성 원칙

- 에너지 값은 코드에 하드코딩하지 않고 **`data/`의 CSV에서만** 읽습니다. (환산: `1 Ry = 13.605698 eV`)
- 값이 없으면 가상값으로 채우지 않고 **"데이터 없음"** 으로 표시합니다. 데모 데이터는 만들지 않습니다.
- 모든 계산값에 출처(`source_file`)와 `calc_group`이 따라붙습니다.
- 같은 `source_file`에 서로 다른 `energy_Ry`가 등록되면 **등록을 거부**합니다.
- 서로 다른 `calc_group`의 에너지는 **절대 섞어서 빼지 않습니다.**

## 데이터 세트 (두 calc_group)

- **SET1 (대형 슈퍼셀)**: 단독 분자 3(CO₂·H₂O·SO₂), 표면 7(Ti2CO2·Ti2CF2·Ti2C_OH2·Ti2C_O_OH·
  Ti2C_OF_alt·Ti2C_FOH_clu·Ti2C_ternary), 복합체 **21종**(각 표면 × 3가스). 모든 조성 좌표 확정.
  삼원 대표는 2×2 셀에서 가능한 1/4-격자 점 (0.5, 0.25, 0.25)로 둡니다(명세 3.1·10).
- **SET2 (표준 단위셀)**: 단독 분자 2(CO₂·SO₂), 표면 4(Ti2CO2·Ti2CF2·Ti2C_FH·Ti2C_OF),
  복합체 4종. (H₂O 단독 분자 없음 → SET2에서 H₂O/P(CO₂/H₂O)는 데이터 없음.)
- 두 세트는 셀 크기가 다른 독립 계산이라 **세트 내에서만 E_ads를 계산**하고, 화면에서는 겹쳐 비교만 합니다.
- 복합체 흡착 에너지 비교는 **데이터·QC** 화면의 바 차트/테이블과 시작 화면의 반응성 경향에서 봅니다.

## 단독 실행 스크립트 (요구사항 1~3 직접 충족)

`standalone_app.py` — 시작 페이지(개요+반응성 경향), 두 세트 전체·복합체 9종 인터랙티브 테이블,
Plotly 바 차트를 단일 파일로 제공합니다. 에너지는 `data/energies.csv`에서만 읽습니다.

```bash
streamlit run standalone_app.py
```

## 화면 (시작 + 6개 메뉴)

- **시작 화면** (`ui/landing.py`): 사이드바 없는 전체 화면. "플랫폼 시작하기"로 입장
  (`?enter=1` 또는 우측 상단 "입장 →"로도 가능). "적용 범위 보기"로 적용 범위 펼침.
- **정방향 검증**: 표면 구성·배가스 조건 입력 → 가스별 E_ads(계산/예측), P(CO₂/H₂O),
  P(CO₂/SO₂, 참고용), 보정 후 P_cond, 분류 배지·근거, 가장 가까운 계산 조성.
- **역방향 추천**: 네 모드 — ⓪ **공장 조건 → 최적 비율 추천(기본)**: 공장 배가스(H₂O·SO₂·CO₂ mol%)만
  입력하면 그 조건에서 CO₂ 선호도 P_cond 가 가장 큰 표면 비율(–O/–F/–OH)을 추천(최적+차선+지도).
  ① 조성→예측, ② 목표 E_ads→조성 추천, ③ 우선 검토 후보 탐색(Pareto, 명세 6.2): 격자 분류→비지배
  선별→σ 오름차순, 조성 지도에 후보 표시. 하단에 '다음 계산 후보'(미계산 격자점 중 score=Σσ/s 최대,
  명세 7). GPR 비활성 시 잠금 화면(학습 데이터 n/3).
- **조성 지도**: 삼원 좌표(O(0,0)·F(1,0)·OH(0.5,√3/2)) 산점도. 지표 탭 Eads(CO₂·H₂O·SO₂)·
  P(CO₂/H₂O)·Δd·σ(불확실성). ◆ 계산(색=지표값) · ◇ 이 지표 없음 · 빈 원 계획.
- **데이터·QC**: energies.csv 표(calc_group 그룹), 누락 체크리스트, QC, CSV 업로드(미리보기→확인→백업).
- **모델 정보**: 타깃별 학습 데이터 n/3, LOOCV MAE/RMSE(활성 시), 데이터 SHA-256(energies·composition·geometry).
- **내보내기**: 결과 CSV, 인쇄용 HTML(입력·지표 정의·δ 가정·분류 설정·모델·데이터 버전(SHA·LOOCV)·적용 범위·데이터 없음 항목).

분류 이름은 **우선 검토 / 추가 계산 권장 / 현재 기준 미충족** 만 씁니다 (PDF 9장).

## 계산 규칙 (PDF 4·5·7장)

- `E_ads = E_complex − (E_surface + E_gas)` — 세 값이 있고 calc_group이 같을 때만. `1 Ry = 13.6057 eV`.
- `P(CO₂/H₂O) = E_ads(H₂O) − E_ads(CO₂)`, `P(CO₂/SO₂) = E_ads(SO₂) − E_ads(CO₂)` (참고용).
- `Δd = |(z_T − z_ref)_after − (z_T − z_ref)_before|` (SO₂ 한정).
- 조건 보정 δ (T=298.15 K): `δ = T·[S°(gas) − S°(CO₂)] − kT·ln(p_gas/p_CO₂)`.
  예: CO₂ 12 mol%, H₂O 10 mol%, SO₂ 500 ppm → δ_H₂O=−0.073 eV, δ_SO₂=+0.247 eV.
- GPR: 입력 `u=(xF−xOH)/√2, v=(2xO−xF−xOH)/√6`, 타깃 4개(Eads CO₂/H₂O/SO₂, Δd),
  타깃별 학습 데이터 < `min_train_points`(7)면 비활성.

## 구조

```
project/
  app.py                 # 시작 화면 + 6개 메뉴
  config/settings.json   # 분류 설정값(kappa, margin_m, preset, composition_grid 등)
  core/                  # 순수 계산 (Streamlit 비의존)
    units coords conditions energetics selectivity classify
    grid settings gpr_model screening scope loader composition
  ui/                    # 표현 레이어
    landing nav branding tokens theme components charts htmlutil illustrations
  data/
    energies.csv         # 에너지 (유일한 에너지 출처)
    composition_map.csv  # 표면 → xO,xF,xOH, confirmed, status(computed|planned)
    geometry.csv         # Δd 입력 (현재 비어 있음 → Δd 데이터 없음)
    backup/              # CSV 업로드 시 자동 백업
  tests/                 # pytest
```

이전 버전(.out 검사기, 작업 관리, 무결성 점검, 로드맵, 표면 비교 등)은 `archive/v1` 브랜치에 보존됩니다.

## 데이터 입력

1. `data/energies.csv` 편집 — 기존 값은 유지, 선택 컬럼(converged, setup_hash,
   min_distance_after, reaction_flag, qc_note, cell, arrangement_note)은 비워도 됩니다.
2. 데이터·QC 화면에서 CSV 업로드 — 미리보기·충돌 검사 후 확인하면 백업 뒤 반영됩니다.
3. H₂O 행은 `calc_group=UNASSIGNED`이므로, 사용자가 CSV에서 짝 calc_group을 지정하면 즉시 반영됩니다.

### Δd(표면 흐트러짐) 데이터 — QE 파일에서 자동 추출

`data/geometry.csv`(컬럼 `surface,z_T_before,z_T_after,z_ref_before,z_ref_after`)가 채워지면
조성 지도 Δd 탭·모델 정보 Δd 축·정방향 Δd 행·역방향 Pareto 의 Δd 축이 자동으로 켜집니다.
Quantum ESPRESSO 출력(`.out`/`.pwo`)·구조(`.xsf`/`.xyz`) 파일이 있으면 다음으로 생성합니다:

```bash
python scripts/extract_delta_d.py --manifest scripts/delta_d_manifest.csv \
    --files-dir data/qe --out data/geometry.csv
```

자세한 사용법은 `scripts/README.md`. 좌표를 못 읽으면 그 쌍은 건너뛰고(값 생성 안 함),
`geometry.csv` 가 비어 있으면 Δd 는 '데이터 대기'로 표시됩니다.

## 현재 데이터 기대 동작

- 복합체 **25종** E_ads 계산됨 (SET1 21종 + SET2 4종), 각 세트 안에서만.
- SET1은 7표면 × 3가스가 모두 계산되어 P(CO₂/H₂O)·P(CO₂/SO₂)가 한 세트 안에서 산출됩니다.
  (한 표면이 두 세트에 걸쳐 있으면 가스를 가장 많이 보유한 단일 세트에서 계산 → 세트 혼합 방지.)
- SET2는 H₂O 단독 분자가 없어 SET2 단독으로는 H₂O/P(CO₂/H₂O) 데이터 없음.
- 반응성 경향(각 세트 내): SO₂ > H₂O > CO₂ 순으로 더 강하게 흡착하는 경향이 수치로 나타남.
- 조성 지도: 조성 확정 표면만 마커 표시. Ti₂C_FH는 H→OH 환산 가정으로 F:OH 50:50(0,0.5,0.5) 좌표를 부여해 확정 처리.
- GPR 활성 threshold=3. 현재 Eads(CO₂·H₂O·SO₂) 타깃은 활성, Δd는 geometry 데이터가
  입력되기 전까지 비활성(위 'Δd 데이터' 절대로 geometry.csv 를 채우면 활성화).

## 실행

```bash
pip install -r requirements.txt
pytest -q              # 테스트
streamlit run app.py   # 앱
```

## 주의

가상 데이터·성능 수치·고객 사례·수상 문구를 만들어 넣지 않습니다.
금지 표현(실제 선택도/포집량 예측, 피독 확정, 안전 구역, 최적 소재, 합격/불합격)을 쓰지 않습니다.
