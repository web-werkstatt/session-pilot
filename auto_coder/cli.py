"""CLI fuer auto_coder: scan und report Befehle."""

import argparse
import sys

from auto_coder.report import load_report
from auto_coder.scanner import ProjectQualityScanner


def cmd_scan(args):
    """Scannt ein oder alle Projekte."""
    scanner = ProjectQualityScanner()

    if args.all:
        print("Scanne alle Projekte...\n")
        reports = scanner.scan_all()
        print(f"\n{'='*60}")
        print(f"{'Projekt':<30} {'Score':>6} {'Issues':>7}")
        print(f"{'='*60}")
        for r in sorted(reports, key=lambda x: x.score_numeric):
            print(f"{r.project:<30} {r.score:>3} ({r.score_numeric:>3}) {r.summary.get('total_issues', 0):>5}")
        print(f"{'='*60}")
        print(f"{len(reports)} Projekte gescannt.")
    else:
        if not args.project:
            print("Fehler: Projekt-Pfad angeben oder --all verwenden.", file=sys.stderr)
            sys.exit(1)
        print(f"Scanne {args.project}...")
        report = scanner.scan(args.project)
        _print_report(report)


def cmd_report(args):
    """Zeigt gespeicherten Report an."""
    report = load_report(args.project)
    if not report:
        print(f"Kein Report gefunden fuer {args.project}", file=sys.stderr)
        sys.exit(1)
    _print_report(report)


def _print_report(report):
    """Formatiert Report fuer Terminal-Ausgabe."""
    s = report.summary
    print(f"\n{'='*60}")
    print(f"  {report.project} — Score: {report.score} ({report.score_numeric}/100)")
    print(f"{'='*60}")
    print(f"  Gescannt: {report.scanned_at}")
    print(f"  Issues:   {s.get('errors', 0)} Errors, {s.get('warnings', 0)} Warnings, {s.get('info', 0)} Info")
    if s.get("skipped_checks"):
        print(f"  Skipped:  {', '.join(s['skipped_checks'])}")
    print()

    if not report.issues:
        print("  Keine Issues gefunden!")
        return

    # Gruppiert nach Kategorie
    categories: dict[str, list] = {}
    for issue in report.issues:
        categories.setdefault(issue.category, []).append(issue)

    for cat, issues in sorted(categories.items()):
        print(f"  [{cat}]")
        for issue in issues:
            icon = "X" if issue.level == "error" else "!" if issue.level == "warning" else "i"
            print(f"    {icon} {issue.id}: {issue.title}")
            if issue.files:
                print(f"      Dateien: {', '.join(issue.files[:3])}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="auto_coder",
        description="Quality Scanner fuer Projekte",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    scan_p = sub.add_parser("scan", help="Projekt scannen")
    scan_p.add_argument("project", nargs="?", help="Pfad zum Projekt")
    scan_p.add_argument("--all", action="store_true", help="Alle Projekte scannen")

    # report
    report_p = sub.add_parser("report", help="Report anzeigen")
    report_p.add_argument("project", help="Pfad zum Projekt")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
