# run_all.py
"""
Run multiple Python scripts at the same time (concurrently). Cross‑platform.
Great when your paths have spaces like "Graph 1/script.py".

Usage examples:
  # Explicit scripts
  python run_all.py "Graph 1/script.py" "Graph 2/script.py"

  # All subfolders named "Graph */script.py"
  python run_all.py --glob "Graph */script.py"

  # Limit how many run at once (queue the rest)
  python run_all.py --glob "Graph */script.py" --max-procs 3

  # Use a specific interpreter (e.g., your venv)
  python run_all.py --glob "Graph */script.py" --python .venv/Scripts/python.exe
"""
from __future__ import annotations

import argparse
import os
import sys
import shlex
import subprocess as sp
from pathlib import Path
from typing import List

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run multiple Python scripts concurrently.")
    ap.add_argument("scripts", nargs="*", help="Script paths to run (files).")
    ap.add_argument("--glob", help="Glob pattern to find scripts (e.g., 'Graph */script.py').")
    ap.add_argument("--python", default="python", help="Python interpreter to use (default: python).")
    ap.add_argument("--max-procs", type=int, default=0, help="Max concurrent processes (0 = no limit).")
    ap.add_argument("--logs-dir", default="logs", help="Directory to write per‑script logs.")
    return ap.parse_args()

def discover_scripts(args: argparse.Namespace) -> List[Path]:
    found: List[Path] = []
    if args.glob:
        for p in Path().glob(args.glob):
            if p.is_file():
                found.append(p.resolve())
    for s in args.scripts:
        p = Path(s).resolve()
        if p.is_file():
            found.append(p)
    # De‑dupe while preserving order
    seen = set()
    ordered = []
    for p in found:
        if p not in seen:
            ordered.append(p)
            seen.add(p)
    if not ordered:
        raise SystemExit("No scripts found. Pass paths and/or --glob pattern.")
    return ordered

def pretty_name(path: Path) -> str:
    return path.as_posix().replace("/", "_")

def main() -> None:
    args = parse_args()
    scripts = discover_scripts(args)
    logs_dir = Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    max_procs = args.max_procs if args.max_procs and args.max_procs > 0 else len(scripts)

    running: List[sp.Popen] = []
    queue: List[Path] = list(scripts)
    results = {}

    def launch(script_path: Path) -> sp.Popen:
        log_file = logs_dir / f"{pretty_name(script_path)}.log"
        log = open(log_file, "w", encoding="utf-8", buffering=1)
        # -u for unbuffered output; pass args as list to handle spaces safely
        proc = sp.Popen(
            [args.python, "-u", str(script_path)],
            stdout=log,
            stderr=sp.STDOUT,
            cwd=str(script_path.parent),
            text=True
        )
        results[proc] = (script_path, log_file, log)
        print(f"[LAUNCHED] {script_path}  ->  {log_file}")
        return proc

    # Prime the pool
    while queue and len(running) < max_procs:
        running.append(launch(queue.pop(0)))

    # Loop until all complete
    while running:
        for proc in list(running):
            rc = proc.poll()
            if rc is None:
                continue
            script_path, log_file, log = results.pop(proc)
            log.close()
            running.remove(proc)
            status = "OK" if rc == 0 else f"FAIL (exit {rc})"
            print(f"[DONE] {script_path}  ->  {status}  (log: {log_file})")
            if queue:
                running.append(launch(queue.pop(0)))

    # Summary
    print("\nSummary:")
    for log_file in sorted(Path(args.logs_dir).glob("*.log")):
        print(f"  {log_file.name}")

if __name__ == "__main__":
    main()
