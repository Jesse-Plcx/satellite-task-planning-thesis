"""Genetic algorithm for satellite task planning - Improved version"""
import numpy as np
import random
from copy import deepcopy


class TaskSchedule:
    """Represents a complete task schedule (chromosome)"""
    def __init__(self, numSatellites, numTargets):
        self.numSatellites = numSatellites
        self.numTargets = numTargets
        # Each gene: (satId, targetId, windowIndex)
        self.genes = []  # Original genes - NEVER modified after crossover/mutation
        self.fitness = 0.0
        self.coverage = 0
        self.feasible = False
    
    def decode_and_evaluate(self, accessWindows, targetList, satResources):
        """Decode genes into a schedule and evaluate fitness."""
        # ── local state (replaces mutation of sat/target objects) ──────────
        sat_storage  = {}   # satId -> storage used (float)
        sat_last_end = {}   # satId -> end time of last accepted task
        sat_tasks    = {}   # satId -> list of task dicts (for apply_solution)
        imaged       = set()  # set of targetIds already imaged

        for satId in range(len(satResources)):
            sat_storage[satId]  = 0.0
            sat_last_end[satId] = 0.0
            sat_tasks[satId]    = []
        # ───────────────────────────────────────────────────────────────────

        # Decode genes: build valid task list
        validTasks = []
        for gene in self.genes:
            satId, targetId, windowIdx = gene
            key = (satId, targetId)
            if key not in accessWindows:
                continue
            windows = accessWindows[key]
            if windowIdx >= len(windows):
                continue

            # Expect new format (5 values): start, end, duration, maxElevation, minRange
            window_data = windows[windowIdx]
            if len(window_data) != 5:
                raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
            windowStart, windowEnd, windowDuration, maxElevation, minRange = window_data

            validTasks.append({
                'satId':       satId,
                'targetId':    targetId,
                'windowStart': windowStart,
                'windowEnd':   windowEnd,
                'priority':    targetList[targetId].priority,
                'maxElevation': maxElevation,
                'gene':        gene
            })

        # Sort by start time for deterministic simulation
        validTasks.sort(key=lambda x: x['windowStart'])

        # Simulate execution (read-only access to satResources / targetList)
        covered = 0
        executedGenes = []
        executed_elevations = {}  # gene -> actualElevation [rad]

        for task in validTasks:
            satId    = task['satId']
            targetId = task['targetId']
            sat      = satResources[satId]   # read-only: .image_size, .storage_capacity,
                                             #            .slew_time,  .imaging_time

            # Check if already imaged
            if targetId in imaged:
                continue

            # Check storage
            if sat_storage[satId] + sat.image_size > sat.storage_capacity:
                continue

            # Calculate start time considering slew.
            if sat_tasks[satId]:   # has prior tasks → must account for slew
                earliestStart = sat_last_end[satId] + sat.slew_time
            else:                  # first task → can start as soon as window opens
                earliestStart = 0.0
            actualStart = max(task['windowStart'], earliestStart)
            actualEnd     = actualStart + sat.imaging_time

            # Check if within window
            if actualEnd > task['windowEnd']:
                continue

            # Estimate actual elevation at imaging midpoint (match greedy)
            min_elev_rad = np.radians(15.0)
            t_mid = actualStart + sat.imaging_time / 2.0
            t_peak = (task['windowStart'] + task['windowEnd']) / 2.0
            half_window = (task['windowEnd'] - task['windowStart']) / 2.0
            position_factor = (max(0.0, 1.0 - ((t_mid - t_peak) / half_window) ** 2)
                               if half_window > 0 else 1.0)
            actual_elev_rad = min_elev_rad + (task['maxElevation'] - min_elev_rad) * position_factor

            # Accept task — update local state only
            task_record = {
                'targetId':     targetId,
                'start':        actualStart,
                'end':          actualEnd,
                'window':       (task['windowStart'], task['windowEnd']),
                'maxElevation': task['maxElevation'],
                'actualElevation': actual_elev_rad,
                'priority':     task['priority']
            }
            sat_tasks[satId].append(task_record)
            sat_storage[satId]  += sat.image_size
            sat_last_end[satId]  = actualEnd
            imaged.add(targetId)
            covered += 1
            executedGenes.append(task['gene'])
            executed_elevations[task['gene']] = actual_elev_rad

        # Calculate priority sum and elevation bonus (separated for clearer objective)
        executed_set = set(executedGenes)
        priority_sum = 0.0
        elevation_bonus_sum = 0.0
        for task in validTasks:
            if task['gene'] in executed_set:
                actual_elev_rad = executed_elevations.get(task['gene'], task['maxElevation'])
                elevation_deg = np.degrees(actual_elev_rad)
                elevation_factor = 1.0 + min(elevation_deg / 90.0, 1.0)
                priority_sum += task['priority']
                elevation_bonus_sum += (elevation_factor - 1.0)

        # Fitness = coverage + priority sum + elevation bonus (separated)
        total_targets_count = len(targetList)
        coverage_rate_internal = covered / total_targets_count if total_targets_count > 0 else 0.0
        coverage_weight = 100.0
        fitness = coverage_weight * coverage_rate_internal + 0.5 * (
            priority_sum + 0.3 * elevation_bonus_sum
        )

        # Cache for apply_solution (written only here, never between evaluations)
        self._last_sat_tasks   = sat_tasks
        self._last_sat_storage = sat_storage
        self._last_imaged      = imaged

        return fitness, covered, executedGenes
    
    def calculate_fitness(self, accessWindows, targetList, satResources):
        """Calculate fitness - wrapper for decode_and_evaluate"""
        self.fitness, self.coverage, _ = self.decode_and_evaluate(
            accessWindows, targetList, satResources
        )
        return self.fitness
    
    def apply_solution(self, accessWindows, targetList, satResources):
        """Calls decode_and_evaluate (which caches results in self._last_*),"""
        _, _, executedGenes = self.decode_and_evaluate(
            accessWindows, targetList, satResources
        )
        # Only update genes when applying final solution
        self.genes = executedGenes

        # Write simulation state back to real sat/target objects
        for satId, sat in enumerate(satResources):
            sat.tasks_completed = self._last_sat_tasks.get(satId, [])
            sat.storage_used    = self._last_sat_storage.get(satId, 0.0)
        for idx, target in enumerate(targetList):
            target.imaged = (idx in self._last_imaged)


def _estimate_actual_elevation(windowStart, windowEnd, imaging_time, maxElevation):
    """Estimate actual elevation at imaging midpoint assuming earliest start."""
    min_elev_rad = np.radians(15.0)
    t_mid = windowStart + imaging_time / 2.0
    t_peak = (windowStart + windowEnd) / 2.0
    half_window = (windowEnd - windowStart) / 2.0
    position_factor = (max(0.0, 1.0 - ((t_mid - t_peak) / half_window) ** 2)
                       if half_window > 0 else 1.0)
    return min_elev_rad + (maxElevation - min_elev_rad) * position_factor


def _build_task_pool(accessWindows, targetList, satResources):
    """Precompute taskPool and taskQuality for reuse across mutations."""
    taskPool = []
    taskQuality = {}
    for (satId, targetId), windows in accessWindows.items():
        priority = targetList[targetId].priority
        for windowIdx, window_data in enumerate(windows):
            task_gene = (satId, targetId, windowIdx)
            taskPool.append(task_gene)

            if len(window_data) != 5:
                raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
            windowStart, windowEnd, _, maxElevation, _ = window_data
            sat = satResources[satId]
            actual_elev_rad = _estimate_actual_elevation(windowStart, windowEnd, sat.imaging_time, maxElevation)
            elevation_deg = np.degrees(actual_elev_rad)
            elevation_factor = 1.0 + min(elevation_deg / 90.0, 1.0)
            quality = priority + 0.3 * (elevation_factor - 1.0)
            taskQuality[task_gene] = quality
    return taskPool, taskQuality


def initialize_population(popSize, accessWindows, numSatellites, numTargets, targetList, satResources,
                          taskPool=None, taskQuality=None):
    """Create initial population with diverse initialization strategies"""
    population = []
    
    # Build task pool with quality metrics (or reuse precomputed values)
    if taskPool is None or taskQuality is None:
        taskPool = []
        taskQuality = {}  # (satId, targetId, windowIdx) -> quality score
        
        for (satId, targetId), windows in accessWindows.items():
            priority = targetList[targetId].priority
            for windowIdx, window_data in enumerate(windows):
                task_gene = (satId, targetId, windowIdx)
                
                # Extract quality metrics
                if len(window_data) != 5:
                    raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
                windowStart, windowEnd, windowDuration, maxElevation, minRange = window_data
                # Quality = priority + 0.3*(elevation_factor - 1) (based on estimated actual elevation)
                sat = satResources[satId]
                actual_elev_rad = _estimate_actual_elevation(windowStart, windowEnd, sat.imaging_time, maxElevation)
                elevation_deg = np.degrees(actual_elev_rad)
                elevation_factor = 1.0 + min(elevation_deg / 90.0, 1.0)
                quality = priority + 0.3 * (elevation_factor - 1.0)
                
                taskPool.append(task_gene)
                taskQuality[task_gene] = quality
    
    # Sort tasks by quality (for greedy-seeded initialization)
    sortedTasks = sorted(taskPool, key=lambda x: taskQuality[x], reverse=True)
    
    # Strategy 1: Greedy with perturbation (70%)
    num_perturb = int(popSize * 0.7)
    for _ in range(num_perturb):
        schedule = TaskSchedule(numSatellites, numTargets)
        
        # Take top-quality tasks with some randomness
        minTasks = max(int(numTargets*0.3), numSatellites*5)
        maxTasks = min(int(numTargets*0.8), len(taskPool))
        minTasks = min(minTasks, maxTasks)
        numTasks = min(len(sortedTasks), random.randint(minTasks, maxTasks))

        # Greedy with perturbation: sample from top-quality tasks randomly
        top_k = sortedTasks[:min(int(numTargets * 1.5), len(sortedTasks))]
        selected = []
        seen_targets = set()

        for gene in top_k:
            if random.random() < 0.8 and gene[1] not in seen_targets:
                selected.append(gene)
                seen_targets.add(gene[1])
            if len(selected) >= numTasks:
                break

        # Fill remaining slots with random tasks (avoid duplicate targetId)
        remaining_pool = [g for g in taskPool if g[1] not in seen_targets]
        random.shuffle(remaining_pool)
        for gene in remaining_pool:
            if len(selected) >= numTasks:
                break
            selected.append(gene)
            seen_targets.add(gene[1])

        schedule.genes = selected
        population.append(schedule)
    
    # Strategy 2: Random initialization (30%)
    num_random = popSize - num_perturb
    for _ in range(num_random):
        schedule = TaskSchedule(numSatellites, numTargets)
        minTasks = int(numTargets*0.2)
        maxTasks = min(int(numTargets*0.6), len(taskPool))
        minTasks = min(minTasks, maxTasks)
        numTasks = min(len(taskPool), random.randint(minTasks, maxTasks))
        schedule.genes = random.sample(taskPool, numTasks)
        population.append(schedule)
    
    return population


def tournament_selection(population, tournamentSize=3):
    """Select parent using tournament selection"""
    tournament = random.sample(population, min(tournamentSize, len(population)))
    return max(tournament, key=lambda x: x.fitness)


def crossover_uniform(parent1, parent2):
    """Uniform crossover - each gene has 50% chance from either parent"""
    child = TaskSchedule(parent1.numSatellites, parent1.numTargets)
    
    if len(parent1.genes) == 0:
        child.genes = parent2.genes[:]   # tuples are immutable, shallow copy is sufficient
        return child
    if len(parent2.genes) == 0:
        child.genes = parent1.genes[:]
        return child
    
    # Uniform crossover
    all_genes = []
    
    # Take genes from both parents
    for gene in parent1.genes:
        if random.random() < 0.5:
            all_genes.append(gene)
    
    for gene in parent2.genes:
        if random.random() < 0.5:
            all_genes.append(gene)
    
    # Remove duplicate targets (keep first occurrence)
    seen_targets = set()
    unique_genes = []
    for gene in all_genes:
        targetId = gene[1]
        if targetId not in seen_targets:
            seen_targets.add(targetId)
            unique_genes.append(gene)
    
    child.genes = unique_genes if len(unique_genes) > 0 else parent1.genes[:]
    return child


def crossover_two_point(parent1, parent2):
    """Two-point crossover - swap middle segment"""
    child = TaskSchedule(parent1.numSatellites, parent1.numTargets)
    
    if len(parent1.genes) == 0 or len(parent2.genes) == 0:
        child.genes = parent1.genes[:] if len(parent1.genes) > 0 else parent2.genes[:]
        return child
    
    # Select two crossover points
    len1 = len(parent1.genes)
    len2 = len(parent2.genes)
    
    point1_a = random.randint(0, len1)
    point1_b = random.randint(0, len1)
    point1_start = min(point1_a, point1_b)
    point1_end = max(point1_a, point1_b)
    
    point2_a = random.randint(0, len2)
    point2_b = random.randint(0, len2)
    point2_start = min(point2_a, point2_b)
    point2_end = max(point2_a, point2_b)
    
    # Create child: parent1[start:end] + parent2[middle]
    child.genes = (parent1.genes[:point1_start] + 
                   parent2.genes[point2_start:point2_end] + 
                   parent1.genes[point1_end:])
    
    # Remove duplicate targets
    seen_targets = set()
    unique_genes = []
    for gene in child.genes:
        targetId = gene[1]
        if targetId not in seen_targets:
            seen_targets.add(targetId)
            unique_genes.append(gene)
    child.genes = unique_genes
    
    return child


def local_search_task_replacement(schedule, accessWindows, targetList, satResources, improvement_rate=0.3, taskQuality=None):
    """Local search: Replace low-quality tasks with high-quality alternatives"""
    if len(schedule.genes) == 0:
        return
    
    # Calculate quality for all possible tasks (or reuse precomputed values)
    if taskQuality is None:
        taskQuality = {}
        allTasks = []
        
        for (satId, targetId), windows in accessWindows.items():
            priority = targetList[targetId].priority
            for windowIdx, window_data in enumerate(windows):
                task_gene = (satId, targetId, windowIdx)
                
                if len(window_data) != 5:
                    raise ValueError(f"Expected 5 values in window_data, got {len(window_data)}: {window_data}")
                windowStart, windowEnd, windowDuration, maxElevation, minRange = window_data
                sat = satResources[satId]
                actual_elev_rad = _estimate_actual_elevation(windowStart, windowEnd, sat.imaging_time, maxElevation)
                elevation_deg = np.degrees(actual_elev_rad)
                elevation_bonus = 0.3 * min(elevation_deg / 90.0, 1.0)
                quality = priority + elevation_bonus
                
                taskQuality[task_gene] = quality
                allTasks.append((task_gene, quality))
    else:
        allTasks = list(taskQuality.items())
    
    # Sort by quality
    allTasks.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate quality of current genes
    current_qualities = [(gene, taskQuality.get(gene, 0.0)) for gene in schedule.genes]
    current_qualities.sort(key=lambda x: x[1])  # Ascending order
    
    # Get targets already in schedule
    current_targets = set(gene[1] for gene in schedule.genes)
    
    # Try to replace bottom X% of tasks with high-quality alternatives
    num_replace = max(1, int(len(schedule.genes) * improvement_rate))
    
    replacements = []
    for gene, quality in current_qualities[:num_replace]:
        # Find high-quality alternative not in current schedule
        for alt_gene, alt_quality in allTasks:
            if alt_quality > quality * 1.1 and alt_gene[1] not in current_targets:
                replacements.append((gene, alt_gene))
                current_targets.discard(gene[1])  # discard: no KeyError if already removed (duplicate targetId in genes)
                current_targets.add(alt_gene[1])
                break
    
    # Apply replacements
    for old_gene, new_gene in replacements:
        if old_gene in schedule.genes:
            idx = schedule.genes.index(old_gene)
            schedule.genes[idx] = new_gene


def mutate_enhanced(schedule, accessWindows, targetList, satResources, mutationRate=0.2,
                    generation=0, maxGenerations=100, taskPool=None, taskQuality=None):
    """Enhanced mutation with multiple operations and adaptive rate"""
    # Adaptive mutation: increase rate if in late generations
    adaptive_rate = mutationRate
    if generation > maxGenerations * 0.7:  # Last 30% of generations
        adaptive_rate = min(mutationRate * 1.5, 0.4)
    
    if random.random() > adaptive_rate:
        return
    
    if len(schedule.genes) == 0:
        # If empty, add some high-quality genes
        if taskPool is None or taskQuality is None:
            taskPool, taskQuality = _build_task_pool(accessWindows, targetList, satResources)
        
        # Add top-quality tasks
        sortedTasks = sorted(taskQuality.keys(), key=lambda x: taskQuality[x], reverse=True)
        num_add = random.randint(min(5, len(sortedTasks)), min(20, len(sortedTasks)))
        schedule.genes = sortedTasks[:num_add]
        return
    
    # Choose mutation type with adjusted probabilities for resource-constrained scenarios
    mutation_types = ['replace_quality', 'add_quality', 'replace_window']
    weights = [0.40, 0.40, 0.20]  # Emphasize quality-based operations
    mutationType = random.choices(mutation_types, weights=weights)[0]
    
    if taskPool is None or taskQuality is None:
        taskPool, taskQuality = _build_task_pool(accessWindows, targetList, satResources)
    
    if mutationType == 'replace_quality':
        # Replace with high-quality task
        if len(schedule.genes) > 0:
            # Replace a random task with a high-quality alternative
            idx = random.randint(0, len(schedule.genes) - 1)
            current_targets = set(gene[1] for gene in schedule.genes)
            old_targetId = schedule.genes[idx][1]
            # Exclude the targetId at the replaced position to avoid false "duplicate" filtering
            current_targets.discard(old_targetId)
            
            # Find high-quality tasks not in schedule
            available = [(gene, taskQuality[gene]) for gene in taskPool 
                        if gene[1] not in current_targets]
            if available:
                available.sort(key=lambda x: x[1], reverse=True)
                # Pick from top 20% with some randomness
                top_choices = available[:max(1, len(available)//5)]
                new_gene = random.choice(top_choices)[0]
                schedule.genes[idx] = new_gene
    
    elif mutationType == 'add_quality':
        # Add 1-3 high-quality genes (without replacement — no duplicate targetIds)
        current_targets = set(gene[1] for gene in schedule.genes)
        available = [(gene, taskQuality[gene]) for gene in taskPool
                    if gene[1] not in current_targets]

        if available:
            available.sort(key=lambda x: x[1], reverse=True)
            top_choices = available[:max(1, len(available)//3)]
            num_add = random.randint(1, min(3, len(top_choices)))
            # Sample WITHOUT replacement to prevent duplicate targetIds in genes
            selected = random.sample(top_choices, num_add)
            for new_gene, _ in selected:
                schedule.genes.append(new_gene)
                current_targets.add(new_gene[1])  # keep the guard set in sync
    
    elif mutationType == 'replace_window':
        # Switch to a different window for the same (satId, targetId)
        if len(schedule.genes) > 0:
            idx = random.randint(0, len(schedule.genes) - 1)
            satId, targetId, windowIdx = schedule.genes[idx]
            key = (satId, targetId)
            if key in accessWindows and len(accessWindows[key]) > 1:
                new_windowIdx = random.choice(
                    [w for w in range(len(accessWindows[key])) if w != windowIdx]
                )
                schedule.genes[idx] = (satId, targetId, new_windowIdx)


def genetic_task_planning(accessWindows, targetList, satResources, numSatellites, numTargets,
                          popSize=50, numGenerations=100, mutationRate=0.2, eliteSize=3, seed=42):
    """Improved Genetic Algorithm for satellite task planning"""
    # Fix all random sources so every run with the same seed produces identical results
    random.seed(seed)
    np.random.seed(seed)

    print(f"\n=== Starting Enhanced Genetic Algorithm ===")
    print(f"Population: {popSize}, Generations: {numGenerations}, Mutation: {mutationRate}, Elite: {eliteSize}, Seed: {seed}")
    
    # Initialize diverse population
    taskPool, taskQuality = _build_task_pool(accessWindows, targetList, satResources)
    population = initialize_population(
        popSize, accessWindows, numSatellites, numTargets, targetList, satResources,
        taskPool=taskPool, taskQuality=taskQuality
    )

    # Evaluate initial population
    for individual in population:
        individual.calculate_fitness(accessWindows, targetList, satResources)
    
    bestEver = max(population, key=lambda x: x.fitness)
    bestEver = deepcopy(bestEver)
    initial_best_coverage = bestEver.coverage
    
    print(f"Initial best: {bestEver.coverage}/{numTargets} targets")
    local_search_runs = 0
    local_search_improvements = 0
    local_search_delta = 0.0
    
    # Evolution loop
    for generation in range(numGenerations):
        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Track best
        current_best = population[0]
        if current_best.fitness > bestEver.fitness:
            bestEver = deepcopy(current_best)
                    
        # Apply local search to elite solutions every 10 generations
        if generation > 0 and generation % 10 == 0:
            local_search_runs += 1
            improvements = 0
            for i in range(min(eliteSize, 5)):  # Top 5 elites
                if i >= len(population):
                    break
                
                fitness_before = population[i].fitness
                elite_schedule = deepcopy(population[i])
                
                # Apply local search to improve task selection
                local_search_task_replacement(
                    elite_schedule, accessWindows, targetList, satResources,
                    improvement_rate=0.3, taskQuality=taskQuality
                )
                
                # Re-evaluate
                elite_schedule.calculate_fitness(accessWindows, targetList, satResources)
                
                fitness_after = elite_schedule.fitness
                if fitness_after > fitness_before:
                    population[i] = elite_schedule
                    improvements += 1
                    local_search_delta += (fitness_after - fitness_before)
            
            local_search_improvements += improvements
        
        # Print progress every 50 generations
        if (generation + 1) % 50 == 0:
            avgFitness = np.mean([ind.fitness for ind in population])
            stdFitness = np.std([ind.fitness for ind in population])
            print(f"Gen {generation+1}/{numGenerations}: "
                  f"Best={current_best.coverage}/{numTargets} ({current_best.fitness:.1f}), "
                  f"Avg={avgFitness:.1f}±{stdFitness:.1f}")
        
        # Adaptive mutation rate (no stagnation-based boost)
        current_mutation_rate = mutationRate
        
        # Create next generation
        nextGen = []
        
        # Elitism: keep top individuals
        nextGen.extend([deepcopy(ind) for ind in population[:eliteSize]])
        
        # Generate offspring
        while len(nextGen) < popSize:
            # Select parents
            parent1 = tournament_selection(population, tournamentSize=3)
            parent2 = tournament_selection(population, tournamentSize=3)
            
            # Crossover (alternate between uniform and two-point)
            if random.random() < 0.5:
                child = crossover_uniform(parent1, parent2)
            else:
                child = crossover_two_point(parent1, parent2)
            
            # Mutation with adaptive rate
            mutate_enhanced(child, accessWindows, targetList, satResources, current_mutation_rate,
                            generation, numGenerations, taskPool=taskPool, taskQuality=taskQuality)
            
            # Evaluate child
            child.calculate_fitness(accessWindows, targetList, satResources)
            
            nextGen.append(child)
        
        population = nextGen
    
    # Final statistics
    population.sort(key=lambda x: x.fitness, reverse=True)
    
    print(f"\n=== Evolution Summary ===")
    print(f"Initial best: {initial_best_coverage}/{numTargets}")
    print(f"Final best: {bestEver.coverage}/{numTargets}")
    if local_search_runs > 0:
        avg_delta = local_search_delta / local_search_improvements if local_search_improvements > 0 else 0.0
        print(f"Local search: {local_search_runs} runs, "
              f"{local_search_improvements} elite improvements, "
              f"avg Δfitness={avg_delta:.2f}")
    print(f"Best genes: {len(bestEver.genes)} tasks")
    
    # Apply best solution to actual data
    print(f"\n=== Applying Best Solution ===")
    bestEver.apply_solution(accessWindows, targetList, satResources)
    
    covered = sum(1 for target in targetList if target.imaged)
    coverage = (covered / len(targetList)) * 100
    print(f"✓ Final coverage: {covered}/{len(targetList)} ({coverage:.1f}%)")
    print(f"✓ Scheduled tasks: {len(bestEver.genes)}")
    
    return None
