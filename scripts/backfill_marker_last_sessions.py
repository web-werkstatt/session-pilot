#!/usr/bin/env python3
"""
Backfill fuer leere marker.last_session-Felder auf Basis von project_plans.session_uuid.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.copilot_marker_service import backfill_marker_last_sessions


def main():
    parser = argparse.ArgumentParser(description="Backfill marker last_session values from project_plans.session_uuid")
    parser.add_argument("--project", required=True, help="Projektname, z.B. project_dashboard")
    args = parser.parse_args()

    result = backfill_marker_last_sessions(args.project)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
