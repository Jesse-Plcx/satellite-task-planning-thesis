"""Earliest Window First (EWF) baseline greedy algorithm."""
import numpy as np


def _estimate_midpoint_elevation(task, sat, actual_start):
    """Estimate actual elevation at imaging midpoint using the shared project convention."""
    min_elev_rad = np.radians(15.0)
    t_mid = actual_start + sat.imaging_time / 2.0
    t_peak = (task['windowStart'] + task['windowEnd']) / 2.0
    half_window = (task['windowEnd'] - task['windowStart']) / 2.0
    position_factor = (
        max(0.0, 1.0 - ((t_mid - t_peak) / half_window) ** 2)
        if half_window > 0 else 1.0
    )
    return min_elev_rad + (task['maxElevation'] - min_elev_rad) * position_factor


def earliest_window_first_task_planning(accessWindows, targetList, satResources, numSatellites, numTargets,
                                        duration=86400.0):
    """Baseline greedy scheduler: prioritize the earliest feasible access window."""
    print("\n=== Starting Earliest Window First (EWF) ===")

    task_pool = []
    for (satId, targetId), windows in accessWindows.items():
        for window_data in windows:
            if len(window_data) != 5:
                raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
            windowStart, windowEnd, windowDuration, maxElevation, minRange = window_data
            task_pool.append({
                'satId': satId,
                'targetId': targetId,
                'windowStart': windowStart,
                'windowEnd': windowEnd,
                'duration': windowDuration,
                'priority': targetList[targetId].priority,
                'maxElevation': maxElevation,
                'minRange': minRange
            })

    task_pool.sort(key=lambda task: (task['windowStart'], task['windowEnd'], -task['priority']))
    print(f"Task pool: {len(task_pool)} candidate tasks")

    scheduled_tasks = []
    for task in task_pool:
        sat = satResources[task['satId']]
        target = targetList[task['targetId']]

        if target.imaged:
            continue
        if sat.storage_used + sat.image_size > sat.storage_capacity:
            continue

        if sat.tasks_completed:
            earliest_start = sat.tasks_completed[-1]['end'] + sat.slew_time
        else:
            earliest_start = 0.0

        actual_start = max(task['windowStart'], earliest_start)
        actual_end = actual_start + sat.imaging_time
        if actual_end > task['windowEnd']:
            continue

        actual_elev_rad = _estimate_midpoint_elevation(task, sat, actual_start)

        sat.tasks_completed.append({
            'targetId': task['targetId'],
            'start': actual_start,
            'end': actual_end,
            'window': (task['windowStart'], task['windowEnd']),
            'maxElevation': task['maxElevation'],
            'actualElevation': actual_elev_rad,
            'priority': target.priority
        })
        sat.storage_used += sat.image_size
        target.imaged = True
        scheduled_tasks.append(task)

    covered = sum(1 for target in targetList if target.imaged)
    coverage = (covered / len(targetList)) * 100 if targetList else 0.0
    print(f"✓ Scheduled {len(scheduled_tasks)} tasks")
    print(f"✓ Coverage: {covered}/{len(targetList)} ({coverage:.1f}%)")
    return None
