# scripts/ — 데이터 추출 유틸리티

## extract_delta_d.py — QE 파일 → Δd(표면 흐트러짐) 추출

Quantum ESPRESSO 출력(`.out`/`.pwo`) 또는 구조 파일(`.xsf`/`.xyz`)에서 완화 후
원자 좌표를 읽어, 명세 4.3의 Δd 와 '가스 최하단 원자 ↔ 표면 최상단 원자' 수직 거리를
계산해 `data/geometry.csv` 로 저장합니다.

```
Δd = | (z_T − z_ref)_after − (z_T − z_ref)_before |
  z_T   : 가스에 가장 가까운 표면 말단기(–O/–F/–OH) 원자의 z
  z_ref : 가스가 붙는 쪽 Ti 층 평균 z (기준층 → 셀 전체 이동에 무관)
  before: clean 표면,  after: SO₂ 흡착 복합체   (Δd 는 SO₂ 한정)
```

### 사용법

**(A) 매니페스트(권장)** — before/after 쌍을 CSV로 지정:

```bash
# scripts/delta_d_manifest.example.csv 를 복사해 실제 파일명으로 수정
cp scripts/delta_d_manifest.example.csv scripts/delta_d_manifest.csv
#   컬럼: surface,gas,clean_file,adsorbed_file  (gas 는 보통 SO2)

python scripts/extract_delta_d.py \
    --manifest scripts/delta_d_manifest.csv \
    --files-dir data/qe \
    --out data/geometry.csv
```

**(B) 단일 쌍 직접 지정:**

```bash
python scripts/extract_delta_d.py \
    --surface Ti2CO2 \
    --clean    data/qe/Ti2CO2_clean.out \
    --adsorbed data/qe/SO2_on_Ti2CO2.out \
    --gas SO2 \
    --out data/geometry.csv
```

### 입력 파일 두기

QE 파일은 보통 `data/qe/` 에 둡니다(용량이 크면 git 에 올리지 않아도 됩니다).
`geometry.csv` 만 커밋하면 대시보드가 Δd 를 표시합니다.

### 결과가 반영되는 곳 (자동)

`data/geometry.csv` 가 채워지면 재시작 없이 다음 화면이 자동으로 Δd 를 반영합니다:

- **조성 지도**: `Δd` 지표 탭
- **모델 정보**: `Δd` 학습 데이터 축 + LOOCV(학습점 ≥ `min_train_points` 이면 활성)
- **정방향 검증**: 표면별 Δd 행
- **역방향 추천(Pareto)**: Δd 상한을 비지배 선별 축으로 사용

### 좌표 단위/형식

- QE `ATOMIC_POSITIONS` 단위 `angstrom`/`bohr`/`crystal`/`alat` 를 처리합니다
  (crystal/alat 은 `CELL_PARAMETERS`·alat 필요).
- `.xyz`, `.xsf` 는 Å 데카르트 좌표로 가정합니다.
- 가스가 슬랩 위/아래 어디에 붙든 자동으로 그 면을 기준으로 계산합니다.

값을 지어내지 않습니다. 좌표를 읽지 못한 쌍은 건너뛰고 사유를 stderr 로 남깁니다.
