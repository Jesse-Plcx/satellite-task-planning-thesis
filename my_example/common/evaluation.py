"""Evaluation metrics for satellite task planning"""
import numpy as np


def evaluate_schedule(targetList, satResources, numSatellites, duration=86400.0):
    
    total_targets = len(targetList)
    covered_targets = sum(1 for t in targetList if t.imaged)
    coverage_rate = covered_targets / total_targets if total_targets > 0 else 0.0

    # ------------------------------------------------------------------ #
    # Accumulate per-task metrics                                          #
    # ------------------------------------------------------------------ #
    total_priority = 0.0
    total_elevation_deg = 0.0
    total_end_time = 0.0
    num_tasks = 0

    for i in range(numSatellites):
        for task in satResources[i].tasks_completed:
            targetId = task['targetId']
            priority = task.get('priority', targetList[targetId].priority)

            # Use actualElevation (midpoint estimate) for M2/M3; fall back to maxElevation if missing.
            actual_el = task.get('actualElevation', task.get('maxElevation', np.radians(45.0)))
            el_deg = np.degrees(actual_el)

            total_priority += priority
            total_elevation_deg += el_deg
            total_end_time += task['end']
            num_tasks += 1

    # ------------------------------------------------------------------ #
    # M1 – Coverage rate (already computed above)                          #
    # M2 – Weighted priority (the objective function)                      #
    # M3 – Average actual elevation                                        #
    # ------------------------------------------------------------------ #
    avg_actual_elevation_deg = total_elevation_deg / num_tasks if num_tasks > 0 else 0.0

    # PRIMARY SCORE: weighted priority (M2)
    # NOTE: coverage_rate (M1) is kept SEPARATE from weighted priority (M2).
    # Their trade-off is a scientifically meaningful result, not a problem
    # to be hidden by combining them into a single number.
    priority_score = total_priority

    # TIME COMPLETION (informational only – NOT part of the score)
    avg_end_time = total_end_time / num_tasks if num_tasks > 0 else 0.0
    time_spread_pct = (avg_end_time / duration * 100.0) if duration > 0 else 0.0

    # No per-algorithm report here; comparison table in main.py is sufficient.

    return covered_targets, priority_score, avg_actual_elevation_deg
