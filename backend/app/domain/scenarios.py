"""Synthetic scenario catalogue and timetable construction.

Every scenario is explicitly labelled SYNTHETIC. Scenario definitions are
deterministic and include a fixed seed so runs are reproducible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .network import Network, build_default_network

TRAIN_TYPES: dict[str, dict[str, Any]] = {
    "EXPRESS": {"priority": 1, "speed_factor": 0.85, "dwell_min": 1, "max_hold_min": 20},
    "PASSENGER": {"priority": 3, "speed_factor": 1.0, "dwell_min": 2, "max_hold_min": 30},
    "MEMU": {"priority": 4, "speed_factor": 1.0, "dwell_min": 1, "max_hold_min": 25},
    "FREIGHT": {"priority": 5, "speed_factor": 1.25, "dwell_min": 2, "max_hold_min": 45},
}


@dataclass(frozen=True)
class TrainSpec:
    id: str
    name: str
    train_type: str
    origin: str
    destination: str
    scheduled_departure_min: int
    initial_delay_min: int = 0

    @property
    def priority(self) -> int:
        return int(TRAIN_TYPES[self.train_type]["priority"])

    @property
    def dwell_min(self) -> int:
        return int(TRAIN_TYPES[self.train_type]["dwell_min"])

    @property
    def max_hold_min(self) -> int:
        return int(TRAIN_TYPES[self.train_type]["max_hold_min"])

    @property
    def speed_factor(self) -> float:
        return float(TRAIN_TYPES[self.train_type]["speed_factor"])


@dataclass(frozen=True)
class ClosureSpec:
    block_id: str
    start_min: int
    end_min: int
    reason: str


@dataclass(frozen=True)
class PlatformOutageSpec:
    station_id: str
    platform_id: str
    start_min: int
    end_min: int
    reason: str


@dataclass(frozen=True)
class ScenarioSpec:
    key: str
    name: str
    description: str
    start_time_min: int
    seed: int
    trains: tuple[TrainSpec, ...]
    closures: tuple[ClosureSpec, ...] = ()
    platform_outages: tuple[PlatformOutageSpec, ...] = ()
    label: str = "SYNTHETIC"


def _t(
    train_id: str,
    name: str,
    train_type: str,
    origin: str,
    destination: str,
    departure: str,
    initial_delay_min: int = 0,
) -> TrainSpec:
    hours, minutes = (int(part) for part in departure.split(":"))
    return TrainSpec(
        id=train_id,
        name=name,
        train_type=train_type,
        origin=origin,
        destination=destination,
        scheduled_departure_min=hours * 60 + minutes,
        initial_delay_min=initial_delay_min,
    )


SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        key="normal_traffic",
        name="Normal traffic — balanced timetable",
        description=(
            "Four trains in both directions with one planned single-line crossing. "
            "Use this scenario to inspect the baseline decision workflow."
        ),
        start_time_min=6 * 60,
        seed=42,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:04"),
            _t("61042", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:09"),
            _t("FRT-701", "Vasanth Freight", "FREIGHT", "VSN", "NDL", "06:14"),
        ),
    ),
    ScenarioSpec(
        key="evening_peak",
        name="Evening peak — high traffic",
        description=(
            "Eight trains converge on the single-line sections within a short window. "
            "Expect several simultaneous crossing and platform conflicts."
        ),
        start_time_min=17 * 60,
        seed=77,
        trains=(
            _t("12951", "Capital Express", "EXPRESS", "NDL", "VSN", "17:00"),
            _t("12626", "Nandpur Express Down", "EXPRESS", "VSN", "NDL", "17:02"),
            _t("51832", "Karanpur Passenger Up", "PASSENGER", "NDL", "SRP", "17:03"),
            _t("51833", "Suryapur Passenger Down", "PASSENGER", "VSN", "NDL", "17:05"),
            _t("61043", "Malgaon MEMU Down", "MEMU", "VSN", "MLG", "17:07"),
            _t("61044", "Nandpur MEMU Up", "MEMU", "NDL", "VSN", "17:08"),
            _t("FRT-702", "Suryapur Freight", "FREIGHT", "NDL", "VSN", "17:10"),
            _t("FRT-703", "Karanpur Freight Down", "FREIGHT", "VSN", "NDL", "17:12"),
        ),
    ),
    ScenarioSpec(
        key="single_line_meet",
        name="Single-line meet",
        description=(
            "Two opposing trains require the same single-line block at the same time. "
            "A precedence or holding decision is required."
        ),
        start_time_min=6 * 60,
        seed=7,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:00"),
        ),
    ),
    ScenarioSpec(
        key="delayed_express",
        name="Delayed express",
        description=(
            "A premium express starts 22 minutes late while a freight service is "
            "already approaching the single-line section."
        ),
        start_time_min=6 * 60,
        seed=11,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00", 22),
            _t("FRT-701", "Vasanth Freight", "FREIGHT", "VSN", "NDL", "06:02"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:06"),
        ),
    ),
    ScenarioSpec(
        key="block_closure",
        name="Temporary block closure — infeasible window",
        description=(
            "The MLG–SRP single-line block is closed for 70 minutes. Trains that "
            "must use it have no alternative route in this topology."
        ),
        start_time_min=6 * 60,
        seed=23,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:02"),
            _t("61042", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:04"),
        ),
        closures=(
            ClosureSpec("B3", 6 * 60 + 5, 7 * 60 + 15, "Engineering block — track renewal"),
        ),
    ),
    ScenarioSpec(
        key="platform_outage",
        name="Platform outage at Malgaon Junction",
        description=(
            "Two of three platforms at MLG are unavailable, reducing platform capacity "
            "while three trains are due in the same window."
        ),
        start_time_min=6 * 60,
        seed=31,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:00"),
            _t("61042", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:03"),
        ),
        platform_outages=(
            PlatformOutageSpec("MLG", "P1", 5 * 60 + 45, 7 * 60, "Platform resurfacing"),
            PlatformOutageSpec("MLG", "P2", 5 * 60 + 45, 7 * 60, "Platform resurfacing"),
        ),
    ),
    ScenarioSpec(
        key="priority_train",
        name="Priority train conflict",
        description=(
            "A late premium express conflicts with a freight already occupying the "
            "single-line section. The priority policy is a soft operational input, "
            "not a safety override."
        ),
        start_time_min=6 * 60,
        seed=53,
        trains=(
            _t("12951", "Capital Express", "EXPRESS", "NDL", "VSN", "06:00", 15),
            _t("FRT-704", "Nandpur Freight", "FREIGHT", "NDL", "VSN", "06:00"),
            _t("51834", "Suryapur Passenger", "PASSENGER", "VSN", "NDL", "06:01"),
        ),
    ),
    ScenarioSpec(
        key="no_feasible_schedule",
        name="No feasible schedule — extended single-line closure",
        description=(
            "The MLG–SRP single-line block is closed beyond the planning horizon. "
            "No diversion exists and waiting exceeds the configured hold policy, so "
            "the optimizer must report no feasible schedule rather than invent one."
        ),
        start_time_min=6 * 60,
        seed=91,
        trains=(
            _t("12625", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51831", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:01"),
            _t("61042", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:03"),
        ),
        closures=(
            ClosureSpec("B3", 6 * 60 + 5, 12 * 60, "Extended engineering possession"),
        ),
    ),
)

SCENARIO_MAP = {scenario.key: scenario for scenario in SCENARIOS}


def scenario_catalogue() -> list[dict]:
    return [
        {
            "key": scenario.key,
            "name": scenario.name,
            "description": scenario.description,
            "start_time_min": scenario.start_time_min,
            "seed": scenario.seed,
            "train_count": len(scenario.trains),
            "closure_count": len(scenario.closures),
            "platform_outage_count": len(scenario.platform_outages),
            "label": scenario.label,
        }
        for scenario in SCENARIOS
    ]


def build_train(spec: TrainSpec, network: Network) -> dict:
    """Build a train record with a deterministic timetable for its route."""
    direction = network.direction_for(spec.origin, spec.destination)
    route = network.route_stations(spec.origin, spec.destination)
    segments = network.segments(route, direction)

    schedule: list[dict] = []
    cursor = spec.scheduled_departure_min
    schedule.append(
        {
            "station_id": route[0],
            "arrival_min": None,
            "departure_min": cursor,
            "run_from_previous_min": 0,
            "block_id": None,
            "section_id": None,
        }
    )
    for index, (section, block) in enumerate(segments):
        run_min = max(1, int(round(block.run_time_min * spec.speed_factor)))
        arrival = cursor + run_min
        is_destination = index == len(segments) - 1
        departure = None if is_destination else arrival + spec.dwell_min
        schedule.append(
            {
                "station_id": route[index + 1],
                "arrival_min": arrival,
                "departure_min": departure,
                "run_from_previous_min": run_min,
                "block_id": block.id,
                "section_id": section.id,
            }
        )
        if departure is not None:
            cursor = departure

    initial_delay = spec.initial_delay_min
    return {
        "id": spec.id,
        "name": spec.name,
        "train_type": spec.train_type,
        "priority": spec.priority,
        "max_hold_min": spec.max_hold_min,
        "dwell_min": spec.dwell_min,
        "direction": direction,
        "origin": spec.origin,
        "destination": spec.destination,
        "route": route,
        "schedule": schedule,
        "initial_delay_min": initial_delay,
        "scheduled_departure_min": spec.scheduled_departure_min,
        "label": "SYNTHETIC",
    }


def build_scenario(key: str, network: Network | None = None) -> dict:
    if key not in SCENARIO_MAP:
        raise KeyError(f"Unknown scenario '{key}'")
    spec = SCENARIO_MAP[key]
    network = network or build_default_network()
    trains = [build_train(train, network) for train in spec.trains]
    return {
        "scenario_key": spec.key,
        "scenario_name": spec.name,
        "description": spec.description,
        "start_time_min": spec.start_time_min,
        "seed": spec.seed,
        "label": spec.label,
        "network": network.to_dict(),
        "trains": trains,
        "closures": [asdict(closure) for closure in spec.closures],
        "platform_outages": [asdict(outage) for outage in spec.platform_outages],
    }
