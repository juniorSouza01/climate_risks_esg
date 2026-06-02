from __future__ import annotations

import pytest

from climate_esg.geospatial.regions import BBox, bbox_from_points


def test_bbox_from_points_aplica_margem() -> None:
    b = bbox_from_points([(-26.30, -48.85), (-26.27, -48.84)], margin_deg=1.0)
    assert b.lat_min == pytest.approx(-27.30)
    assert b.lat_max == pytest.approx(-25.27)
    assert b.lon_min == pytest.approx(-49.85)
    assert b.lon_max == pytest.approx(-47.84)


def test_bbox_from_points_um_ponto_vira_caixa() -> None:
    b = bbox_from_points([(-26.0, -48.0)], margin_deg=2.0)
    assert isinstance(b, BBox)
    assert b.lat_min < b.lat_max
    assert b.lon_min < b.lon_max


def test_bbox_from_points_clampeia_limites() -> None:
    b = bbox_from_points([(-89.0, -179.0), (89.0, 179.0)], margin_deg=5.0)
    assert b.lat_min == -90.0
    assert b.lat_max == 90.0
    assert b.lon_min == -180.0
    assert b.lon_max == 180.0


def test_bbox_from_points_vazio_levanta() -> None:
    with pytest.raises(ValueError, match="sem pontos"):
        bbox_from_points([])
