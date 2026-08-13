import pytest

from agent.environment import EnvironmentalImpact, estimate_impact


def test_estimate_impact_returns_positive_values_for_typical_query():
    # Arrange: token counts from a typical run
    prompt_tokens = 1500
    completion_tokens = 600

    # Act
    impact = estimate_impact(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    # Assert
    assert isinstance(impact, EnvironmentalImpact)
    assert impact.energy_wh > 0
    assert impact.co2_grams > 0
    assert impact.water_ml > 0


def test_estimate_impact_is_zero_for_zero_tokens():
    impact = estimate_impact(prompt_tokens=0, completion_tokens=0)

    assert impact.energy_wh == 0
    assert impact.co2_grams == 0
    assert impact.water_ml == 0
    assert impact.led_bulb_seconds == 0


def test_estimate_impact_scales_linearly_with_tokens():
    # Arrange
    small = estimate_impact(prompt_tokens=100, completion_tokens=100)
    large = estimate_impact(prompt_tokens=200, completion_tokens=200)

    # Assert: doubling tokens doubles every estimate
    assert large.energy_wh == pytest.approx(2 * small.energy_wh)
    assert large.co2_grams == pytest.approx(2 * small.co2_grams)
    assert large.water_ml == pytest.approx(2 * small.water_ml)


def test_completion_tokens_weigh_more_than_prompt_tokens():
    prompt_heavy = estimate_impact(prompt_tokens=1000, completion_tokens=0)
    completion_heavy = estimate_impact(prompt_tokens=0, completion_tokens=1000)

    assert completion_heavy.energy_wh > prompt_heavy.energy_wh


def test_led_bulb_seconds_derived_from_energy():
    impact = estimate_impact(prompt_tokens=0, completion_tokens=1000)

    # 10 W bulb: seconds = Wh / 10 W * 3600 s/h
    assert impact.led_bulb_seconds == pytest.approx(impact.energy_wh / 10 * 3600)


def test_estimate_impact_rejects_negative_tokens():
    with pytest.raises(ValueError):
        estimate_impact(prompt_tokens=-1, completion_tokens=0)
    with pytest.raises(ValueError):
        estimate_impact(prompt_tokens=0, completion_tokens=-1)
