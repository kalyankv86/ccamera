"""CLI wrapper around ccms.scheduler.partitions.ensure_partitions.
Run once at deploy time (dev_bootstrap.sh); the same function is also called
monthly by the Celery beat task ccms.checkers.tasks.ensure_partitions_task."""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ccms.scheduler.partitions import ensure_partitions  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["ensure"])
    parser.add_argument("--months-ahead", type=int, default=3)
    args = parser.parse_args()
    if args.action == "ensure":
        names = ensure_partitions(args.months_ahead)
        print("Ensured partitions:", ", ".join(names))
