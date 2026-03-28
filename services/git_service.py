"""
Git Service - Lokale Git-Informationen
"""
import subprocess


def get_local_git_info(project_path):
    """Holt lokalen Git-Info inkl. Remote-Vergleich"""
    info = {
        "local_sha": None,
        "remote_name": None,
        "has_remote": False
    }

    try:
        # Lokaler HEAD SHA
        result = subprocess.run(
            ["git", "-C", project_path, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["local_sha"] = result.stdout.strip()

        # Remote URL prüfen
        result = subprocess.run(
            ["git", "-C", project_path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            if "git.webideas24.com" in remote_url:
                info["has_remote"] = True
                info["remote_name"] = remote_url.split("/")[-1].replace(".git", "")
    except:
        pass

    return info



def get_git_status_detail(project_path):
    """Detaillierter Git-Status fuer ein Projekt"""
    result = {"is_git": False, "branch": None, "changes": [], "ahead": 0, "behind": 0, "has_remote": False}

    try:
        # Branch
        r = subprocess.run(["git", "-C", project_path, "branch", "--show-current"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return result
        result["is_git"] = True
        result["branch"] = r.stdout.strip()

        # Status --porcelain
        r = subprocess.run(["git", "-C", project_path, "status", "--porcelain"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split('\n'):
                if line.strip():
                    status = line[:2]
                    filepath = line[3:]
                    result["changes"].append({"status": status.strip(), "file": filepath})

        # Remote + ahead/behind
        r = subprocess.run(["git", "-C", project_path, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=5)
        result["has_remote"] = r.returncode == 0

        if result["has_remote"]:
            # Fetch (silent, kurzer Timeout)
            subprocess.run(["git", "-C", project_path, "fetch", "--quiet"],
                           capture_output=True, timeout=10)
            r = subprocess.run(["git", "-C", project_path, "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                parts = r.stdout.strip().split()
                if len(parts) == 2:
                    result["ahead"] = int(parts[0])
                    result["behind"] = int(parts[1])
    except Exception:
        pass

    return result


def git_add_all(project_path):
    """Staged alle Aenderungen"""
    r = subprocess.run(["git", "-C", project_path, "add", "-A"],
                       capture_output=True, text=True, timeout=10)
    return r.returncode == 0, r.stderr.strip()


def git_commit(project_path, message):
    """Erstellt einen Commit"""
    if not message or not message.strip():
        return False, "Commit-Message darf nicht leer sein"

    r = subprocess.run(["git", "-C", project_path, "commit", "-m", message],
                       capture_output=True, text=True, timeout=15)
    output = r.stdout.strip() + "\n" + r.stderr.strip()
    return r.returncode == 0, output.strip()


def git_push(project_path):
    """Pusht zum Remote"""
    r = subprocess.run(["git", "-C", project_path, "push"],
                       capture_output=True, text=True, timeout=30)
    output = r.stdout.strip() + "\n" + r.stderr.strip()
    return r.returncode == 0, output.strip()


def git_pull(project_path):
    """Pullt vom Remote"""
    r = subprocess.run(["git", "-C", project_path, "pull", "--ff-only"],
                       capture_output=True, text=True, timeout=30)
    output = r.stdout.strip() + "\n" + r.stderr.strip()
    return r.returncode == 0, output.strip()


def get_activity_score(project_path):
    """Berechnet Aktivitaets-Score basierend auf Commits der letzten 7/30 Tage.
    Returns: {"commits_7d": int, "commits_30d": int, "score": int, "level": str}
    """
    result = {"commits_7d": 0, "commits_30d": 0, "score": 0, "level": "inactive"}
    try:
        for period, key in [("7 days", "commits_7d"), ("30 days", "commits_30d")]:
            r = subprocess.run(
                ["git", "-C", project_path, "rev-list", "--count",
                 f"--since={period} ago", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                result[key] = int(r.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass

    # Gewichteter Score: 7d-Commits zaehlen 3x, 30d-Commits 1x
    score = result["commits_7d"] * 3 + result["commits_30d"]
    result["score"] = score

    if score >= 20:
        result["level"] = "hot"
    elif score >= 10:
        result["level"] = "active"
    elif score >= 3:
        result["level"] = "moderate"
    elif score >= 1:
        result["level"] = "low"
    else:
        result["level"] = "inactive"

    return result


def get_branches(project_path):
    """Listet alle Branches mit letzter Aktivitaet.
    Returns: {"count": int, "branches": [{"name": str, "last_commit": str, "is_current": bool}]}
    """
    result = {"count": 0, "branches": []}
    try:
        r = subprocess.run(
            ["git", "-C", project_path, "branch", "-a",
             "--format=%(refname:short)|%(committerdate:short)|%(HEAD)"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0:
            return result

        seen = set()
        for line in r.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('|')
            if len(parts) < 3:
                continue
            name = parts[0].strip()
            # Remote-Branches: origin/xxx -> nur wenn kein lokaler existiert
            if name.startswith("origin/"):
                local_name = name[7:]
                if local_name == "HEAD":
                    continue
                if local_name in seen:
                    continue
                name = local_name
            if name in seen:
                continue
            seen.add(name)
            result["branches"].append({
                "name": name,
                "last_commit": parts[1].strip(),
                "is_current": parts[2].strip() == "*"
            })
        result["count"] = len(result["branches"])
        # Sortieren: aktueller Branch zuerst, dann nach Datum absteigend
        result["branches"].sort(key=lambda b: (not b["is_current"], b.get("last_commit", "")), reverse=False)
        result["branches"].sort(key=lambda b: b["is_current"], reverse=True)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def get_contributors(project_path, limit=3):
    """Top Contributors mit Commit-Anzahl.
    Returns: [{"name": str, "email": str, "commits": int}]
    """
    result = []
    try:
        r = subprocess.run(
            ["git", "-C", project_path, "shortlog", "-sne", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            import re
            for line in r.stdout.strip().split('\n')[:limit]:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'(\d+)\s+(.+?)\s+<(.+?)>', line)
                if match:
                    result.append({
                        "name": match.group(2).strip(),
                        "email": match.group(3).strip(),
                        "commits": int(match.group(1))
                    })
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result
