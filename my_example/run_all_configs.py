"""
Run the formal scenario config experiments in my_example/configs.

Usage:
  python run_all_configs.py
  python run_all_configs.py --algorithm random
  python run_all_configs.py --algorithm ewf
  python run_all_configs.py --algorithm genetic
  python run_all_configs.py --algorithm sa
  python run_all_configs.py --no-show
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Run formal scenario config experiments.")
    parser.add_argument("--algorithm", type=str, default=None,
                        choices=["random", "ewf", "greedy", "sa", "genetic", "both", "all", "all_no_ga"],
                        help="Override algorithm for every config.")
    parser.add_argument("--no-show", action="store_true",
                        help="Disable plot windows (uses non-interactive backend).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing.")
    args, extra = parser.parse_known_args()

    script_dir = Path(__file__).resolve().parent
    configs_dir = script_dir / "configs"
    formal_order = [
        "scenario_surplus_30sat_100tar.yaml",
        "scenario_normal_30sat_400tar.yaml",
        "scenario_severe_30sat_1000tar.yaml",
    ]
    configs = [configs_dir / name for name in formal_order if (configs_dir / name).exists()]

    if not configs:
        print(f"No formal scenario config files found in {configs_dir}")
        return 1

    print(f"Found {len(configs)} configs:")
    for cfg in configs:
        print(f"  - {cfg.name}")

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nBatch start: {start_time}\n")

    for cfg in configs:
        cmd = [sys.executable, "main.py", "--config", str(cfg)]
        if args.algorithm:
            cmd += ["--algorithm", args.algorithm]
        if extra:
            cmd += extra

        print(f"\n>>> Running: {' '.join(cmd)}")
        if args.dry_run:
            continue

        env = os.environ.copy()
        if args.no_show:
            env["MPLBACKEND"] = "Agg"

        result = subprocess.run(cmd, cwd=script_dir, env=env)
        if result.returncode != 0:
            print(f"Stopped: {cfg.name} failed with code {result.returncode}")
            return result.returncode

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nBatch done: {end_time}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
