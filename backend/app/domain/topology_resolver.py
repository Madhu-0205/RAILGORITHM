"""Railway Topology and Directional Resolver for RAILGORITHM.

Dynamically resolves adjacent station relationships, junction branching,
block occupancy, and line clear operational states directly from configured
railway infrastructure topology (Network domain model or simulation state),
without relying on hardcoded linear dictionaries.
"""
from __future__ import annotations

from typing import Any


def get_adjacent_station_ids(network_data: dict, station_id: str) -> set[str]:
    """Return all station IDs that share a direct connecting section with station_id."""
    sections = network_data.get("sections", [])
    neighbors: set[str] = set()
    for sec in sections:
        from_st = sec.get("from_station")
        to_st = sec.get("to_station")
        if from_st == station_id and to_st:
            neighbors.add(to_st)
        elif to_st == station_id and from_st:
            neighbors.add(from_st)
    return neighbors


def resolve_adjacent_stations(
    network_data: dict,
    station_id: str,
    block_occupancy: dict[str, Any] | None = None,
    all_trains: dict[str, Any] | None = None,
    now_min: int = 0,
) -> dict[str, Any]:
    """Dynamically resolve adjacent stations, junction branch lines, and directional context.

    Supports:
    - Linear intermediate stations (one upstream, one downstream)
    - Terminal stations (only upstream or only downstream)
    - Junction stations with 2, 3, or more converging branch lines
    - Arbitrary non-linear track layouts
    """
    stations_map = {s["id"]: s for s in network_data.get("stations", [])}
    if station_id not in stations_map:
        raise KeyError(f"Station '{station_id}' not found in network topology")

    curr_st = stations_map[station_id]
    curr_x = float(curr_st.get("x", 0.0))
    sections = network_data.get("sections", [])

    block_occ = block_occupancy or {}
    trains_map = all_trains or {}

    connected_routes = []
    for sec in sections:
        from_st = sec.get("from_station")
        to_st = sec.get("to_station")
        if from_st == station_id and to_st in stations_map:
            connected_routes.append((sec, stations_map[to_st]))
        elif to_st == station_id and from_st in stations_map:
            connected_routes.append((sec, stations_map[from_st]))

    upstream_routes = []
    downstream_routes = []
    lateral_branches = []

    for sec, neighbor in connected_routes:
        n_x = float(neighbor.get("x", 0.0))
        if n_x < curr_x:
            upstream_routes.append((sec, neighbor))
        elif n_x > curr_x:
            downstream_routes.append((sec, neighbor))
        else:
            lateral_branches.append((sec, neighbor))

    # Sort routes by proximity (|n_x - curr_x|)
    upstream_routes.sort(key=lambda item: abs(float(item[1].get("x", 0.0)) - curr_x))
    downstream_routes.sort(key=lambda item: abs(float(item[1].get("x", 0.0)) - curr_x))

    def _build_neighbor_view(sec: dict, neighbor: dict, position_label: str) -> dict[str, Any]:
        blocks = sec.get("blocks", [])
        block_details = []
        for blk in blocks:
            b_id = blk.get("id", "BLK")
            occ = block_occ.get(b_id, {})
            occ_train_id = occ.get("train_id")
            occ_tr = trains_map.get(occ_train_id) if occ_train_id else None

            b_state = "OCCUPIED" if occ_train_id else "CLEAR"
            block_details.append({
                "block_id": b_id,
                "direction": blk.get("direction", "BIDIRECTIONAL"),
                "signaling_type": blk.get("signaling_type", "ABSOLUTE_BLOCK"),
                "state": b_state,
                "train": {
                    "train_id": occ_train_id,
                    "train_name": occ_tr.get("name", occ_train_id) if occ_tr else None,
                    "direction": occ_tr.get("direction") if occ_tr else None,
                    "speed_kmph": occ_tr.get("speed_kmph", 0.0) if occ_tr else None,
                } if occ_train_id else None,
            })

        has_occupant = any(b["state"] == "OCCUPIED" for b in block_details)
        token_status = "LINE_CLEAR_OCCUPIED" if has_occupant else "LINE_CLEAR_NORMAL"

        return {
            "station_id": neighbor["id"],
            "station_name": neighbor.get("name", neighbor["id"]),
            "code": neighbor.get("code", neighbor["id"]),
            "relative_position": position_label,
            "distance_km": float(sec.get("distance_km", 10.0)),
            "section_id": sec.get("id"),
            "section_mode": sec.get("mode", "SINGLE"),
            "headway_min": int(sec.get("headway_min", 3)),
            "blocks": block_details,
            "line_clear_status": token_status,
            "last_movement_event": {
                "message": f"Block section {sec.get('id')} under Absolute Block regulation",
                "time_min": max(0, now_min - 4),
            },
            "telemetry_freshness_seconds": 5,
            "data_classification": "SIMULATION",
        }

    upstream_view = None
    if upstream_routes:
        sec, neighbor = upstream_routes[0]
        upstream_view = _build_neighbor_view(sec, neighbor, "UPSTREAM (Rear Station)")

    downstream_view = None
    if downstream_routes:
        sec, neighbor = downstream_routes[0]
        downstream_view = _build_neighbor_view(sec, neighbor, "DOWNSTREAM (Advance Station)")

    # Any secondary routes (junction branches)
    branches = []
    # Additional upstream routes beyond the primary
    for sec, neighbor in upstream_routes[1:]:
        branches.append({
            "branch_id": sec.get("id"),
            "name": f"Branch Line to {neighbor.get('name', neighbor['id'])}",
            "destination_station": neighbor["id"],
            "mode": sec.get("mode", "SINGLE"),
            "distance_km": float(sec.get("distance_km", 10.0)),
            "status": "OCCUPIED" if any(block_occ.get(b.get("id", ""), {}).get("train_id") for b in sec.get("blocks", [])) else "CLEAR",
            "signaling": sec.get("blocks", [{}])[0].get("signaling_type", "ABSOLUTE_BLOCK"),
            "data_classification": "SIMULATION",
        })

    # Additional downstream routes beyond the primary
    for sec, neighbor in downstream_routes[1:]:
        branches.append({
            "branch_id": sec.get("id"),
            "name": f"Branch Line to {neighbor.get('name', neighbor['id'])}",
            "destination_station": neighbor["id"],
            "mode": sec.get("mode", "SINGLE"),
            "distance_km": float(sec.get("distance_km", 10.0)),
            "status": "OCCUPIED" if any(block_occ.get(b.get("id", ""), {}).get("train_id") for b in sec.get("blocks", [])) else "CLEAR",
            "signaling": sec.get("blocks", [{}])[0].get("signaling_type", "ABSOLUTE_BLOCK"),
            "data_classification": "SIMULATION",
        })

    # Lateral same-x branches
    for sec, neighbor in lateral_branches:
        branches.append({
            "branch_id": sec.get("id"),
            "name": f"Siding / Feeder to {neighbor.get('name', neighbor['id'])}",
            "destination_station": neighbor["id"],
            "mode": sec.get("mode", "SINGLE"),
            "distance_km": float(sec.get("distance_km", 5.0)),
            "status": "OCCUPIED" if any(block_occ.get(b.get("id", ""), {}).get("train_id") for b in sec.get("blocks", [])) else "CLEAR",
            "signaling": "ONE_TRAIN_ONLY_SYSTEM",
            "data_classification": "SIMULATION",
        })

    return {
        "station_id": station_id,
        "station_name": curr_st.get("name", station_id),
        "is_junction": bool(curr_st.get("is_junction", False) or len(connected_routes) > 2),
        "total_connected_routes": len(connected_routes),
        "upstream_station": upstream_view,
        "downstream_station": downstream_view,
        "junction_branches": branches,
        "data_classification": "SIMULATION",
    }
