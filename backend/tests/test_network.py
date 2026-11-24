"""Railway topology model."""
from __future__ import annotations

import pytest

from app.domain.network import Network, TopologyError, build_default_network


def test_default_network_shape():
    network = build_default_network()
    assert [station.id for station in network.stations] == [
        "NDL",
        "KRN",
        "MLG",
        "SRP",
        "VSN",
    ]
    assert len(network.sections) == 4
    assert network.section("S1").mode == "SINGLE"
    assert network.section("S2").mode == "DOUBLE"
    assert network.section("S3").mode == "SINGLE"
    assert network.section("S4").mode == "DOUBLE"
    assert network.station("MLG").is_junction


def test_routes_in_both_directions():
    network = build_default_network()
    assert network.route_stations("NDL", "VSN") == ["NDL", "KRN", "MLG", "SRP", "VSN"]
    assert network.route_stations("VSN", "NDL") == ["VSN", "SRP", "MLG", "KRN", "NDL"]
    assert network.route_stations("NDL", "MLG") == ["NDL", "KRN", "MLG"]
    assert network.route_stations("MLG", "MLG") == ["MLG"]


def test_direction_for():
    network = build_default_network()
    assert network.direction_for("NDL", "VSN") == "UP"
    assert network.direction_for("VSN", "NDL") == "DOWN"


def test_segments_respect_direction():
    network = build_default_network()
    route = network.route_stations("NDL", "VSN")
    segments = network.segments(route, "UP")
    assert [section.id for section, _ in segments] == ["S1", "S2", "S3", "S4"]
    assert all(block.direction in {"UP", "BIDIRECTIONAL"} for _, block in segments)


def test_unknown_station_raises():
    network = build_default_network()
    with pytest.raises(TopologyError):
        network.station("XXX")
    with pytest.raises(TopologyError):
        network.route_stations("NDL", "XXX")


def test_roundtrip_serialisation():
    network = build_default_network()
    restored = Network.from_dict(network.to_dict())
    assert [station.id for station in restored.stations] == [
        station.id for station in network.stations
    ]
    assert [section.id for section in restored.sections] == [
        section.id for section in network.sections
    ]
    restored.validate()


def test_invalid_network_is_rejected():
    data = build_default_network().to_dict()
    data["sections"][0]["from_station"] = "XXX"
    with pytest.raises(TopologyError):
        Network.from_dict(data).validate()
