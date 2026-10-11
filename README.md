# 배가스 맞춤형 Ti2C MXene AI-DFT 스크리닝 플랫폼

Ti2C MXene 표면 말단기(-O, -F, -OH) 조성에 따른 CO2 / H2O / SO2 흡착 거동을
DFT 계산 결과로부터 산출·시각화하고, GPR 기반 Active Learning으로 조성 공간을
스캔해 최적 조성을 추천하는 B2B 웹 플랫폼.

## 데이터 무결성 원칙

- 에너지 값은 **코드에 하드코딩하지 않는다.** 오직 `data/energies.csv`에서만 읽는다.
- 값이 없으면 임의값·더미·가상 데이터로 채우지 않고 **"데이터 없음(pending)"** 으로 표시한다.
- 모든 숫자에는 출처(`source_file`)와 `calc_group`이 따라붙는다.
- 서로 다른 `calc_group`의 값은 **절대 섞어서 계산하지 않는다.**
- 새 데이터는 코드 수정 없이 **CSV 행 추가 또는 앱 내 업로드**로만 반영된다.

## 구조

```
project/
  app.py            # Streamlit UI (한국어) — 5페이지 라우팅, 표시 전담
  .streamlit/
    config.toml         # 테마(라이트 기본, 딥 틸 주조색)
  ui/               # 디자인 시스템 (표현 레이어, core와 분리)
    tokens.py           # 색상·상태색·가스 고정색 단일 소스
    theme.py            # 전역 CSS(Pretendard/JetBrains Mono, 카드, 배지, 다크모드)
    components.py       # pill 배지·KPI·안내/빈 상태·진행바·출처 칩
    charts.py           # Plotly 헬퍼(배경 투명, 가스 고정색, 축 단위)
  core/             # 순수 계산 로직 (Streamlit 비의존, pytest 대상)
  data/
    energies.csv        # 에너지 (유일한 에너지 출처)
    geometry.csv        # Δd 입력 (z_before/z_after). 현재 값 없음 → Δd pending
    composition_map.csv # 표면 → [xO, xF, xOH] 매핑
  tests/            # pytest 단위 테스트 (51개)
```

## 페이지 (사이드바 내비게이션)

1. **Overview** — 가치 제안 + KPI 카드 4개 + E_ad 요약 막대차트 + 다음에 필요한 계산 체크리스트
2. **정방향 검증** — 표면/가스 선택 → E_ad 큰 숫자 + 해석 배지 + 계산 과정 접이식 + 선택성 지표
3. **역방향 추천** — 조성 삼각도(ternary), 데이터 부족 시 흐림+잠금, 활성 시 Pareto 추천/AL 후보
4. **모델 품질** — LOOCV MAE/RMSE/R²/N (충분할 때만)
5. **데이터 레지스트리** — 검색/필터, calc_group별 그룹, 상태 배지, CSV 업로드

## 디자인 원칙

- "결론은 위에, 근거는 아래에"(점진적 공개). 숫자가 주인공(tabular-nums).
- 상태색 의미 고정: ok=에메랄드, pending=앰버, suspect=레드, info=블루.
- 가스 고정색: CO₂=틸, H₂O=블루, SO₂=앰버. 색만으로 구분하지 않고 아이콘·라벨 병기.
- 모든 계산값에 출처(source_file·calc_group) 추적 가능.

## 실행

```bash
pip install -r requirements.txt

# 테스트 (core는 Streamlit 없이 실행됨)
pytest -q

# 앱 실행
streamlit run app.py
```

## 단위

`1 Ry = 13.6057 eV`. 화면에는 eV와 Ry를 모두 표시한다.

## 지표 정의

- `E_ad = E_adsorbed − (E_clean + E_molecule)` — 세 값이 모두 존재하고 calc_group이 동일할 때만 계산.
- `P(CO2/H2O) = E_ads(H2O) − E_ads(CO2)`
- `P(CO2/SO2) = E_ads(SO2) − E_ads(CO2)`
- `Δd_surface = |mean(z_after) − mean(z_before)|` — 가스 쪽 면 말단 원자들의 평균 z 변화량 (SO2 한정)
- `E_ad`가 -3 eV 미만 또는 +0.5 eV 초과이면 **suspect** 경고.

## 현재 데이터(calc_group=A)로 기대되는 동작

- H2O 단독 분자 에너지가 없으므로 H2O 관련 항목과 **모든 P 지수는 pending**.
- `Δd`는 geometry 값이 없으므로 pending.
- Ti2C_FH는 H의 OH 환산이 미확정이라 조성 미매핑 → GPR 학습 제외.
- 유효 학습 표면이 7개 미만이라 **Tab B의 모든 GPR 모델은 비활성**.
