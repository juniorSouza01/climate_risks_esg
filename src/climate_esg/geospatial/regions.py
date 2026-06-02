from __future__ import annotations

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
