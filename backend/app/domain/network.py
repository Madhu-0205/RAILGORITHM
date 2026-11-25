"""Configurable synthetic railway topology.

The topology is deliberately explicit: stations, platforms, single/double line
sections and blocks. All values are configuration inputs to the simulation and
the independent validator; nothing is inferred from UI state.

Macroscopic Dispatching Scope:
RAILGORITHM models macroscopic railway corridor movements (station berthing, line clear,
section headways, and aggregate junction throat bottlenecks). It is an advisory decision-support
system and does NOT emulate vital electronic micro-interlocking (route control charts, point motor
relays, signal aspect cascades). Non-vital advisory schedules are subject to Station Master and
Section Controller verification against physical station working rules and interlocking tables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


class TopologyError(ValueError):
    """Raised when the configured topology is internally inconsistent."""


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    code: str
    platforms: tuple[str, ...]
    x: float
    is_junction: bool = False
    platform_length_m: int = 600
    junction_throat_capacity: int = 2
    platform_electrification: bool = True
    incompatible_route_pairs: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Block:
    id: str
    direction: str  # UP | DOWN | BIDIRECTIONAL
    run_time_min: int
    gradient_pct: float = 0.0
    km_start: float = 0.0
    km_end: float = 10.0
    signaling_type: str = "ABSOLUTE_BLOCK"  # ABSOLUTE_BLOCK | AUTOMATIC_BLOCK


@dataclass(frozen=True)
class Section:
    id: str
    from_station: str
    to_station: str
    mode: str  # SINGLE | DOUBLE
    blocks: tuple[Block, ...]
    headway_min: int = 3
    max_speed_kmph: int = 100
    distance_km: float = 10.0
    traction_type: str = "25kV_AC_ELECTRIC"  # 25kV_AC_ELECTRIC | DIESEL


@dataclass(frozen=True)
class Network:
    id: str
    name: str
    timezone: str
    stations: tuple[Station, ...]
    sections: tuple[Section, ...]
    label: str = "SYNTHETIC"

    # ---- lookups -----------------------------------------------------------
    @property
    def station_map(self) -> dict[str, Station]:
        return {station.id: station for station in self.stations}

    @property
    def section_map(self) -> dict[str, Section]:
        return {section.id: section for section in self.sections}

    @property
    def block_map(self) -> dict[str, Block]:
        return {
            block.id: block
            for section in self.sections
            for block in section.blocks
        }

    def section_for_block(self, block_id: str) -> Section:
        for section in self.sections:
            if any(block.id == block_id for block in section.blocks):
                return section
        raise TopologyError(f"Unknown block '{block_id}'")

    def adjacent_sections(self, station_id: str) -> list[Section]:
        self.station(station_id)
        return [
            section
            for section in self.sections
            if station_id in {section.from_station, section.to_station}
        ]

    def station(self, station_id: str) -> Station:
        try:
            return self.station_map[station_id]
        except KeyError as exc:
            raise TopologyError(f"Unknown station '{station_id}'") from exc

    def section(self, section_id: str) -> Section:
        try:
            return self.section_map[section_id]
        except KeyError as exc:
            raise TopologyError(f"Unknown section '{section_id}'") from exc

    def section_between(self, a: str, b: str) -> Section:
        for section in self.sections:
            if {section.from_station, section.to_station} == {a, b}:
                return section
        raise TopologyError(f"No section connects '{a}' and '{b}'")

    def block_for(self, section: Section, direction: str) -> Block:
        if direction not in {"UP", "DOWN"}:
            raise TopologyError(f"Invalid direction '{direction}'")
        for block in section.blocks:
            if block.direction == direction:
                return block
        for block in section.blocks:
            if block.direction == "BIDIRECTIONAL":
                return block
        raise TopologyError(
            f"Section '{section.id}' has no block usable in direction {direction}"
        )

    def route_stations(self, origin: str, destination: str) -> list[str]:
        """Route through the linear section graph, ordered by x coordinate."""
        stations = sorted(self.stations, key=lambda station: station.x)
        ids = [station.id for station in stations]
        if origin not in ids or destination not in ids:
            raise TopologyError("Origin or destination is not part of the topology")
        start, end = ids.index(origin), ids.index(destination)
        if start == end:
            return [origin]
        step = 1 if end > start else -1
        stop = end + step
        if stop < 0:
            stop = None
        route = ids[start:stop:step]
        for left, right in zip(route, route[1:]):
            self.section_between(left, right)
        return route

    def direction_for(self, origin: str, destination: str) -> str:
        origin_x = self.station(origin).x
        destination_x = self.station(destination).x
        if origin_x == destination_x:
            raise TopologyError("Origin and destination are the same station")
        return "UP" if destination_x > origin_x else "DOWN"

    def segments(self, route: Iterable[str], direction: str) -> list[tuple[Section, Block]]:
        route_list = list(route)
        result: list[tuple[Section, Block]] = []
        for left, right in zip(route_list, route_list[1:]):
            section = self.section_between(left, right)
            result.append((section, self.block_for(section, direction)))
        return result

    def validate(self) -> None:
        station_ids = [station.id for station in self.stations]
        if len(station_ids) != len(set(station_ids)):
            raise TopologyError("Duplicate station identifiers")
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise TopologyError("Duplicate section identifiers")
        if len(self.stations) < 2:
            raise TopologyError("Topology requires at least two stations")
        seen_pairs: set[frozenset[str]] = set()
        for station in self.stations:
            if not station.platforms:
                raise TopologyError(f"Station '{station.id}' has no platforms")
            if len(set(station.platforms)) != len(station.platforms):
                raise TopologyError(f"Station '{station.id}' has duplicate platforms")
        for section in self.sections:
            if section.from_station not in station_ids or section.to_station not in station_ids:
                raise TopologyError(f"Section '{section.id}' references unknown station")
            pair = frozenset({section.from_station, section.to_station})
            if pair in seen_pairs:
                raise TopologyError("Multiple sections between the same station pair")
            seen_pairs.add(pair)
            block_ids = [block.id for block in section.blocks]
            if len(block_ids) != len(set(block_ids)):
                raise TopologyError(f"Section '{section.id}' has duplicate blocks")
            if section.mode == "SINGLE":
                if len(section.blocks) != 1 or section.blocks[0].direction != "BIDIRECTIONAL":
                    raise TopologyError(
                        f"Single-line section '{section.id}' must have one bidirectional block"
                    )
            elif section.mode == "DOUBLE":
                directions = {block.direction for block in section.blocks}
                if directions != {"UP", "DOWN"}:
                    raise TopologyError(
                        f"Double-line section '{section.id}' must have UP and DOWN blocks"
                    )
            else:
                raise TopologyError(f"Unknown section mode '{section.mode}'")
            for block in section.blocks:
                if block.run_time_min <= 0:
                    raise TopologyError(f"Block '{block.id}' has non-positive run time")
            if section.headway_min < 0:
                raise TopologyError(f"Section '{section.id}' has negative headway")
        # Connectivity check along x ordering.
        ordered = sorted(self.stations, key=lambda station: station.x)
        for left, right in zip(ordered, ordered[1:]):
            self.section_between(left.id, right.id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "timezone": self.timezone,
            "label": self.label,
            "stations": [asdict(station) for station in self.stations],
            "sections": [
                {
                    **{k: v for k, v in asdict(section).items() if k != "blocks"},
                    "blocks": [asdict(block) for block in section.blocks],
                }
                for section in self.sections
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Network":
        stations = tuple(
            Station(
                id=raw["id"],
                name=raw["name"],
                code=raw.get("code", raw["id"]),
                platforms=tuple(raw["platforms"]),
                x=float(raw["x"]),
                is_junction=bool(raw.get("is_junction", False)),
                platform_length_m=int(raw.get("platform_length_m", 600)),
                junction_throat_capacity=int(raw.get("junction_throat_capacity", 2)),
                platform_electrification=bool(raw.get("platform_electrification", True)),
                incompatible_route_pairs=tuple(
                    tuple(pair) for pair in raw.get("incompatible_route_pairs", ())
                ),
            )
            for raw in data["stations"]
        )
        sections = tuple(
            Section(
                id=raw["id"],
                from_station=raw["from_station"],
                to_station=raw["to_station"],
                mode=raw["mode"],
                blocks=tuple(
                    Block(
                        id=block["id"],
                        direction=block["direction"],
                        run_time_min=int(block["run_time_min"]),
                        gradient_pct=float(block.get("gradient_pct", 0.0)),
                        km_start=float(block.get("km_start", 0.0)),
                        km_end=float(block.get("km_end", 10.0)),
                        signaling_type=block.get("signaling_type", "ABSOLUTE_BLOCK"),
                    )
                    for block in raw["blocks"]
                ),
                headway_min=int(raw.get("headway_min", 3)),
                max_speed_kmph=int(raw.get("max_speed_kmph", 100)),
                distance_km=float(raw.get("distance_km", 10.0)),
                traction_type=raw.get("traction_type", "25kV_AC_ELECTRIC"),
            )
            for raw in data["sections"]
        )
        network = cls(
            id=data["id"],
            name=data["name"],
            timezone=data.get("timezone", "Asia/Kolkata"),
            stations=stations,
            sections=sections,
            label=data.get("label", "SYNTHETIC"),
        )
        network.validate()
        return network


def build_default_network() -> Network:
    """The synthetic Northern Section used by every bundled scenario.

    NDL --(single, 12 min)-- KRN --(double, 10 min)-- MLG --(single, 14 min)-- SRP
    --(double, 9 min)-- VSN
    MLG is a junction station with three platforms and reduced throat capacity.
    """
    network = Network(
        id="north-section",
        name="Northern Section (Synthetic)",
        timezone="Asia/Kolkata",
        stations=(
            Station(
                "NDL", "Nandpur Junction", "NDL", ("P1", "P2", "P3"), 0.0, True,
                platform_length_m=720, junction_throat_capacity=2,
                platform_electrification=True,
                incompatible_route_pairs=(("NDL-R1", "NDL-R2"),),
            ),
            Station("KRN", "Karanpur", "KRN", ("P1", "P2"), 1.0, platform_length_m=580),
            Station(
                "MLG", "Malgaon Junction", "MLG", ("P1", "P2", "P3"), 2.0, True,
                platform_length_m=650, junction_throat_capacity=2,
                platform_electrification=True,
                incompatible_route_pairs=(("MLG-R1", "MLG-R3"), ("MLG-R2", "MLG-R3")),
            ),
            Station("SRP", "Suryapur", "SRP", ("P1", "P2"), 3.0, platform_length_m=560),
            Station("VSN", "Vasanth Nagar", "VSN", ("P1", "P2"), 4.0, platform_length_m=600),
        ),
        sections=(
            Section(
                "S1",
                "NDL",
                "KRN",
                "SINGLE",
                (Block("B1", "BIDIRECTIONAL", 12, km_start=0.0, km_end=14.0, signaling_type="ABSOLUTE_BLOCK"),),
                headway_min=4,
                max_speed_kmph=90,
                distance_km=14.0,
                traction_type="25kV_AC_ELECTRIC",
            ),
            Section(
                "S2",
                "KRN",
                "MLG",
                "DOUBLE",
                (
                    Block("B2U", "UP", 10, km_start=14.0, km_end=32.0, signaling_type="ABSOLUTE_BLOCK"),
                    Block("B2D", "DOWN", 10, km_start=14.0, km_end=32.0, signaling_type="ABSOLUTE_BLOCK"),
                ),
                headway_min=3,
                max_speed_kmph=110,
                distance_km=18.0,
                traction_type="25kV_AC_ELECTRIC",
            ),
            Section(
                "S3",
                "MLG",
                "SRP",
                "SINGLE",
                (Block("B3", "BIDIRECTIONAL", 14, km_start=32.0, km_end=48.0, signaling_type="ABSOLUTE_BLOCK"),),
                headway_min=4,
                max_speed_kmph=90,
                distance_km=16.0,
                traction_type="25kV_AC_ELECTRIC",
            ),
            Section(
                "S4",
                "SRP",
                "VSN",
                "DOUBLE",
                (
                    Block("B4U", "UP", 9, km_start=48.0, km_end=60.0, signaling_type="ABSOLUTE_BLOCK"),
                    Block("B4D", "DOWN", 9, km_start=48.0, km_end=60.0, signaling_type="ABSOLUTE_BLOCK"),
                ),
                headway_min=3,
                max_speed_kmph=110,
                distance_km=12.0,
                traction_type="25kV_AC_ELECTRIC",
            ),
        ),
    )
    network.validate()
    return network
