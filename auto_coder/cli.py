"""CLI fuer auto_coder: scan und report Befehle."""

import argparse
import sys

from auto_coder.report import diff_reports, load_baseline, load_report, save_baseline
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


def cmd_diff(args):
    """Scannt und vergleicht mit Baseline."""
    baseline = load_baseline(args.project)
    if not baseline:
        print(f"Keine Baseline gefunden fuer {args.project}", file=sys.stderr)
        print("Erstelle eine mit: auto_coder baseline <projekt>")
        sys.exit(1)

    scanner = ProjectQualityScanner()
    print(f"Scanne {args.project}...")
    current = scanner.scan(args.project)
    delta = diff_reports(baseline, current)

    print(f"\n{'='*60}")
    print(f"  {current.project} — Diff zur Baseline")
    print(f"{'='*60}")
    print(f"  Score:    {baseline.score} ({baseline.score_numeric}) -> {current.score} ({current.score_numeric})  [{'+' if delta['score_delta'] >= 0 else ''}{delta['score_delta']}]")
    print(f"  Errors:   {'+' if delta['error_delta'] >= 0 else ''}{delta['error_delta']}")
    print(f"  Warnings: {'+' if delta['warning_delta'] >= 0 else ''}{delta['warning_delta']}")
    print()

    if delta["new_issues"]:
        print(f"  NEU ({len(delta['new_issues'])}):")
        for issue in delta["new_issues"]:
            icon = "X" if issue.level == "error" else "!" if issue.level == "warning" else "i"
            print(f"    {icon} {issue.id}: {issue.title}")
        print()

    if delta["fixed_issues"]:
        print(f"  BEHOBEN ({len(delta['fixed_issues'])}):")
        for issue in delta["fixed_issues"]:
            print(f"    + {issue.id}: {issue.title}")
        print()

    if delta["improved"]:
        print("  Ergebnis: OK (keine Verschlechterung)")
    else:
        print("  Ergebnis: VERSCHLECHTERT")
        sys.exit(1)


def cmd_baseline(args):
    """Speichert aktuellen Report als Baseline."""
    report = load_report(args.project)
    if not report:
        print("Kein Report vorhanden. Fuehre zuerst einen Scan aus.", file=sys.stderr)
        sys.exit(1)
    path = save_baseline(args.project, report)
    s = report.summary
    print(f"Baseline gespeichert: {path}")
    print(f"  Score: {report.score} ({report.score_numeric})")
    print(f"  Issues: {s.get('errors', 0)} Errors, {s.get('warnings', 0)} Warnings")


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

    # diff
    diff_p = sub.add_parser("diff", help="Vergleich mit Baseline")
    diff_p.add_argument("project", help="Pfad zum Projekt")

    # baseline
    base_p = sub.add_parser("baseline", help="Aktuelle Baseline setzen")
    base_p.add_argument("project", help="Pfad zum Projekt")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "baseline":
        cmd_baseline(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
