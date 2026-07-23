"""Calibration-aware edge-cost utilities.

This module converts hardware instruction properties into non-negative
additive routing costs. The functions are deliberately independent of Qiskit:
any object exposing ``error`` and ``duration`` attributes can be used.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log1p, isfinite
from typing import Protocol, runtime_checkable


@runtime_checkable
class InstructionPropertiesLike(Protocol):
    """Minimal instruction-properties interface used by this package."""

    error: float | None
    duration: float | None


@dataclass(frozen=True, slots=True)
class EdgeCalibration:
    """Normalized calibration values and their additive cost components.

    Attributes:
        error_rate: Validated two-qubit instruction error probability in
            ``[0, 1)``.
        duration: Validated non-negative duration in the caller's chosen time
            unit. Qiskit commonly reports seconds.
        hop_cost: Base cost of traversing one hardware edge.
        error_cost: Additive reliability penalty ``-log(1 - error_rate)``.
        normalized_duration: ``duration / duration_scale``.
        total_cost: Weighted sum of the three cost components.
    """

    error_rate: float
    duration: float
    hop_cost: float
    error_cost: float
    normalized_duration: float
    total_cost: float


def _require_real(name: str, value: object) -> float:
    """Validate and convert a finite real number, rejecting booleans.

    Args:
        name: Name used in error messages.
        value: Candidate numeric value.

    Returns:
        The validated floating-point value.

    Raises:
        TypeError: If ``value`` is not a real number.
        ValueError: If ``value`` is not finite.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")

    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")

    return result


def validate_error_rate(error_rate: float, *, clamp: bool = False) -> float:
    """Validate a gate error probability.

    Args:
        error_rate: Probability-like value expected in ``[0, 1)``.
        clamp: When ``True``, values below zero are clamped to zero and values
            at or above one are clamped to ``1 - 1e-12``.

    Returns:
        The validated or clamped error rate.

    Raises:
        ValueError: If ``error_rate`` is out of range and ``clamp`` is false.
    """

    value = _require_real("error_rate", error_rate)

    if clamp:
        return min(max(value, 0.0), 1.0 - 1e-12)

    if not 0.0 <= value < 1.0:
        raise ValueError("error_rate must satisfy 0 <= error_rate < 1")

    return value


def error_to_additive_cost(error_rate: float, *, clamp: bool = False) -> float:
    """Convert an error probability into an additive path penalty.

    Args:
        error_rate: Probability-like value expected in ``[0, 1)``.
        clamp: When ``True``, out-of-range values are clamped before
            conversion.

    Returns:
        The additive reliability penalty ``-log(1 - error_rate)``.
    """

    error = validate_error_rate(error_rate, clamp=clamp)
    return -log1p(-error)


def normalize_duration(duration: float, *, duration_scale: float) -> float:
    """Normalize a non-negative duration by a positive finite scale.

    Args:
        duration: Non-negative duration in the caller's unit.
        duration_scale: Positive scale used to normalize ``duration``.

    Returns:
        The normalized duration.
    """

    value = _require_real("duration", duration)
    scale = _require_real("duration_scale", duration_scale)

    if value < 0.0:
        raise ValueError("duration cannot be negative")
    if scale <= 0.0:
        raise ValueError("duration_scale must be positive")

    return value / scale


def combined_edge_cost(
    *,
    error_rate: float = 0.0,
    duration: float = 0.0,
    hop_cost: float = 1.0,
    hop_weight: float = 1.0,
    error_weight: float = 0.0,
    duration_weight: float = 0.0,
    duration_scale: float = 1e-7,
    clamp_error: bool = False,
) -> EdgeCalibration:
    """Calculate all edge-cost components and their weighted total.

    Args:
        error_rate: Gate error probability.
        duration: Gate duration.
        hop_cost: Base cost for one hop.
        hop_weight: Weight applied to ``hop_cost``.
        error_weight: Weight applied to the additive error penalty.
        duration_weight: Weight applied to the normalized duration.
        duration_scale: Scale used to normalize duration.
        clamp_error: Whether to clamp error values outside ``[0, 1)``.

    Returns:
        A validated ``EdgeCalibration`` record.

    Raises:
        ValueError: If any cost or weight is negative.
    """

    hop = _require_real("hop_cost", hop_cost)
    hop_w = _require_real("hop_weight", hop_weight)
    error_w = _require_real("error_weight", error_weight)
    duration_w = _require_real("duration_weight", duration_weight)

    for name, value in (
        ("hop_cost", hop),
        ("hop_weight", hop_w),
        ("error_weight", error_w),
        ("duration_weight", duration_w),
    ):
        if value < 0.0:
            raise ValueError(f"{name} cannot be negative")

    validated_error = validate_error_rate(error_rate, clamp=clamp_error)
    validated_duration = _require_real("duration", duration)
    if validated_duration < 0.0:
        raise ValueError("duration cannot be negative")

    error_cost = error_to_additive_cost(validated_error)
    normalized = normalize_duration(
        validated_duration,
        duration_scale=duration_scale,
    )

    total = hop_w * hop + error_w * error_cost + duration_w * normalized

    return EdgeCalibration(
        error_rate=validated_error,
        duration=validated_duration,
        hop_cost=hop,
        error_cost=error_cost,
        normalized_duration=normalized,
        total_cost=total,
    )


def calibration_from_properties(
    properties: InstructionPropertiesLike | None,
    **cost_options: float | bool,
) -> EdgeCalibration:
    """Build an edge calibration from a Qiskit-like properties object.

    Args:
        properties: Qiskit-like instruction properties object.
        **cost_options: Keyword arguments forwarded to
            ``combined_edge_cost``.

    Returns:
        A validated ``EdgeCalibration`` record.

    Notes:
        Missing properties, or attributes whose value is ``None``, are
        interpreted as zero error and zero duration.
    """

    if properties is None:
        error_rate = 0.0
        duration = 0.0
    else:
        error_value = getattr(properties, "error", None)
        duration_value = getattr(properties, "duration", None)
        error_rate = 0.0 if error_value is None else error_value
        duration = 0.0 if duration_value is None else duration_value

    return combined_edge_cost(
        error_rate=error_rate,
        duration=duration,
        **cost_options,
    )
