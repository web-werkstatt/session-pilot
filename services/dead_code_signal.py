"""Extrahiert Dead-Code-Summary aus Quality-Report Issues."""


def extract_dead_code_summary(issues):
    """Zaehlt Dead-Code-Issues nach Kategorie und Typ."""
    dead_code = [i for i in issues if i.get("category") == "dead_code" and i.get("status") != "ignored"]
    dead_deps = [i for i in issues if i.get("category") == "dead_deps" and i.get("status") != "ignored"]
    dead_frontend = [i for i in issues if i.get("category") == "dead_frontend" and i.get("status") != "ignored"]

    unused_imports = sum(1 for i in dead_code if "Import" in i.get("title", ""))
    orphaned_files = sum(1 for i in dead_code if "Verwaist" in i.get("title", ""))
    orphaned_assets = sum(1 for i in dead_frontend if i.get("level") == "warning")
    unused_css = sum(1 for i in dead_frontend if i.get("level") == "info")
    high_conf = sum(1 for i in dead_code + dead_deps + dead_frontend if i.get("confidence") == "high")

    total = len(dead_code) + len(dead_deps) + len(dead_frontend)
    if total == 0:
        return None

    return {
        "total": total,
        "unused_imports": unused_imports,
        "orphaned_files": orphaned_files,
        "unused_deps": len(dead_deps),
        "orphaned_assets": orphaned_assets,
        "unused_css_classes": unused_css,
        "high_confidence": high_conf,
    }
