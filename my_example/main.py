"""
Main entry point for satellite task planning with algorithm comparison
"""
import argparse
import time
import os
import json
import platform
import subprocess
import sys
from copy import deepcopy
from datetime import datetime

from common.scenario_generator import generate_walker_constellation
from common.simulator import setup_simulation, process_access_windows
from common.visualization import plot_task_planning_results
from common.evaluation import evaluate_schedule
from algorithms import (
    random_baseline_task_planning,
    earliest_window_first_task_planning,
    greedy_task_planning,
    genetic_task_planning,
    simulated_annealing_task_planning
)
from config_loader import ConfigLoader
from Basilisk.architecture import astroConstants


DISPLAY_NAMES = {
    'random': 'Random',
    'ewf': 'EWF',
    'greedy': 'Improved Greedy',
    'sa': 'SA',
    'genetic': 'Genetic'
}


def safe_git_output(args, cwd):
    """Return git metadata when available without failing the run."""
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def run_algorithm(algorithmName, accessWindows, targetList, satResources,
                  numSatellites, numTargets, duration, output_dir=None, **kwargs):
    """Run specified algorithm and visualize results
    
    Args:
        output_dir: Optional output directory path. If provided, results will be saved there.
    """
    display_name = DISPLAY_NAMES.get(algorithmName, algorithmName.upper())
    print(f"\n{'='*70}")
    print(f"Running {display_name} Algorithm")
    print(f"{'='*70}")
    
    # Make deep copies to ensure fair comparison
    targetListCopy = deepcopy(targetList)
    satResourcesCopy = deepcopy(satResources)
    
    startTime = time.time()
    
    if algorithmName == 'random':
        random_baseline_task_planning(
            accessWindows, targetListCopy, satResourcesCopy,
            numSatellites, numTargets, duration=duration, seed=kwargs.get('seed', 42)
        )
    elif algorithmName == 'ewf':
        earliest_window_first_task_planning(
            accessWindows, targetListCopy, satResourcesCopy,
            numSatellites, numTargets, duration=duration
        )
    elif algorithmName == 'greedy':
        greedy_task_planning(accessWindows, targetListCopy, satResourcesCopy,
                           numSatellites, numTargets, duration=duration)
    elif algorithmName == 'sa':
        initialTemperature = kwargs.get('initialTemperature')
        finalTemperature = kwargs.get('finalTemperature', 0.05)
        coolingRate = kwargs.get('coolingRate', 0.97)
        iterationsPerTemp = kwargs.get('iterationsPerTemp', 40)
        seed = kwargs.get('seed', 42)
        simulated_annealing_task_planning(
            accessWindows, targetListCopy, satResourcesCopy,
            numSatellites, numTargets,
            initialTemperature=initialTemperature,
            finalTemperature=finalTemperature,
            coolingRate=coolingRate,
            iterationsPerTemp=iterationsPerTemp,
            seed=seed
        )
    elif algorithmName == 'genetic':
        popSize = kwargs.get('popSize', 50)
        numGenerations = kwargs.get('numGenerations', 100)
        mutationRate = kwargs.get('mutationRate', 0.1)
        seed = kwargs.get('seed', 42)
        historyPath = kwargs.get('historyPath')
        genetic_task_planning(accessWindows, targetListCopy, satResourcesCopy,
                            numSatellites, numTargets,
                            popSize=popSize, numGenerations=numGenerations,
                            mutationRate=mutationRate, seed=seed,
                            historyPath=historyPath)
    else:
        raise ValueError(f"Unknown algorithm: {algorithmName}")
    
    elapsedTime = time.time() - startTime
    
    covered_count, total_value, avg_elev_deg = evaluate_schedule(
        targetListCopy, satResourcesCopy, numSatellites, duration
    )
    print(f"M4 Runtime: {elapsedTime:.2f} seconds\n")
    
    result_dir = plot_task_planning_results(targetListCopy, satResourcesCopy, numSatellites, 
                                            duration, algorithmName=display_name,
                                            output_dir=output_dir)
    
    return (targetListCopy, satResourcesCopy, elapsedTime, result_dir,
            covered_count, total_value, avg_elev_deg)


def main():
    parser = argparse.ArgumentParser(
        description='Satellite Task Planning with Multiple Algorithms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use formal normal-conflict configuration
  python main.py
  
  # Use final thesis scenario configs
  python main.py --config configs/scenario_surplus_30sat_100tar.yaml
  python main.py --config configs/scenario_normal_30sat_400tar.yaml
  python main.py --config configs/scenario_severe_30sat_1000tar.yaml
  
  # Use config file and override parameters
  python main.py --config configs/scenario_normal_30sat_400tar.yaml --targets 500
  
  # Main comparison: Improved Greedy vs Genetic
  python main.py --satellites 18 --targets 100 --algorithm both

  # Full comparison: Random + EWF + Improved Greedy + SA + Genetic
  python main.py --satellites 18 --targets 100 --algorithm all

  # Non-GA comparison: Random + EWF + Improved Greedy + SA
  python main.py --satellites 18 --targets 100 --algorithm all_no_ga
        """
    )
    
    # Configuration file argument
    parser.add_argument('--config', type=str, default=None,
                       help='Path to YAML configuration file')
    
    # Algorithm selection
    parser.add_argument('--algorithm', type=str, default=None,
                       choices=['random', 'ewf', 'greedy', 'sa', 'genetic', 'both', 'all', 'all_no_ga'],
                       help='Algorithm to run (overrides config)')
    
    # Simulation parameters (override config)
    parser.add_argument('--satellites', type=int, default=None,
                       help='Number of satellites (overrides config)')
    parser.add_argument('--targets', type=int, default=None,
                       help='Number of targets (overrides config)')
    parser.add_argument('--target-mode', type=str, default=None,
                       choices=['random', 'cities', 'grid'],
                       help='Target generation mode (overrides config)')
    parser.add_argument('--duration', type=float, default=None,
                       help='Simulation duration in seconds (overrides config)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for scenario generation and stochastic algorithms (overrides config)')
    parser.add_argument('--vizard', action='store_true', default=None,
                       help='Enable Vizard 3D visualization (overrides config)')
    parser.add_argument('--no-vizard', action='store_true', default=False,
                       help='Disable Vizard 3D visualization')
    
    # Constellation parameters (override config)
    parser.add_argument('--planes', type=int, default=None,
                       help='Number of orbital planes (overrides config)')
    parser.add_argument('--altitude', type=float, default=None,
                       help='Orbital altitude in km (overrides config)')
    parser.add_argument('--inclination', type=float, default=None,
                       help='Orbital inclination in degrees (overrides config)')
    
    # Genetic algorithm parameters (override config)
    parser.add_argument('--pop-size', type=int, default=None,
                       help='Genetic algorithm population size (overrides config)')
    parser.add_argument('--generations', type=int, default=None,
                       help='Genetic algorithm generations (overrides config)')
    parser.add_argument('--mutation-rate', type=float, default=None,
                       help='Genetic algorithm mutation rate (overrides config)')
    
    # Simulated annealing parameters (override config)
    parser.add_argument('--sa-initial-temp', type=float, default=None,
                       help='SA initial temperature; if omitted, auto-calibrated from sampled Δfitness')
    parser.add_argument('--sa-final-temp', type=float, default=None,
                       help='SA final temperature (overrides config)')
    parser.add_argument('--sa-cooling-rate', type=float, default=None,
                       help='SA cooling rate (overrides config)')
    parser.add_argument('--sa-iter-per-temp', type=int, default=None,
                       help='SA iterations per temperature level (overrides config)')
    
    args = parser.parse_args()
    
    # Load configuration from file
    config = ConfigLoader.load_config(args.config)
    
    # Override config with command-line arguments (使用映射简化代码)
    arg_to_config_map = {
        # 格式: 'arg_name': ('config_section', 'config_key')
        'algorithm': ('algorithms', 'run'),
        'satellites': ('simulation', 'satellites'),
        'targets': ('simulation', 'targets'),
        'target_mode': ('simulation', 'target_mode'),
        'duration': ('simulation', 'duration'),  
        'seed': ('simulation', 'seed'),
        'planes': ('constellation', 'num_planes'),
        'altitude': ('constellation', 'altitude_km'),
        'inclination': ('constellation', 'inclination_deg'),
        'sa_initial_temp': ('algorithms', 'sa', 'initial_temperature'),
        'sa_final_temp': ('algorithms', 'sa', 'final_temperature'),
        'sa_cooling_rate': ('algorithms', 'sa', 'cooling_rate'),
        'sa_iter_per_temp': ('algorithms', 'sa', 'iterations_per_temp'),
        'pop_size': ('algorithms', 'genetic', 'population_size'),
        'generations': ('algorithms', 'genetic', 'num_generations'),
        'mutation_rate': ('algorithms', 'genetic', 'mutation_rate'),
    }
    
    # 批量处理参数覆盖
    for arg_name, config_path in arg_to_config_map.items():
        arg_value = getattr(args, arg_name, None)
        if arg_value is not None:
            # 根据配置路径深度设置值
            if len(config_path) == 2:
                config[config_path[0]][config_path[1]] = arg_value
            elif len(config_path) == 3:
                config[config_path[0]][config_path[1]][config_path[2]] = arg_value
    
    # 特殊处理 vizard 布尔标志
    if args.vizard is not None:
        config['simulation']['vizard'] = True
    if args.no_vizard:
        config['simulation']['vizard'] = False
    
    # Print configuration
    ConfigLoader.print_config(config)
    
    # Extract configuration values
    sim_config = config['simulation']
    const_config = config['constellation']
    sat_res_config = config['satellite_resources']
    algo_config = config['algorithms']
    
    num_satellites = sim_config['satellites']
    num_targets = sim_config['targets']
    target_mode = sim_config['target_mode']
    duration = sim_config['duration']
    use_vizard = sim_config['vizard']
    seed = sim_config.get('seed')
    if seed is None:
        seed = int(time.time() * 1000) % (2**32)
    
    # Generate Walker constellation
    walkerElements = generate_walker_constellation(
        numSatellites=num_satellites,
        numPlanes=const_config['num_planes'],
        altitude_km=const_config['altitude_km'],
        inclination_deg=const_config['inclination_deg']
    )
    
    # Setup simulation
    scSim, targetList, satResources, accessRecorders, duration = setup_simulation(
        numSatellites=num_satellites,
        numTargets=num_targets,
        walkerElements=walkerElements,
        targetMode=target_mode,
        duration=duration,
        useVizard=use_vizard,
        targetSeed=seed,
        satResourcesConfig=sat_res_config
    )
    
    # Process access windows
    imaging_time = sat_res_config.get('imaging_time_sec', 10.0) if sat_res_config else 10.0
    sat_altitudes_km = [elem["altitude_km"] for elem in walkerElements]
    accessWindows = process_access_windows(
        accessRecorders, num_satellites, num_targets,
        min_window_duration=imaging_time,
        sat_altitudes_km=sat_altitudes_km,
        max_roll_angle_deg=sat_res_config.get('max_roll_angle_deg')
    )
    
    # Create shared output directory for this experiment
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Extract config name from file path
    if args.config:
        config_name = os.path.splitext(os.path.basename(args.config))[0]
    else:
        config_name = 'default'
    
    folder_name = f"{config_name}_{timestamp}"
    runs_dir = os.path.join(script_dir, 'res', 'runs')
    shared_output_dir = os.path.join(runs_dir, folder_name)
    os.makedirs(shared_output_dir, exist_ok=True)
    repo_root = os.path.dirname(script_dir)
    git_commit = safe_git_output(["rev-parse", "HEAD"], repo_root)
    git_branch = safe_git_output(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    command_line = subprocess.list2cmdline([sys.executable, *sys.argv])

    # Write run summary (configuration + visibility criteria) to a txt file
    summary_path = os.path.join(shared_output_dir, "run_summary.txt")
    req_earth_km = (astroConstants.REQ_EARTH / 1000.0) if astroConstants.REQ_EARTH > 1e5 else astroConstants.REQ_EARTH
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("EXPERIMENT CONFIGURATION\n")
        f.write("="*60 + "\n")
        f.write(f"Config file: {args.config or 'default'}\n")
        f.write(f"Seed: {seed}\n")
        f.write(f"Duration: {duration:.1f} s ({duration/3600:.1f} h)\n")
        f.write(f"Satellites: {num_satellites}\n")
        f.write(f"Targets: {num_targets}\n")
        f.write(f"Target mode: {target_mode}\n")
        f.write(f"Walker planes: {const_config['num_planes']}\n")
        f.write(f"Altitude: {const_config['altitude_km']} km\n")
        f.write(f"Inclination: {const_config['inclination_deg']}°\n")
        f.write("\n")
        f.write("REPRODUCIBILITY METADATA\n")
        f.write("="*60 + "\n")
        f.write(f"Timestamp:              {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Output directory:       {shared_output_dir}\n")
        f.write(f"Command:                {command_line}\n")
        f.write(f"Python executable:      {sys.executable}\n")
        f.write(f"Python version:         {platform.python_version()}\n")
        f.write(f"Git branch:             {git_branch}\n")
        f.write(f"Git commit:             {git_commit}\n")
        f.write("\n")
        f.write("VISIBILITY CRITERIA & CONSTRAINTS\n")
        f.write("="*60 + "\n")
        f.write("Minimum Elevation Angle:  15.0°\n")
        f.write(f"Maximum Roll Angle:       ±{sat_res_config.get('max_roll_angle_deg', 45.0)}° (agile pointing)\n")
        f.write(f"Minimum Window Duration:  {sat_res_config.get('imaging_time_sec', 10.0):.0f} seconds  (= imaging_time_sec, physical minimum to complete imaging)\n")
        f.write(f"Earth Model:              WGS-84 (REQ_EARTH = {req_earth_km:.1f} km)\n")
        f.write(f"Storage Capacity:         {sat_res_config.get('storage_capacity_mbits', 100.0)} Mbits per satellite\n")
        f.write(f"Image Size:               {sat_res_config.get('image_size_mbits', 10.0)} Mbits per image\n")
        max_images = int(sat_res_config.get('storage_capacity_mbits', 100.0) / sat_res_config.get('image_size_mbits', 10.0))
        f.write(f"Max Images per Satellite: {max_images}\n")
        f.write(f"Slew Time:                {sat_res_config.get('slew_time_sec', 30.0)} seconds\n")
        f.write(f"Imaging Time:             {sat_res_config.get('imaging_time_sec', 10.0)} seconds\n")
        pmin = sat_res_config.get('priority_min', 0.1)
        pmax = sat_res_config.get('priority_max', 1.0)
        f.write(f"Priority Distribution:    uniform [{pmin:.1f}, {pmax:.1f}]  (range ratio {pmax/pmin:.0f}x)\n")
        f.write("="*60 + "\n")
    
    # Run algorithms
    results = {}
    algorithm_to_run = algo_config['run']
    
    if algorithm_to_run in ['random', 'all', 'all_no_ga']:
        (targetListRandom, satResourcesRandom, timeRandom, output_dir,
         covered_random, value_random, elev_random) = run_algorithm(
            'random', accessWindows, targetList, satResources,
            num_satellites, num_targets, duration, output_dir=shared_output_dir,
            seed=seed
        )
        results['random'] = {
            'coverage': covered_random,
            'total_value': value_random,
            'avg_elev_deg': elev_random,
            'time': timeRandom
        }

    if algorithm_to_run in ['ewf', 'all', 'all_no_ga']:
        (targetListEWF, satResourcesEWF, timeEWF, output_dir,
         covered_ewf, value_ewf, elev_ewf) = run_algorithm(
            'ewf', accessWindows, targetList, satResources,
            num_satellites, num_targets, duration, output_dir=shared_output_dir
        )
        results['ewf'] = {
            'coverage': covered_ewf,
            'total_value': value_ewf,
            'avg_elev_deg': elev_ewf,
            'time': timeEWF
        }

    if algorithm_to_run in ['greedy', 'both', 'all', 'all_no_ga']:
        (targetListGreedy, satResourcesGreedy, timeGreedy, output_dir,
         covered_greedy, value_greedy, elev_greedy) = run_algorithm(
            'greedy', accessWindows, targetList, satResources,
            num_satellites, num_targets, duration, output_dir=shared_output_dir
        )
        results['greedy'] = {
            'coverage': covered_greedy,
            'total_value': value_greedy,
            'avg_elev_deg': elev_greedy,
            'time': timeGreedy
        }

    if algorithm_to_run in ['sa', 'all', 'all_no_ga']:
        sa_config = algo_config['sa']
        (targetListSA, satResourcesSA, timeSA, output_dir,
         covered_sa, value_sa, elev_sa) = run_algorithm(
            'sa', accessWindows, targetList, satResources,
            num_satellites, num_targets, duration, output_dir=shared_output_dir,
            initialTemperature=sa_config['initial_temperature'],
            finalTemperature=sa_config['final_temperature'],
            coolingRate=sa_config['cooling_rate'],
            iterationsPerTemp=sa_config['iterations_per_temp'],
            seed=seed
        )
        results['sa'] = {
            'coverage': covered_sa,
            'total_value': value_sa,
            'avg_elev_deg': elev_sa,
            'time': timeSA
        }
    
    if algorithm_to_run in ['genetic', 'both', 'all']:
        genetic_config = algo_config['genetic']
        (targetListGenetic, satResourcesGenetic, timeGenetic, output_dir,
         covered_genetic, value_genetic, elev_genetic) = run_algorithm(
            'genetic', accessWindows, targetList, satResources,
            num_satellites, num_targets, duration, output_dir=shared_output_dir,
            popSize=genetic_config['population_size'],
            numGenerations=genetic_config['num_generations'],
            mutationRate=genetic_config['mutation_rate'],
            seed=seed,
            historyPath=os.path.join(shared_output_dir, "genetic_convergence.csv")
        )
        results['genetic'] = {
            'coverage': covered_genetic,
            'total_value': value_genetic,
            'avg_elev_deg': elev_genetic,
            'time': timeGenetic
        }
    
    # Print comparison
    if algorithm_to_run in ['both', 'all', 'all_no_ga']:
        lines = []
        lines.append("\n" + "="*75)
        if algorithm_to_run == 'both':
            lines.append("MAIN COMPARISON (IMPROVED GREEDY VS GENETIC)")
        elif algorithm_to_run == 'all_no_ga':
            lines.append("NON-GA COMPARISON (RANDOM + EWF + IMPROVED GREEDY + SA)")
        else:
            lines.append("FULL COMPARISON (RANDOM + EWF + IMPROVED GREEDY + SA + GENETIC)")
        lines.append("="*75)
        lines.append("="*75)
        lines.append(f"{'Algorithm':<10} {'M1 Task Comp':<18} {'M2 Priority':<14} "
                     f"{'M3 Avg Elev':<13} {'M4 Runtime':<10}")
        lines.append("-"*75)
        for algo, res in results.items():
            coverage_pct = (res['coverage'] / num_targets) * 100
            display_name = DISPLAY_NAMES.get(algo, algo.capitalize())
            lines.append(f"{display_name:<16} "
                         f"{res['coverage']}/{num_targets} ({coverage_pct:>5.1f}%)  "
                         f"{res['total_value']:>12.3f}  "
                         f"{res['avg_elev_deg']:>6.1f}°       "
                         f"{res['time']:>6.2f}s")
        lines.append("-"*75)
        
        # Calculate differences
        if 'greedy' in results and 'genetic' in results:
            cov_diff = results['genetic']['coverage'] - results['greedy']['coverage']
            cov_diff_pct = (cov_diff / num_targets) * 100
            value_diff = results['genetic']['total_value'] - results['greedy']['total_value']
            value_diff_pct = (value_diff / results['greedy']['total_value'] * 100) if results['greedy']['total_value'] > 0 else 0
            time_diff = results['genetic']['time'] - results['greedy']['time']
            
            elev_diff = results['genetic']['avg_elev_deg'] - results['greedy']['avg_elev_deg']
            lines.append(f"{'Δ (Gen-Gre)':<16} "
                         f"{cov_diff:+d} ({cov_diff_pct:+.1f}%)     "
                         f"{value_diff:>+12.3f} ({value_diff_pct:+.1f}%)  "
                         f"{elev_diff:>+6.1f}°      "
                         f"{time_diff:>+6.2f}s")
        
        lines.append("="*75)
        print("\n".join(lines))

        # Also append comparison to run summary file
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n\nALGORITHM COMPARISON\n")
            f.write("="*75 + "\n")
            f.write("\n".join(lines[3:]) + "\n")

    metrics_summary_path = os.path.join(shared_output_dir, "metrics_summary.json")
    metrics_payload = {
        'config_file': args.config or 'default',
        'config_name': config_name,
        'run_dir': shared_output_dir,
        'seed': seed,
        'algorithm_mode': algorithm_to_run,
        'num_satellites': num_satellites,
        'num_targets': num_targets,
        'duration_sec': duration,
        'python_executable': sys.executable,
        'python_version': platform.python_version(),
        'git_branch': git_branch,
        'git_commit': git_commit,
        'command': command_line,
        'results': {}
    }
    for algo, res in results.items():
        coverage_pct = (res['coverage'] / num_targets) * 100 if num_targets > 0 else 0.0
        metrics_payload['results'][algo] = {
            'display_name': DISPLAY_NAMES.get(algo, algo.capitalize()),
            'coverage_count': int(res['coverage']),
            'coverage_pct': float(coverage_pct),
            'total_value': float(res['total_value']),
            'avg_elev_deg': float(res['avg_elev_deg']),
            'time_sec': float(res['time'])
        }
    with open(metrics_summary_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2, ensure_ascii=False)
    
    # Print output directory summary
    print("\n" + "="*70)
    print("RESULTS SAVED")
    print("="*70)
    if algorithm_to_run in ['both', 'all', 'all_no_ga']:
        print(f"  Results saved to: {shared_output_dir}")
        print(f"    - Selected algorithm plots and summaries")
    elif algorithm_to_run == 'random':
        print(f"  Random baseline results saved to: {shared_output_dir}")
    elif algorithm_to_run == 'ewf':
        print(f"  EWF results saved to: {shared_output_dir}")
    elif algorithm_to_run == 'greedy':
        print(f"  Improved Greedy results saved to: {shared_output_dir}")
    elif algorithm_to_run == 'sa':
        print(f"  SA results saved to: {shared_output_dir}")
    elif algorithm_to_run == 'genetic':
        print(f"  Genetic results saved to: {shared_output_dir}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
