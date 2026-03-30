"""
Run the main multi-seed experiment and aggregate summary statistics.

Recommended usage:
  python run_multiseed.py
  python run_multiseed.py --config configs/default.yaml --algorithm all --seeds 1,2,3,4,5
"""
import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_SEEDS = [1, 2, 3, 4, 5]


def parse_seed_list(seed_text: str | None) -> list[int]:
    if not seed_text:
        return DEFAULT_SEEDS[:]
    seeds = []
    for item in seed_text.split(","):
        item = item.strip()
        if not item:
            continue
        seeds.append(int(item))
    if not seeds:
        raise ValueError("No valid seeds were provided")
    return seeds


def format_mean_std(values: list[float], decimals: int = 3, suffix: str = "") -> str:
    if not values:
        return "-"
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{mean:.{decimals}f} ± {std:.{decimals}f}{suffix}"


def format_mean_std_pct(values: list[float]) -> str:
    if not values:
        return "-"
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{mean:.1f}% ± {std:.1f}%"


def latest_saved_path(stdout_text: str) -> str | None:
    matches = re.findall(r"saved to:\s*(.+)", stdout_text, flags=re.IGNORECASE)
    if not matches:
        return None
    return matches[-1].strip()


def aggregate_records(records: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for rec in records:
        grouped.setdefault(rec["algorithm"], []).append(rec)

    summary = {}
    for algo, rows in grouped.items():
        summary[algo] = {
            "runs": len(rows),
            "coverage_count_mean_std": format_mean_std([r["coverage_count"] for r in rows], decimals=2),
            "coverage_pct_mean_std": format_mean_std_pct([r["coverage_pct"] for r in rows]),
            "total_value_mean_std": format_mean_std([r["total_value"] for r in rows], decimals=3),
            "avg_elev_deg_mean_std": format_mean_std([r["avg_elev_deg"] for r in rows], decimals=2, suffix="°"),
            "time_sec_mean_std": format_mean_std([r["time_sec"] for r in rows], decimals=2, suffix=" s"),
        }
    return summary


def write_summary_csv(path: Path, summary: dict[str, dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "algorithm",
            "runs",
            "coverage_count_mean_std",
            "coverage_pct_mean_std",
            "total_value_mean_std",
            "avg_elev_deg_mean_std",
            "time_sec_mean_std",
        ])
        for algo, row in summary.items():
            writer.writerow([
                algo,
                row["runs"],
                row["coverage_count_mean_std"],
                row["coverage_pct_mean_std"],
                row["total_value_mean_std"],
                row["avg_elev_deg_mean_std"],
                row["time_sec_mean_std"],
            ])


def write_summary_markdown(path: Path, summary: dict[str, dict], seeds: list[int]) -> None:
    lines = [
        "# Multi-Seed Experiment Summary",
        "",
        "- Type: `scene-based main experiment`",
        f"- Seeds: `{', '.join(str(s) for s in seeds)}`",
        "",
        "| Algorithm | Runs | M1 count | M1 rate | M2 | M3 | Time |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for algo, row in summary.items():
        lines.append(
            f"| {algo} | {row['runs']} | {row['coverage_count_mean_std']} | "
            f"{row['coverage_pct_mean_std']} | {row['total_value_mean_std']} | "
            f"{row['avg_elev_deg_mean_std']} | {row['time_sec_mean_std']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the main multi-seed experiment and aggregate results."
    )
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Path to config file relative to my_example/")
    parser.add_argument("--algorithm", type=str, default="all",
                        choices=["random", "ewf", "greedy", "sa", "genetic", "both", "all"],
                        help="Algorithm set to run in each repetition.")
    parser.add_argument("--seeds", type=str, default="1,2,3,4,5",
                        help="Comma-separated scene seed list. Default: 1,2,3,4,5")
    parser.add_argument("--keep-vizard", action="store_true",
                        help="Keep Vizard enabled. Default is disabled for batch experiments.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing.")
    args = parser.parse_args()

    seeds = parse_seed_list(args.seeds)
    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_name = Path(args.config).stem
    output_dir = script_dir / "res" / "multiseed" / f"{config_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")

    run_records = []
    for idx, seed in enumerate(seeds, start=1):
        cmd = [
            sys.executable, "main.py",
            "--config", args.config,
            "--algorithm", args.algorithm,
            "--seed", str(seed),
        ]
        if not args.keep_vizard:
            cmd.append("--no-vizard")

        print(f"\n[{idx}/{len(seeds)}] {' '.join(cmd)}")
        if args.dry_run:
            continue

        result = subprocess.run(
            cmd,
            cwd=script_dir,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return result.returncode

        run_dir = latest_saved_path(result.stdout)
        if not run_dir:
            print(result.stdout)
            raise RuntimeError("Could not find result directory in main.py output")

        metrics_path = Path(run_dir) / "metrics_summary.json"
        if not metrics_path.exists():
            raise FileNotFoundError(f"metrics_summary.json not found: {metrics_path}")

        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        for algo, metrics in payload["results"].items():
            run_records.append({
                "seed": seed,
                "algorithm": algo,
                "display_name": metrics["display_name"],
                "coverage_count": metrics["coverage_count"],
                "coverage_pct": metrics["coverage_pct"],
                "total_value": metrics["total_value"],
                "avg_elev_deg": metrics["avg_elev_deg"],
                "time_sec": metrics["time_sec"],
                "run_dir": run_dir,
            })

    if args.dry_run:
        return 0

    all_runs_csv = output_dir / "all_runs.csv"
    with all_runs_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed", "algorithm", "display_name", "coverage_count",
                "coverage_pct", "total_value", "avg_elev_deg", "time_sec", "run_dir"
            ]
        )
        writer.writeheader()
        writer.writerows(run_records)

    summary = aggregate_records(run_records)
    write_summary_csv(output_dir / "summary.csv", summary)
    write_summary_markdown(output_dir / "summary.md", summary, seeds=seeds)

    manifest = {
        "config": args.config,
        "algorithm": args.algorithm,
        "experiment_type": "scene-based main experiment",
        "seeds": seeds,
        "output_dir": str(output_dir),
        "num_runs": len(run_records),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("MULTI-SEED RESULTS SAVED")
    print("=" * 70)
    print(f"  {output_dir}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
