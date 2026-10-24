import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.geo import distance_km, haversine_km, within_radius  # noqa: E402

CHENNAI = (13.08, 80.27)
PUNE = (18.52, 73.86)


def test_chennai_to_pune_great_circle():
    assert haversine_km(*CHENNAI, *PUNE) == pytest.approx(915, rel=0.02)


def test_zero_distance():
    assert haversine_km(*CHENNAI, *CHENNAI) == 0


def test_distance_accepts_dicts_tuples_and_objects():
    class Point:
        lat, lon = PUNE

    d = distance_km({"lat": 13.08, "lon": 80.27}, Point())
    assert d == pytest.approx(distance_km(CHENNAI, PUNE))


def test_within_radius_uses_buffer():
    # Sriperumbudur is ~40 km from central Chennai.
    sriperumbudur = (12.97, 79.94)
    assert within_radius(sriperumbudur, CHENNAI, radius_km=35)  # 35 * 1.2 = 42
    assert not within_radius(sriperumbudur, CHENNAI, radius_km=35, buffer=1.0)
    assert not within_radius(PUNE, CHENNAI, radius_km=150)
