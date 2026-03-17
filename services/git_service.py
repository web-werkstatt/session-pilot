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


def get_git_status(project_path):
    """Prueft Git-Status eines Projekts"""
    try:
        result = subprocess.run(
            ["git", "-C", project_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            if result.stdout.strip():
                return "geaendert"
            return "sauber"
    except Exception:
        pass
    return None


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
