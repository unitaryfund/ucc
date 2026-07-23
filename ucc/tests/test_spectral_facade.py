"""Tests for the public spectral compiler façade."""

from __future__ import annotations

from ucc.custom_passes.spectral import (
    HardwareMetric,
    SpectralLayoutPass,
    SpectralRoutingPass,
    build_baseline_pass_manager,
    build_spectral_pass_manager,
)


def test_public_facade_exposes_core_builders_and_passes():
    assert build_baseline_pass_manager is not None
    assert build_spectral_pass_manager is not None
    assert HardwareMetric.__name__ == "HardwareMetric"
    assert SpectralLayoutPass.__name__ == "SpectralLayoutPass"
    assert SpectralRoutingPass.__name__ == "SpectralRoutingPass"
