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

- **SET1 (대형 슈퍼셀)**: 단독 분자 3(CO₂·H₂O·SO₂), 표면 3(Ti2CF2·Ti2C_OF_alt·Ti2C_FOH_clu),
  복합체 **9종**(각 표면 × 3가스). 세트1 전용 표면 2개는 조성 좌표 미확정(임의로 지어내지 않음).
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
- **역방향 추천**: 조성 격자 평가 → 우선 검토 후보. GPR 비활성 시 잠금 화면(학습 데이터 n/7).
- **조성 지도**: 삼원 좌표(O(0,0)·F(1,0)·OH(0.5,√3/2)) 산점도. ◆ 계산 · 빈 원 계획 · ✕ 미확정.
- **데이터·QC**: energies.csv 표(calc_group 그룹), 누락 체크리스트, QC, CSV 업로드(미리보기→확인→백업).
- **모델 정보**: 타깃별 학습 데이터 n/7, LOOCV MAE/RMSE(활성 시), 데이터 SHA-256.
- **내보내기**: 결과 CSV, 인쇄용 HTML(입력·지표 정의·δ 가정·분류 설정·적용 범위·데이터 없음 항목).

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

## 현재 데이터 기대 동작

- 복합체 **13종** E_ads 계산됨 (SET1 9종 + SET2 4종), 각 세트 안에서만.
- SET2는 H₂O 단독 분자가 없어 H₂O/P(CO₂/H₂O)는 데이터 없음. SET1은 H₂O 복합체가 있어 계산됨.
- 반응성 경향(각 세트 내): SO₂ > H₂O > CO₂ 순으로 더 강하게 흡착하는 경향이 수치로 나타남.
- 조성 지도: 조성 확정 표면만 마커 표시(SET2). SET1 전용 표면·Ti₂C_FH는 좌표 미확정.
- GPR 4개 타깃 모두 비활성(조성 확정 표면 수가 7 미만).

## 실행

```bash
pip install -r requirements.txt
pytest -q              # 테스트
streamlit run app.py   # 앱
```

## 주의

가상 데이터·성능 수치·고객 사례·수상 문구를 만들어 넣지 않습니다.
금지 표현(실제 선택도/포집량 예측, 피독 확정, 안전 구역, 최적 소재, 합격/불합격)을 쓰지 않습니다.
