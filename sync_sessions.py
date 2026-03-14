#!/usr/bin/env python3
"""
Standalone Sync-Skript fuer Claude Code Sessions.
Kann manuell oder via systemd-Timer ausgefuehrt werden.

Usage: python3 sync_sessions.py
"""
import sys
import os
import time

# Projektverzeichnis zum Pfad hinzufuegen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.db_service import ensure_database
from services.session_import import sync_all


def main():
    start = time.time()
    print(f"Claude Session Sync gestartet: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        ensure_database()
        print("Datenbank bereit.")
    except Exception as e:
        print(f"Datenbank-Fehler: {e}")
        sys.exit(1)

    try:
        stats = sync_all()
        elapsed = time.time() - start
        print(f"\nSync abgeschlossen in {elapsed:.1f}s")
        print(f"  Importiert: {stats['imported']}")
        print(f"  Aktualisiert: {stats['updated']}")
        print(f"  Unverändert: {stats['unchanged']}")
        print(f"  Übersprungen: {stats['skipped']}")
        print(f"  Fehler: {stats['errors']}")
    except Exception as e:
        print(f"Sync-Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
