# tests/test_recommend.py
"""Unit tests for the rule-based advisor (PRD Phase 2 — explain & recommend).

These exercise pure functions in backend/advisor.py — no server / httpx needed.
"""

import advisor

# ─────────────────────────────────────────
# Fixtures (plain dicts, the shape main.py hands the advisor)
# ─────────────────────────────────────────

# Classic convoy: one long job arrives with several short ones.
CONVOY = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 20, "priority": 0},
    {"pid": "P2", "arrival_time": 0, "burst_time": 2, "priority": 0},
    {"pid": "P3", "arrival_time": 0, "burst_time": 3, "priority": 0},
    {"pid": "P4", "arrival_time": 0, "burst_time": 2, "priority": 0},
]

# Uniform, short bursts — no convoy, Round-Robin-friendly.
UNIFORM = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 4, "priority": 0},
    {"pid": "P2", "arrival_time": 0, "burst_time": 4, "priority": 0},
    {"pid": "P3", "arrival_time": 0, "burst_time": 5, "priority": 0},
]

# Distinct priority levels.
PRIORITIZED = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 3},
    {"pid": "P2", "arrival_time": 0, "burst_time": 5, "priority": 1},
    {"pid": "P3", "arrival_time": 0, "burst_time": 5, "priority": 2},
]

DISK_CLUSTERED = dict(head=50, requests=[48, 52, 47, 55, 53, 49],
                      direction="right", number_of_tracks=200)
# Textbook SSTF/SCAN example.
DISK_SPREAD = dict(head=53, requests=[98, 183, 37, 122, 14, 124, 65, 67],
                   direction="right", number_of_tracks=200)


# ─────────────────────────────────────────
# analyze runners
# ─────────────────────────────────────────

def test_analyze_cpu_returns_all_algorithms_with_metrics():
    res = advisor.analyze_cpu(CONVOY)
    assert set(res) == set(advisor.CPU_ALGORITHMS)
    for metrics in res.values():
        assert {"avg_waiting_time", "avg_turnaround_time", "cpu_utilization"} <= set(metrics)


def test_analyze_cpu_does_not_mutate_input():
    before = [dict(p) for p in CONVOY]
    advisor.analyze_cpu(CONVOY)
    assert CONVOY == before


def test_analyze_cpu_quantum_changes_only_round_robin():
    # A workload where the time slice clearly affects Round Robin ordering.
    workload = [
        {"pid": "P1", "arrival_time": 0, "burst_time": 10, "priority": 0},
        {"pid": "P2", "arrival_time": 0, "burst_time": 1, "priority": 0},
        {"pid": "P3", "arrival_time": 0, "burst_time": 1, "priority": 0},
    ]
    small_q = advisor.analyze_cpu(workload, quantum=1)
    large_q = advisor.analyze_cpu(workload, quantum=10)
    # Round Robin is quantum-sensitive...
    assert small_q["round_robin"]["avg_waiting_time"] != large_q["round_robin"]["avg_waiting_time"]
    # ...while the quantum-agnostic algorithms are unaffected.
    for name in ("fcfs", "sjf_np", "sjf_pre"):
        assert small_q[name] == large_q[name]


def test_analyze_disk_returns_all_algorithms():
    res = advisor.analyze_disk(**DISK_SPREAD)
    assert set(res) == set(advisor.DISK_ALGORITHMS)
    for out in res.values():
        assert "total_head_movement" in out


def test_analyze_memory_returns_three_fit_strategies():
    procs = [
        {"pid": "P1", "size": 200, "burst_time": 3.0},
        {"pid": "P2", "size": 400, "burst_time": 2.0},
        {"pid": "P3", "size": 150, "burst_time": 4.0},
    ]
    for compaction in (False, True):
        res = advisor.analyze_memory(total_memory=500, processes=procs, compaction=compaction)
        assert set(res) == set(advisor.MEMORY_FIT_STRATEGIES)  # first/best/worst
        for metrics in res.values():
            assert {"cpu_utilization", "allocated_count", "failed_count"} <= set(metrics)
            assert metrics["allocated_count"] + metrics["failed_count"] == len(procs)


def test_analyze_vm_returns_all_algorithms_and_optimal_is_best():
    # Classic Belady reference string; Optimal should never fault more than others.
    pages = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
    res = advisor.analyze_vm(pages, frames=3)
    assert set(res) == set(advisor.VM_ALGORITHMS)
    for metrics in res.values():
        assert {"page_fault_count", "page_fault_rate"} <= set(metrics)
    optimal_faults = res["optimal"]["page_fault_count"]
    assert optimal_faults == min(m["page_fault_count"] for m in res.values())


# ─────────────────────────────────────────
# property detection
# ─────────────────────────────────────────

def _flags(properties):
    return {p["name"]: p["present"] for p in properties}


def test_convoy_effect_detected():
    assert _flags(advisor.detect_cpu_properties(CONVOY))["convoy_effect"] is True


def test_convoy_effect_absent_for_uniform_bursts():
    flags = _flags(advisor.detect_cpu_properties(UNIFORM))
    assert flags["convoy_effect"] is False
    assert flags["short_uniform_bursts"] is True


def test_priority_starvation_flag():
    assert _flags(advisor.detect_cpu_properties(PRIORITIZED))["priority_starvation_risk"] is True
    assert _flags(advisor.detect_cpu_properties(UNIFORM))["priority_starvation_risk"] is False


def test_disk_locality_vs_spread():
    assert _flags(advisor.detect_disk_properties(50, DISK_CLUSTERED["requests"], 200))["request_locality"] is True
    spread = _flags(advisor.detect_disk_properties(53, DISK_SPREAD["requests"], 200))
    assert spread["request_locality"] is False
    assert spread["wide_spread"] is True


# ─────────────────────────────────────────
# recommendation = ranking truth + justification
# ─────────────────────────────────────────

def test_recommend_cpu_matches_lowest_waiting_time():
    rec = advisor.recommend_cpu(CONVOY)
    metrics = advisor.analyze_cpu(CONVOY)
    best = min(metrics, key=lambda k: metrics[k]["avg_waiting_time"])
    assert rec["recommended"] == best
    assert rec["ranking"][0]["algorithm"] == best
    assert rec["ranking"][0]["rank"] == 1
    # convoy workload should favour a shortest-job policy
    assert rec["recommended"] in ("sjf_np", "sjf_pre")
    assert rec["justification"]


def test_recommend_cpu_ranking_is_sorted_and_complete():
    ranking = advisor.recommend_cpu(CONVOY)["ranking"]
    values = [r["metric_value"] for r in ranking]
    assert values == sorted(values)
    assert [r["rank"] for r in ranking] == list(range(1, len(ranking) + 1))
    assert len(ranking) == len(advisor.CPU_ALGORITHMS)


def test_recommend_disk_matches_lowest_head_movement():
    rec = advisor.recommend_disk(**DISK_SPREAD)
    outcomes = advisor.analyze_disk(**DISK_SPREAD)
    best = min(outcomes, key=lambda k: outcomes[k]["total_head_movement"])
    assert rec["recommended"] == best
    assert rec["ranking"][0]["algorithm"] == best
    assert rec["category"] == "disk_scheduling"
    assert rec["justification"]
