"""Unit tests for Phase 2 calibration-aware edge costs."""

from __future__ import annotations

from types import SimpleNamespace
from math import log
from pytest import mark, approx, raises

from ucc.custom_passes.spectral.calibration import (
    EdgeCalibration,
    calibration_from_properties,
    combined_edge_cost,
    error_to_additive_cost,
    normalize_duration,
    validate_error_rate,
)


def test_zero_error_has_zero_additive_cost():
    assert error_to_additive_cost(0.0) == approx(0.0)


def test_error_cost_matches_negative_log_reliability():
    error = 0.02
    assert error_to_additive_cost(error) == approx(-log(0.98))


def test_error_cost_increases_monotonically():
    assert error_to_additive_cost(0.02) > error_to_additive_cost(0.01)


@mark.parametrize("error", [-0.1, 1.0, 1.1])
def test_strict_error_validation_rejects_out_of_range_values(error):
    with raises(ValueError, match="0 <= error_rate < 1"):
        validate_error_rate(error)


def test_error_clamping_is_explicit():
    assert validate_error_rate(-0.2, clamp=True) == 0.0
    assert validate_error_rate(1.5, clamp=True) < 1.0


@mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_error_is_rejected(value):
    with raises(ValueError, match="finite"):
        validate_error_rate(value)


def test_duration_normalization():
    assert normalize_duration(300e-9, duration_scale=100e-9) == approx(3.0)


def test_negative_duration_is_rejected():
    with raises(ValueError, match="negative"):
        normalize_duration(-1e-9, duration_scale=1e-7)


def test_non_positive_duration_scale_is_rejected():
    with raises(ValueError, match="positive"):
        normalize_duration(1e-9, duration_scale=0.0)


def test_combined_cost_reduces_to_hop_cost():
    calibration = combined_edge_cost(
        error_rate=0.0,
        duration=0.0,
        hop_cost=1.0,
        hop_weight=1.0,
        error_weight=0.0,
        duration_weight=0.0,
    )

    assert isinstance(calibration, EdgeCalibration)
    assert calibration.total_cost == approx(1.0)


def test_combined_cost_contains_all_weighted_components():
    calibration = combined_edge_cost(
        error_rate=0.02,
        duration=300e-9,
        hop_cost=1.0,
        hop_weight=2.0,
        error_weight=4.0,
        duration_weight=0.5,
        duration_scale=100e-9,
    )

    expected = 2.0 + 4.0 * (-log(0.98)) + 0.5 * 3.0
    assert calibration.total_cost == approx(expected)
    assert calibration.normalized_duration == approx(3.0)


@mark.parametrize(
    "field,value",
    [
        ("hop_cost", -1.0),
        ("hop_weight", -1.0),
        ("error_weight", -1.0),
        ("duration_weight", -1.0),
    ],
)
def test_negative_cost_inputs_are_rejected(field, value):
    options = {
        "hop_cost": 1.0,
        "hop_weight": 1.0,
        "error_weight": 1.0,
        "duration_weight": 1.0,
    }
    options[field] = value

    with raises(ValueError, match=field):
        combined_edge_cost(**options)


def test_properties_object_is_read_without_qiskit_dependency():
    properties = SimpleNamespace(error=0.02, duration=300e-9)

    calibration = calibration_from_properties(
        properties,
        error_weight=4.0,
        duration_weight=0.5,
        duration_scale=100e-9,
    )

    assert calibration.error_rate == approx(0.02)
    assert calibration.duration == approx(300e-9)
    assert calibration.total_cost > 1.0


def test_none_properties_use_zero_calibration_values():
    calibration = calibration_from_properties(None)

    assert calibration.error_rate == 0.0
    assert calibration.duration == 0.0
    assert calibration.total_cost == approx(1.0)


def test_none_attributes_use_zero_values():
    properties = SimpleNamespace(error=None, duration=None)
    calibration = calibration_from_properties(properties)

    assert calibration.error_rate == 0.0
    assert calibration.duration == 0.0


def test_two_edge_path_error_cost_equals_negative_log_path_reliability():
    first = error_to_additive_cost(0.01)
    second = error_to_additive_cost(0.02)

    summed_cost = first + second
    path_reliability = (1.0 - 0.01) * (1.0 - 0.02)

    assert summed_cost == approx(-log(path_reliability))
