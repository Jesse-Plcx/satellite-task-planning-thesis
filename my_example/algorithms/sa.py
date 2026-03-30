"""Simulated annealing for satellite task planning."""
import random
from copy import deepcopy

import numpy as np

from .genetic import TaskSchedule, _build_task_pool


def _clone_schedule(schedule):
    cloned = TaskSchedule(schedule.numSatellites, schedule.numTargets)
    cloned.genes = schedule.genes[:]
    cloned.fitness = schedule.fitness
    cloned.coverage = schedule.coverage
    cloned.feasible = schedule.feasible
    return cloned


def _remove_duplicate_targets(genes):
    seen_targets = set()
    unique_genes = []
    for gene in genes:
        target_id = gene[1]
        if target_id not in seen_targets:
            seen_targets.add(target_id)
            unique_genes.append(gene)
    return unique_genes


def _quality_sorted_pool(task_pool, task_quality):
    return sorted(task_pool, key=lambda gene: task_quality[gene], reverse=True)


def _estimate_initial_temperature(base_schedule, task_pool, task_quality, accessWindows,
                                  targetList, satResources, numTargets, seed,
                                  target_acceptance=0.7, sample_count=40,
                                  final_temperature=0.05):
    """Estimate a reasonable initial temperature from sampled downhill moves."""
    probe_rng = random.Random(seed + 1009)
    downhill_magnitudes = []
    all_magnitudes = []

    for _ in range(sample_count):
        candidate = _generate_neighbor(base_schedule, task_pool, task_quality, probe_rng)
        candidate.calculate_fitness(accessWindows, targetList, satResources)
        delta = candidate.fitness - base_schedule.fitness
        if delta < 0:
            downhill_magnitudes.append(-delta)
        if delta != 0:
            all_magnitudes.append(abs(delta))

    if downhill_magnitudes:
        reference_delta = float(np.mean(downhill_magnitudes))
    elif all_magnitudes:
        reference_delta = float(np.mean(all_magnitudes))
    else:
        reference_delta = 100.0 / max(1, numTargets)

    temperature = reference_delta / max(-np.log(target_acceptance), 1e-9)
    return max(temperature, final_temperature * 5.0)


def _generate_neighbor(schedule, task_pool, task_quality, rng):
    """Create a neighboring solution using quality-aware local edits."""
    neighbor = _clone_schedule(schedule)
    current_targets = set(gene[1] for gene in neighbor.genes)

    if not neighbor.genes:
        top_count = min(10, len(task_pool))
        neighbor.genes = _quality_sorted_pool(task_pool, task_quality)[:top_count]
        return neighbor

    move = rng.choices(
        ["replace", "add", "remove", "swap_window", "swap_satellite"],
        weights=[0.35, 0.25, 0.15, 0.15, 0.10],
        k=1
    )[0]

    if move == "replace":
        idx = rng.randrange(len(neighbor.genes))
        old_gene = neighbor.genes[idx]
        current_targets.discard(old_gene[1])
        candidates = [gene for gene in task_pool if gene[1] not in current_targets]
        if candidates:
            top_k = max(1, len(candidates) // 5)
            ranked = sorted(candidates, key=lambda gene: task_quality[gene], reverse=True)[:top_k]
            neighbor.genes[idx] = rng.choice(ranked)

    elif move == "add":
        candidates = [gene for gene in task_pool if gene[1] not in current_targets]
        if candidates:
            ranked = sorted(candidates, key=lambda gene: task_quality[gene], reverse=True)
            top_k = max(1, min(len(ranked), len(ranked) // 4 or 1))
            num_add = rng.randint(1, min(3, top_k))
            for gene in rng.sample(ranked[:top_k], num_add):
                neighbor.genes.append(gene)
                current_targets.add(gene[1])

    elif move == "remove" and neighbor.genes:
        ranked = sorted(neighbor.genes, key=lambda gene: task_quality.get(gene, 0.0))
        remove_gene = rng.choice(ranked[:max(1, min(3, len(ranked)))])
        neighbor.genes.remove(remove_gene)

    elif move == "swap_window" and neighbor.genes:
        idx = rng.randrange(len(neighbor.genes))
        sat_id, target_id, window_idx = neighbor.genes[idx]
        same_pair_candidates = [
            gene for gene in task_pool
            if gene[0] == sat_id and gene[1] == target_id and gene[2] != window_idx
        ]
        if same_pair_candidates:
            neighbor.genes[idx] = rng.choice(same_pair_candidates)

    elif move == "swap_satellite" and neighbor.genes:
        idx = rng.randrange(len(neighbor.genes))
        sat_id, target_id, _ = neighbor.genes[idx]
        alt_sat_candidates = [
            gene for gene in task_pool
            if gene[1] == target_id and gene[0] != sat_id
        ]
        if alt_sat_candidates:
            neighbor.genes[idx] = rng.choice(alt_sat_candidates)

    neighbor.genes = _remove_duplicate_targets(neighbor.genes)
    return neighbor


def simulated_annealing_task_planning(accessWindows, targetList, satResources, numSatellites, numTargets,
                                      initialTemperature=None, finalTemperature=0.05,
                                      coolingRate=0.97, iterationsPerTemp=40, seed=42):
    """Simulated annealing using the same task encoding as the genetic algorithm."""
    random.seed(seed)
    np.random.seed(seed)
    rng = random.Random(seed)

    taskPool, taskQuality = _build_task_pool(accessWindows, targetList, satResources)
    if not taskPool:
        print("No candidate tasks found. SA exits without scheduling.")
        return None

    sorted_pool = _quality_sorted_pool(taskPool, taskQuality)
    initial_gene_count = min(max(numTargets // 3, numSatellites * 5), len(sorted_pool))

    current = TaskSchedule(numSatellites, numTargets)
    current.genes = sorted_pool[:initial_gene_count]
    current.calculate_fitness(accessWindows, targetList, satResources)

    if initialTemperature is None:
        initialTemperature = _estimate_initial_temperature(
            current, taskPool, taskQuality, accessWindows,
            targetList, satResources, numTargets, seed,
            target_acceptance=0.7,
            sample_count=max(30, min(80, len(taskPool) // 10 if len(taskPool) > 0 else 30)),
            final_temperature=finalTemperature
        )
        auto_temp = True
    else:
        initialTemperature = float(initialTemperature)
        auto_temp = False

    if initialTemperature <= finalTemperature:
        initialTemperature = max(finalTemperature * 5.0, finalTemperature + 1e-6)

    print("\n=== Starting Simulated Annealing ===")
    print(
        f"Initial T: {initialTemperature:.3f}"
        f"{' (auto-calibrated)' if auto_temp else ''}, "
        f"Final T: {finalTemperature}, Cooling: {coolingRate}, "
        f"Iter/Temp: {iterationsPerTemp}, Seed: {seed}"
    )

    best = deepcopy(current)
    temperature = float(initialTemperature)
    temperature_step = 0

    while temperature > finalTemperature:
        for _ in range(iterationsPerTemp):
            candidate = _generate_neighbor(current, taskPool, taskQuality, rng)
            candidate.calculate_fitness(accessWindows, targetList, satResources)

            delta = candidate.fitness - current.fitness
            if delta >= 0:
                current = candidate
            else:
                acceptance_prob = np.exp(delta / max(temperature, 1e-9))
                if rng.random() < acceptance_prob:
                    current = candidate

            if current.fitness > best.fitness:
                best = deepcopy(current)

        temperature *= coolingRate
        temperature_step += 1
        if temperature_step % 10 == 0:
            print(
                f"T step {temperature_step}: T={temperature:.3f}, "
                f"Current={current.coverage}/{numTargets} ({current.fitness:.2f}), "
                f"Best={best.coverage}/{numTargets} ({best.fitness:.2f})"
            )

    print("\n=== Annealing Summary ===")
    print(f"Best coverage: {best.coverage}/{numTargets}")
    print(f"Best genes: {len(best.genes)} tasks")

    print("\n=== Applying Best Solution ===")
    best.apply_solution(accessWindows, targetList, satResources)

    covered = sum(1 for target in targetList if target.imaged)
    coverage = (covered / len(targetList)) * 100 if targetList else 0.0
    print(f"✓ Final coverage: {covered}/{len(targetList)} ({coverage:.1f}%)")
    print(f"✓ Scheduled tasks: {len(best.genes)}")

    return None
