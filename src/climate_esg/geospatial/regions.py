from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BBox:
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    def __post_init__(self) -> None:
        if self.lon_min >= self.lon_max or self.lat_min >= self.lat_max:
            raise ValueError(f"bbox inválido: {self}")


SANTA_CATARINA = BBox(lon_min=-54.0, lon_max=-48.0, lat_min=-29.5, lat_max=-25.8)

JOINVILLE_LAT = -26.3045
JOINVILLE_LON = -48.8487


def bbox_from_points(points: Iterable[tuple[float, float]], *, margin_deg: float = 2.0) -> BBox:
    coords = [(lat, lon) for lat, lon in points]
    if not coords:
        raise ValueError("sem pontos para derivar bbox")
    lats = [lat for lat, _ in coords]
    lons = [lon for _, lon in coords]
    return BBox(
        lon_min=max(-180.0, min(lons) - margin_deg),
        lon_max=min(180.0, max(lons) + margin_deg),
        lat_min=max(-90.0, min(lats) - margin_deg),
        lat_max=min(90.0, max(lats) + margin_deg),
    )
