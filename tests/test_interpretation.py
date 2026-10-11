"""해석 배지 경계값 테스트 — ui.components.adsorption_interpretation.

경계값은 ui.components.INTERPRETATION_BANDS 에 정의된다.
이 분류는 설명용 상대 구간이며 core 의 suspect 판정과는 독립이다.
"""

from ui.components import adsorption_interpretation, INTERPRETATION_BANDS


def test_bands_defined_as_explicit_constant():
    # 경계값이 상수로 노출되어 있어야 한다 (코드 어디에 있는지 명확)
    labels = [b[1] for b in INTERPRETATION_BANDS]
    assert labels == ["강한 흡착", "중간 흡착", "약한 흡착", "흡착 불리(양의 E_ad)"]


def test_strong_adsorption():
    assert adsorption_interpretation(-1.0) == ("강한 흡착", "ok")
    assert adsorption_interpretation(-2.5) == ("강한 흡착", "ok")


def test_medium_adsorption():
    # -1.0 < E_ad ≤ -0.3
    assert adsorption_interpretation(-0.9) == ("중간 흡착", "info")
    assert adsorption_interpretation(-0.3) == ("중간 흡착", "info")


def test_weak_adsorption():
    # -0.3 < E_ad < 0.0
    assert adsorption_interpretation(-0.29) == ("약한 흡착", "pending")
    assert adsorption_interpretation(-0.001) == ("약한 흡착", "pending")


def test_unfavorable_adsorption():
    # E_ad ≥ 0.0
    assert adsorption_interpretation(0.0) == ("흡착 불리(양의 E_ad)", "suspect")
    assert adsorption_interpretation(0.4) == ("흡착 불리(양의 E_ad)", "suspect")


def test_initial_data_examples():
    # 초기 데이터 흡착 에너지들은 모두 '중간/약한' 구간
    assert adsorption_interpretation(-0.894)[0] == "중간 흡착"   # SO2@Ti2CO2
    assert adsorption_interpretation(-0.524)[0] == "중간 흡착"   # CO2@Ti2CF2
    assert adsorption_interpretation(-0.401)[0] == "중간 흡착"   # CO2@Ti2C_FH
    assert adsorption_interpretation(-0.628)[0] == "중간 흡착"   # CO2@Ti2C_OF
