"""Candidate-path scoring.

score = 0.30*impact + 0.25*evidence + 0.20*confidence
      + 0.15*business + 0.10*reproducibility
Each input is 0..1; the result is 0..1.
"""


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_path(
    impact: float,
    evidence: float,
    confidence: float,
    business: float,
    reproducibility: float,
) -> float:
    return round(
        0.30 * _clamp(impact)
        + 0.25 * _clamp(evidence)
        + 0.20 * _clamp(confidence)
        + 0.15 * _clamp(business)
        + 0.10 * _clamp(reproducibility),
        4,
    )
