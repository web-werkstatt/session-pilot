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
    """Prüft Git-Status eines Projekts"""
    try:
        result = subprocess.run(
            ["git", "-C", project_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            if result.stdout.strip():
                return "geändert"
            return "sauber"
    except:
        pass
    return None
