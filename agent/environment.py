"""Estimate the environmental footprint of an LLM query from token counts.

These are order-of-magnitude estimates, not measurements. OpenAI does not
publish per-request energy figures, so we linearize from published research:

- Energy: Epoch AI (2025) estimates ~0.3 Wh for a typical GPT-4o query with
  ~500 output tokens (~0.6 mWh per output token). GPT-4o-mini is roughly an
  order of magnitude smaller, so we scale that per-token figure by 1/10.
  Prompt (prefill) tokens are far cheaper to process than completion (decode)
  tokens; we weight them at 10% of a completion token.
- PUE: datacenter overhead (cooling, power delivery) multiplier, ~1.2 for
  modern hyperscale facilities.
- Carbon: ~0.4 gCO2e per Wh, near the US grid average carbon intensity.
- Water: ~1.8 mL per Wh, covering on-site cooling plus off-site generation
  (Ren et al., "Making AI Less Thirsty").
"""

from dataclasses import dataclass

_ENERGY_WH_PER_COMPLETION_TOKEN = 0.00006
_PROMPT_TOKEN_ENERGY_WEIGHT = 0.10
_DATACENTER_PUE = 1.2
_CARBON_INTENSITY_G_PER_WH = 0.4
_WATER_ML_PER_WH = 1.8
_LED_BULB_WATTS = 10
_SECONDS_PER_HOUR = 3600


@dataclass(frozen=True)
class EnvironmentalImpact:
    energy_wh: float
    co2_grams: float
    water_ml: float

    @property
    def led_bulb_seconds(self) -> float:
        """Seconds a 10 W LED bulb would run on the same energy."""
        return self.energy_wh / _LED_BULB_WATTS * _SECONDS_PER_HOUR


def estimate_impact(*, prompt_tokens: int, completion_tokens: int) -> EnvironmentalImpact:
    """Estimate energy, carbon, and water footprint for one query's tokens."""
    if prompt_tokens < 0 or completion_tokens < 0:
        raise ValueError(
            f"Token counts must be non-negative, got prompt_tokens={prompt_tokens}, "
            f"completion_tokens={completion_tokens}"
        )

    weighted_tokens = completion_tokens + prompt_tokens * _PROMPT_TOKEN_ENERGY_WEIGHT
    energy_wh = weighted_tokens * _ENERGY_WH_PER_COMPLETION_TOKEN * _DATACENTER_PUE

    return EnvironmentalImpact(
        energy_wh=energy_wh,
        co2_grams=energy_wh * _CARBON_INTENSITY_G_PER_WH,
        water_ml=energy_wh * _WATER_ML_PER_WH,
    )
