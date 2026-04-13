"""Greedy task planning algorithm"""
import numpy as np


def greedy_task_planning(accessWindows, targetList, satResources, numSatellites, numTargets, duration=86400.0):
    print("\n=== Starting Greedy Task Planning ===")

    def compute_timing(task, sat):
        if sat.tasks_completed:
            last_task = sat.tasks_completed[-1]
            earliest_start = last_task['end'] + sat.slew_time
        else:
            earliest_start = 0.0
        actual_start = max(task['windowStart'], earliest_start)
        actual_end = actual_start + sat.imaging_time
        return earliest_start, actual_start, actual_end

    def estimate_midpoint_elevation(task, sat, actual_start):
        min_elev_rad = np.radians(15.0)
        t_mid = actual_start + sat.imaging_time / 2.0
        t_peak = (task['windowStart'] + task['windowEnd']) / 2.0
        half_window = (task['windowEnd'] - task['windowStart']) / 2.0
        position_factor = (max(0.0, 1.0 - ((t_mid - t_peak) / half_window) ** 2)
                           if half_window > 0 else 1.0)
        return min_elev_rad + (task['maxElevation'] - min_elev_rad) * position_factor
    
    # Step 1: Build task pool
    taskPool = []
    # accessWindows: dict[tuple[int, int], list[tuple[float, float, float, float, float]]]
    # Key: (satId, targetId)
    # windows: list[tuple]
    # window_data: tuple[start, end, duration, maxElevation, minRange]
    for (satId, targetId), windows in accessWindows.items():
        for window_data in windows:        
            if len(window_data) != 5:
                raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
            windowStart, windowEnd, windowDuration, maxElevation, minRange = window_data
            
            taskPool.append({
                'satId': satId,
                'targetId': targetId,
                'windowStart': windowStart,
                'windowEnd': windowEnd,
                'duration': windowDuration,
                'priority': targetList[targetId].priority,
                'maxElevation': maxElevation,
                'minRange': minRange  # (not used in value function)
            })
    
    print(f"Task pool: {len(taskPool)} potential tasks with quality metrics")
    
    # Step 2: Greedy scheduling

    current_time = {i: 0.0 for i in range(numSatellites)}
    scheduledTasks = []
    
    while taskPool:

        best_task = None
        best_value = -np.inf
        best_timing = None
        best_estimated_elev_rad = None
        
        for task in taskPool:
            sat_id = task['satId']
            target_id = task['targetId']
            sat = satResources[sat_id]
            target = targetList[target_id]
            
            if target.imaged:
                continue
            
            if sat.storage_used + sat.image_size > sat.storage_capacity:
                continue
            
            earliest_start, actual_start, actual_end = compute_timing(task, sat)
            if actual_end > task['windowEnd']:
                continue
            
            time_to_start = actual_start - earliest_start
            time_decay = 1800.0  # τ_d: value halves when wait equals this

            estimated_elev_rad = estimate_midpoint_elevation(task, sat, actual_start)
            elevation_deg = np.degrees(estimated_elev_rad)
            elevation_bonus = 0.3 * min(elevation_deg / 90.0, 1.0)

            value = (task['priority'] + elevation_bonus) / (1 + time_to_start / time_decay)
            
            if value > best_value:
                best_value = value
                best_task = task
                best_timing = (earliest_start, actual_start, actual_end)
                best_estimated_elev_rad = estimated_elev_rad
        
        if best_task is None:
            # No more valid tasks
            break
        
        # Schedule the best task
        sat_id = best_task['satId']
        target_id = best_task['targetId']
        sat = satResources[sat_id]
        target = targetList[target_id]
        
        _, actual_start, actual_end = best_timing
        actual_elev_rad = best_estimated_elev_rad

        # Execute task
        sat.tasks_completed.append({
            'targetId':        target_id,
            'start':           actual_start,
            'end':             actual_end,
            'window':          (best_task['windowStart'], best_task['windowEnd']),
            'maxElevation':    best_task['maxElevation'],   # window peak [rad]
            'actualElevation': actual_elev_rad,             # midpoint estimate [rad]
            'priority':        target.priority
        })
        sat.storage_used += sat.image_size
        target.imaged = True
        
        scheduledTasks.append(best_task)
        taskPool.remove(best_task)
        
        current_time[sat_id] = actual_end
    
    covered = sum(1 for target in targetList if target.imaged)
    coverage = (covered / len(targetList)) * 100
    
    print(f"✓ Scheduled {len(scheduledTasks)} tasks")
    print(f"✓ Coverage: {covered}/{len(targetList)} ({coverage:.1f}%)")
    
    return None 
