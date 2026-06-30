# advisor.py
"""
Rule-based advisor layer (PRD Phase 2 — "Explain & recommend").

Pure, transparent, testable logic with NO web/server dependencies:
  * analyze_cpu / analyze_disk  — run every algorithm in a category on one workload
                                  (the single source of truth shared with the
                                  /schedule/analyze and /disk/analyze endpoints).
  * detect_cpu_properties / detect_disk_properties — rule-based workload analysis.
  * recommend_cpu / recommend_disk — rank algorithms by the key metric, pick a
                                     winner, and build a human-readable justification.

The advisor never invents scheduling numbers; rankings come straight from the real
algorithm outputs. Detection rules are heuristics and say so in their `detail`.
"""

# CPU scheduling algorithms
from algorithms.cpu_scheduling.fcfs import fcfs
from algorithms.cpu_scheduling.sjf_nonpree import sjf_non_preemptive
from algorithms.cpu_scheduling.sjf_pree import sjf_preemptive
from algorithms.cpu_scheduling.priority_pree import priority_preemptive
from algorithms.cpu_scheduling.priority_nonpree import priority_non_preemptive
from algorithms.cpu_scheduling.round_robin import round_robin

# Disk scheduling algorithms
from algorithms.mass_storage.fcfs_disk import fcfs_disk
from algorithms.mass_storage.sstf_disk import sstf_disk
from algorithms.mass_storage.scan_disk import scan_disk
from algorithms.mass_storage.c_scan_disk import cscan_disk
from algorithms.mass_storage.look_disk import look_disk
from algorithms.mass_storage.c_look import clook_disk

# Memory management (MVT)
from algorithms.virtual_memory.mvt import mvt_with_compaction, mvt_without_compaction

# Page replacement
from algorithms.page_replacement.fifo_pra import fifo_pra
from algorithms.page_replacement.lru_pra import lru_pra
from algorithms.page_replacement.lru_approx_pra import lru_approximation_pra
from algorithms.page_replacement.optimal_pra import optimal_pra
from algorithms.page_replacement.lfu import lfu_pra
from algorithms.page_replacement.mfu import mfu_pra

CPU_ALGORITHMS = {
    "fcfs": fcfs,
    "sjf_np": sjf_non_preemptive,
    "sjf_pre": sjf_preemptive,
    "priority_np": priority_non_preemptive,
    "priority_pre": priority_preemptive,
    "round_robin": round_robin,
}

DISK_ALGORITHMS = {
    "fcfs": fcfs_disk,
    "sstf": sstf_disk,
    "scan": scan_disk,
    "cscan": cscan_disk,
    "look": look_disk,
    "clook": clook_disk,
}

# Friendly names used in justification strings.
CPU_LABELS = {
    "fcfs": "FCFS",
    "sjf_np": "SJF (non-preemptive)",
    "sjf_pre": "SJF (preemptive / SRTF)",
    "priority_np": "Priority (non-preemptive)",
    "priority_pre": "Priority (preemptive)",
    "round_robin": "Round Robin",
}
DISK_LABELS = {
    "fcfs": "FCFS",
    "sstf": "SSTF",
    "scan": "SCAN",
    "cscan": "C-SCAN",
    "look": "LOOK",
    "clook": "C-LOOK",
}

# MVT fit strategies compared side by side ("next" is excluded — the backend
# doesn't implement it distinctly; it behaves identically to first fit).
MEMORY_FIT_STRATEGIES = ("first", "best", "worst")

VM_ALGORITHMS = {
    "fifo": fifo_pra,
    "lru": lru_pra,
    "lru_approx": lru_approximation_pra,
    "optimal": optimal_pra,
    "lfu": lfu_pra,
    "mfu": mfu_pra,
}


# ─────────────────────────────────────────
# ANALYZE RUNNERS (shared with the analyze endpoints)
# ─────────────────────────────────────────

def analyze_cpu(processes, quantum=2):
    """Run every CPU algorithm on the same input; return the comparison metrics.

    `processes` is a list of plain dicts. Each algorithm may mutate its input,
    so every call gets a fresh deep-ish copy of the process dicts. `quantum` is
    the Round Robin time slice (ignored by the other algorithms).
    """
    results = {}
    for name, algorithm in CPU_ALGORITHMS.items():
        fresh = [dict(p) for p in processes]
        outcome = algorithm(fresh, quantum) if name == "round_robin" else algorithm(fresh)
        results[name] = {
            "avg_waiting_time": outcome["avg_waiting_time"],
            "avg_turnaround_time": outcome["avg_turnaround_time"],
            "cpu_utilization": outcome["cpu_utilization"],
        }
    return results


def analyze_disk(head, requests, direction, number_of_tracks):
    """Run every disk algorithm on the same input; return each full DiskResult."""
    kwargs = dict(
        head=head,
        requests=list(requests),
        direction=direction,
        number_of_tracks=number_of_tracks,
    )
    return {name: algorithm(**kwargs) for name, algorithm in DISK_ALGORITHMS.items()}


def analyze_memory(total_memory, processes, compaction):
    """Run the First/Best/Worst fit strategies on the same workload.

    `compaction` selects the with- or without-compaction MVT variant. Each
    strategy gets a fresh copy of the process dicts. Returns per-strategy
    allocation success (allocated/failed counts) and CPU utilization.
    """
    run = mvt_with_compaction if compaction else mvt_without_compaction
    results = {}
    for strategy in MEMORY_FIT_STRATEGIES:
        outcome = run({
            "total_memory": total_memory,
            "fit_strategy": strategy,
            "processes": [dict(p) for p in processes],
        })
        # With compaction, some processes are placed only on the post-compaction
        # retry pass, so both lists count as successfully allocated.
        allocated = len(outcome.get("allocated", [])) + len(outcome.get("retry_allocated", []))
        results[strategy] = {
            "cpu_utilization": outcome["cpu_utilization"],
            "allocated_count": allocated,
            "failed_count": len(outcome.get("failed", [])),
        }
    return results


def analyze_vm(pages, frames):
    """Run every page-replacement algorithm on the same reference string."""
    results = {}
    for name, algorithm in VM_ALGORITHMS.items():
        outcome = algorithm({"pages": list(pages), "frames": frames})
        results[name] = {
            "page_fault_count": outcome["page_fault_count"],
            "page_fault_rate": outcome["page_fault_rate"],
        }
    return results


# ─────────────────────────────────────────
# PROPERTY DETECTION — rule-based, transparent
# ─────────────────────────────────────────

def detect_cpu_properties(processes):
    """Detect workload properties relevant to CPU-scheduling choice."""
    bursts = [p["burst_time"] for p in processes]
    priorities = [p.get("priority", 0) for p in processes]
    arrivals = [p["arrival_time"] for p in processes]
    n = len(bursts)
    mean_burst = sum(bursts) / n
    spread = (max(bursts) - min(bursts)) / mean_burst if mean_burst else 0.0  # range / mean

    # Convoy effect: a long job arrives no later than the shortest job, so short
    # jobs queue behind it under FCFS. Require meaningful burst spread too.
    first_arrival = min(arrivals)
    earliest_bursts = [b for b, a in zip(bursts, arrivals) if a == first_arrival]
    long_arrives_early = max(earliest_bursts) >= mean_burst
    convoy = spread >= 0.5 and long_arrives_early and n > 1

    # SJF starvation: high burst spread means long jobs can be repeatedly deferred
    # behind a stream of shorter ones.
    sjf_starvation = spread >= 1.0 and n > 2

    # Priority starvation: distinct priority levels mean low-priority jobs can starve.
    priority_spread = len(set(priorities)) > 1
    pr_range = max(priorities) - min(priorities)

    # Short / uniform bursts → Round Robin gives good responsiveness with low cost.
    short_uniform = spread < 0.5 and n > 1

    return [
        {
            "name": "convoy_effect",
            "present": convoy,
            "detail": (
                f"A long burst ({max(earliest_bursts)}) arrives at the earliest time "
                f"{first_arrival}; under FCFS shorter jobs wait behind it."
                if convoy else
                "No long job blocks shorter ones at the front of the queue."
            ),
        },
        {
            "name": "sjf_starvation_risk",
            "present": sjf_starvation,
            "detail": (
                f"Burst times vary widely (range/mean ≈ {spread:.2f}); the longest job "
                "may be repeatedly preempted/deferred under SJF/SRTF."
                if sjf_starvation else
                "Burst times are similar enough that SJF starvation is unlikely."
            ),
        },
        {
            "name": "priority_starvation_risk",
            "present": priority_spread,
            "detail": (
                f"{len(set(priorities))} distinct priority levels (range {pr_range}); "
                "low-priority jobs can starve under priority scheduling."
                if priority_spread else
                "All processes share one priority, so priority starvation cannot occur."
            ),
        },
        {
            "name": "short_uniform_bursts",
            "present": short_uniform,
            "detail": (
                "Bursts are short and similar; Round Robin gives fair, responsive sharing."
                if short_uniform else
                "Bursts are not uniform; time-slicing offers less of an advantage."
            ),
        },
    ]


def detect_disk_properties(head, requests, number_of_tracks):
    """Detect workload properties relevant to disk-scheduling choice."""
    lo, hi = min(requests), max(requests)
    span = hi - lo
    disk_size = number_of_tracks if number_of_tracks else (hi + 1)
    span_ratio = span / disk_size if disk_size else 0.0

    # Locality: all requests clustered within a small fraction of the disk.
    locality = span_ratio <= 0.25 and len(requests) > 1

    # Wide spread: requests cover much of the disk, so a directional sweep
    # (SCAN/C-SCAN) amortizes travel.
    wide_spread = span_ratio >= 0.5

    # SSTF starvation: far outliers relative to the bulk can be repeatedly skipped.
    srt = sorted(requests)
    gaps = [b - a for a, b in zip(srt, srt[1:])] or [0]
    biggest_gap = max(gaps)
    outliers = len(requests) > 2 and disk_size and biggest_gap >= 0.3 * disk_size

    return [
        {
            "name": "request_locality",
            "present": locality,
            "detail": (
                f"Requests span cylinders {lo}–{hi} (~{span_ratio:.0%} of the disk); "
                "seek distances stay short, favouring SSTF/LOOK."
                if locality else
                f"Requests span {lo}–{hi} (~{span_ratio:.0%} of the disk); not tightly clustered."
            ),
        },
        {
            "name": "wide_spread",
            "present": wide_spread,
            "detail": (
                f"Requests cover ~{span_ratio:.0%} of the disk; a directional sweep "
                "(SCAN/C-SCAN) amortizes head travel."
                if wide_spread else
                "Requests do not cover much of the disk; a full sweep adds little benefit."
            ),
        },
        {
            "name": "sstf_starvation_risk",
            "present": bool(outliers),
            "detail": (
                f"A large gap ({biggest_gap} cylinders) separates outliers from the bulk; "
                "SSTF may repeatedly skip the far requests."
                if outliers else
                "No isolated far requests, so SSTF starvation is unlikely."
            ),
        },
    ]


# ─────────────────────────────────────────
# RANKING + RECOMMENDATION
# ─────────────────────────────────────────

def _rank(metrics_by_algo, metric_name, value_fn):
    """Build a rank-1-is-best list sorted ascending by the key metric."""
    rows = [
        {"algorithm": name, "metric_name": metric_name, "metric_value": float(value_fn(out))}
        for name, out in metrics_by_algo.items()
    ]
    rows.sort(key=lambda r: r["metric_value"])
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def recommend_cpu(processes, quantum=2):
    """Rank CPU algorithms by average waiting time and explain the pick."""
    metrics = analyze_cpu(processes, quantum)
    properties = detect_cpu_properties(processes)
    ranking = _rank(metrics, "avg_waiting_time", lambda m: m["avg_waiting_time"])

    best = ranking[0]
    best_key = best["algorithm"]
    flags = {p["name"]: p["present"] for p in properties}

    clauses = [
        f"{CPU_LABELS[best_key]} gives the lowest average waiting time "
        f"({best['metric_value']:.2f}) on this workload."
    ]
    if flags["convoy_effect"] and best_key in ("sjf_np", "sjf_pre"):
        clauses.append(
            "A convoy effect is present, so a shortest-job policy beats FCFS by letting "
            "short jobs finish ahead of the long one."
        )
    if flags["short_uniform_bursts"] and best_key == "round_robin":
        clauses.append("Bursts are short and uniform, so Round Robin stays fair without hurting throughput.")
    if flags["priority_starvation_risk"] and best_key in ("priority_np", "priority_pre"):
        clauses.append("Note: priority scheduling can starve low-priority jobs — consider aging.")
    if flags["sjf_starvation_risk"] and best_key in ("sjf_np", "sjf_pre"):
        clauses.append("Note: with this burst spread, the longest job may starve under SJF/SRTF.")

    return {
        "category": "cpu_scheduling",
        "detected_properties": properties,
        "ranking": ranking,
        "recommended": best_key,
        "justification": " ".join(clauses),
    }


def recommend_disk(head, requests, direction, number_of_tracks):
    """Rank disk algorithms by total head movement and explain the pick."""
    outcomes = analyze_disk(head, requests, direction, number_of_tracks)
    properties = detect_disk_properties(head, requests, number_of_tracks)
    ranking = _rank(outcomes, "total_head_movement", lambda o: o["total_head_movement"])

    best = ranking[0]
    best_key = best["algorithm"]
    flags = {p["name"]: p["present"] for p in properties}

    clauses = [
        f"{DISK_LABELS[best_key]} gives the lowest total head movement "
        f"({int(best['metric_value'])} cylinders) on this request set."
    ]
    if flags["request_locality"] and best_key in ("sstf", "look", "clook"):
        clauses.append("Requests are clustered, so a nearest-request / bounded-sweep policy keeps seeks short.")
    if flags["wide_spread"] and best_key in ("scan", "cscan"):
        clauses.append("Requests are spread across the disk, so a full directional sweep amortizes travel.")
    if best_key == "sstf" and flags["sstf_starvation_risk"]:
        clauses.append(
            "Caveat: SSTF wins on distance but can starve the far outliers here — "
            "LOOK/SCAN trade a little movement for fairness."
        )

    return {
        "category": "disk_scheduling",
        "detected_properties": properties,
        "ranking": ranking,
        "recommended": best_key,
        "justification": " ".join(clauses),
    }
