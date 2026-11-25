"""Synthetic scenario catalogue and timetable construction.

Every scenario is explicitly labelled SYNTHETIC. Scenario definitions are
deterministic and include a fixed seed so runs are reproducible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .network import Network, build_default_network

TRAIN_TYPES: dict[str, dict[str, Any]] = {
    "EXPRESS": {
        "priority": 1,
        "speed_factor": 0.85,
        "dwell_min": 1,
        "max_hold_min": 20,
        "category": "PREMIUM_PASSENGER",
        "max_speed_kmph": 130,
        "platform_requirement": 1,
    },
    "PASSENGER": {
        "priority": 3,
        "speed_factor": 1.0,
        "dwell_min": 2,
        "max_hold_min": 30,
        "category": "ORDINARY_PASSENGER",
        "max_speed_kmph": 100,
        "platform_requirement": 1,
    },
    "MEMU": {
        "priority": 4,
        "speed_factor": 1.0,
        "dwell_min": 1,
        "max_hold_min": 25,
        "category": "SUBURBAN",
        "max_speed_kmph": 90,
        "platform_requirement": 1,
    },
    "FREIGHT": {
        "priority": 5,
        "speed_factor": 1.25,
        "dwell_min": 2,
        "max_hold_min": 45,
        "category": "GOODS",
        "max_speed_kmph": 75,
        "platform_requirement": 1,
    },
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

    @property
    def category(self) -> str:
        return str(TRAIN_TYPES[self.train_type]["category"])

    @property
    def max_speed_kmph(self) -> int:
        return int(TRAIN_TYPES[self.train_type]["max_speed_kmph"])


@dataclass(frozen=True)
class DisruptionSpec:
    """A scenario-level disruption applied when the simulation is created.

    ``kind`` is one of BLOCK_CLOSURE, SECTION_CLOSURE, PLATFORM_OUTAGE,
    TRAIN_DELAY or SPEED_RESTRICTION. The disruption is materialised into the
    state so the conflict engine, validator and optimizer all see the same
    evidence.
    """

    id: str
    kind: str
    target: str
    start_min: int
    duration_min: int
    magnitude: int = 0
    reason: str = ""


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
    disruptions: tuple[DisruptionSpec, ...] = ()
    service_pattern: str = "MIXED"
    tags: tuple[str, ...] = ()
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
    ScenarioSpec(
        key="double_line_overtaking",
        name="Double-line overtaking",
        description=(
            "A premium express catches a slower freight on the double-line section. "
            "The express can only overtake where a platform loop or a later block "
            "window allows it; the conflict engine reports the projected overtaking."
        ),
        start_time_min=6 * 60,
        seed=101,
        service_pattern="MIXED",
        tags=("overtaking", "double_line", "priority"),
        trains=(
            _t("FRT-801", "Nandpur Goods", "FREIGHT", "NDL", "VSN", "06:00"),
            _t("12952", "Capital Express", "EXPRESS", "NDL", "VSN", "06:03"),
            _t("51835", "Vasanth Passenger", "PASSENGER", "VSN", "NDL", "06:05"),
        ),
    ),
    ScenarioSpec(
        key="junction_congestion",
        name="Junction congestion at Malgaon",
        description=(
            "Five trains converge on Malgaon Junction within a short window from "
            "both directions. The junction throat and platform capacity are the "
            "binding resources."
        ),
        start_time_min=6 * 60,
        seed=113,
        service_pattern="PEAK",
        tags=("junction", "platform", "congestion"),
        trains=(
            _t("12627", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51836", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:00"),
            _t("61045", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:01"),
            _t("61046", "Suryapur MEMU", "MEMU", "VSN", "MLG", "06:02"),
            _t("FRT-802", "Malgaon Freight", "FREIGHT", "NDL", "VSN", "06:03"),
        ),
    ),
    ScenarioSpec(
        key="maintenance_window",
        name="Planned maintenance window",
        description=(
            "A short planned possession closes the UP block of the SRP–VSN double "
            "line. Trains can be held or re-sequenced within policy; the optimizer "
            "must respect the possession exactly."
        ),
        start_time_min=6 * 60,
        seed=127,
        service_pattern="MIXED",
        tags=("maintenance", "closure", "double_line"),
        trains=(
            _t("12628", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51837", "Karanpur Passenger", "PASSENGER", "NDL", "VSN", "06:03"),
            _t("61047", "Malgaon MEMU", "MEMU", "NDL", "VSN", "06:06"),
        ),
        closures=(
            ClosureSpec("B4U", 6 * 60 + 12, 6 * 60 + 32, "Planned track maintenance"),
        ),
    ),
    ScenarioSpec(
        key="cascading_delay",
        name="Cascading delay",
        description=(
            "A premium express starts 35 minutes late and is followed by three "
            "services. Delay propagates through block and platform contention, "
            "allowing cascading-delay evidence to be inspected."
        ),
        start_time_min=6 * 60,
        seed=139,
        service_pattern="PEAK",
        tags=("delay", "cascading", "priority"),
        trains=(
            _t("12953", "Capital Express", "EXPRESS", "NDL", "VSN", "06:00", 35),
            _t("51838", "Karanpur Passenger", "PASSENGER", "NDL", "VSN", "06:04"),
            _t("61048", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:08"),
            _t("FRT-803", "Vasanth Freight", "FREIGHT", "VSN", "NDL", "06:02"),
        ),
    ),
    ScenarioSpec(
        key="disruption_recovery",
        name="Disruption recovery",
        description=(
            "An unplanned signal failure closes the UP block of KRN–MLG while a "
            "platform at MLG is out of service. Recovery requires re-sequencing "
            "within the configured hold policy."
        ),
        start_time_min=6 * 60,
        seed=151,
        service_pattern="MIXED",
        tags=("disruption", "recovery", "closure", "platform"),
        trains=(
            _t("12629", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51839", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:01"),
            _t("61049", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:04"),
            _t("FRT-804", "Suryapur Freight", "FREIGHT", "NDL", "VSN", "06:06"),
        ),
        platform_outages=(
            PlatformOutageSpec("MLG", "P3", 6 * 60, 6 * 60 + 40, "Signal equipment outage"),
        ),
        disruptions=(
            DisruptionSpec(
                "DIS-001",
                "BLOCK_CLOSURE",
                "B2U",
                6 * 60 + 6,
                18,
                reason="Unplanned signal failure",
            ),
        ),
    ),
    ScenarioSpec(
        key="time_varying_demand",
        name="Time-varying demand",
        description=(
            "Eight mixed-category services are released over a twenty-eight-minute "
            "window, producing time-varying block and platform occupancy rather "
            "than a single instantaneous conflict."
        ),
        start_time_min=6 * 60,
        seed=163,
        service_pattern="PEAK",
        tags=("demand", "occupancy", "mixed"),
        trains=(
            _t("12630", "Nandpur Express", "EXPRESS", "NDL", "VSN", "06:00"),
            _t("51840", "Karanpur Passenger", "PASSENGER", "VSN", "NDL", "06:04"),
            _t("61050", "Malgaon MEMU", "MEMU", "NDL", "SRP", "06:08"),
            _t("FRT-805", "Nandpur Freight", "FREIGHT", "NDL", "VSN", "06:12"),
            _t("51841", "Suryapur Passenger", "PASSENGER", "VSN", "NDL", "06:16"),
            _t("61051", "Vasanth MEMU", "MEMU", "VSN", "NDL", "06:20"),
            _t("12631", "Capital Express", "EXPRESS", "VSN", "NDL", "06:24"),
            _t("FRT-806", "Karanpur Freight", "FREIGHT", "VSN", "NDL", "06:28"),
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
            "disruption_count": len(scenario.disruptions),
            "service_pattern": scenario.service_pattern,
            "tags": list(scenario.tags),
            "train_categories": sorted({train.train_type for train in scenario.trains}),
            "label": scenario.label,
        }
        for scenario in SCENARIOS
    ]


def _materialise_disruptions(
    spec: ScenarioSpec,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Translate scenario disruptions into concrete closures/outages/restrictions."""
    closures = [asdict(closure) for closure in spec.closures]
    outages = [asdict(outage) for outage in spec.platform_outages]
    restrictions: list[dict] = []
    for disruption in spec.disruptions:
        end_min = disruption.start_min + disruption.duration_min
        record = {
            "id": disruption.id,
            "kind": disruption.kind,
            "target": disruption.target,
            "start_min": disruption.start_min,
            "end_min": end_min,
            "magnitude": disruption.magnitude,
            "reason": disruption.reason,
        }
        if disruption.kind == "BLOCK_CLOSURE":
            closures.append(
                {
                    "block_id": disruption.target,
                    "start_min": disruption.start_min,
                    "end_min": end_min,
                    "reason": disruption.reason or "Scenario disruption",
                    "source": "SCENARIO_DISRUPTION",
                    "disruption_id": disruption.id,
                }
            )
        elif disruption.kind == "SECTION_CLOSURE":
            for block_id in disruption.target.split(","):
                closures.append(
                    {
                        "block_id": block_id.strip(),
                        "start_min": disruption.start_min,
                        "end_min": end_min,
                        "reason": disruption.reason or "Scenario disruption",
                        "source": "SCENARIO_DISRUPTION",
                        "disruption_id": disruption.id,
                    }
                )
        elif disruption.kind == "PLATFORM_OUTAGE":
            station_id, _, platform_id = disruption.target.partition("/")
            outages.append(
                {
                    "station_id": station_id,
                    "platform_id": platform_id,
                    "start_min": disruption.start_min,
                    "end_min": end_min,
                    "reason": disruption.reason or "Scenario disruption",
                    "source": "SCENARIO_DISRUPTION",
                    "disruption_id": disruption.id,
                }
            )
        elif disruption.kind == "SPEED_RESTRICTION":
            restrictions.append(record)
        elif disruption.kind != "TRAIN_DELAY":
            raise ValueError(f"Unknown scenario disruption kind '{disruption.kind}'")
    return closures, outages, restrictions


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
        "category": spec.category,
        "max_speed_kmph": spec.max_speed_kmph,
        "priority": spec.priority,
        "max_hold_min": spec.max_hold_min,
        "dwell_min": spec.dwell_min,
        "speed_factor": spec.speed_factor,
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
    closures, outages, restrictions = _materialise_disruptions(spec)
    trains = [build_train(train, network) for train in spec.trains]
    # Scenario-level TRAIN_DELAY disruptions add to the scheduled departure.
    for train in trains:
        for disruption in spec.disruptions:
            if disruption.kind == "TRAIN_DELAY" and disruption.target == train["id"]:
                train["initial_delay_min"] = int(train["initial_delay_min"]) + int(
                    disruption.magnitude
                )
    return {
        "scenario_key": spec.key,
        "scenario_name": spec.name,
        "description": spec.description,
        "start_time_min": spec.start_time_min,
        "seed": spec.seed,
        "service_pattern": spec.service_pattern,
        "tags": list(spec.tags),
        "label": spec.label,
        "network": network.to_dict(),
        "trains": trains,
        "closures": closures,
        "platform_outages": outages,
        "speed_restrictions": restrictions,
        "disruptions": [
            {
                **asdict(disruption),
                "end_min": disruption.start_min + disruption.duration_min,
            }
            for disruption in spec.disruptions
        ],
    }
