"""
Docker Service - Container-Verwaltung
"""
import subprocess
import re


def get_docker_containers():
    """Holt alle Docker-Container"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}|{{.CreatedAt}}"],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 3:
                    name, status, image = parts[0], parts[1], parts[2]
                    ports_str = parts[3] if len(parts) > 3 else ""
                    created_at = parts[4] if len(parts) > 4 else ""

                    if "Up" in status:
                        if "healthy" in status:
                            simple_status = "✅ Healthy"
                        elif "unhealthy" in status:
                            simple_status = "⚠️ Unhealthy"
                        else:
                            simple_status = "🔵 Running"
                    elif "Exited" in status:
                        simple_status = "🔴 Stopped"
                    else:
                        simple_status = status

                    # Port extrahieren
                    port = None
                    if ports_str:
                        all_ports = re.findall(r':(\d+)->', ports_str)
                        if all_ports:
                            web_ports = [int(p) for p in all_ports if int(p) in [9000, 9443, 80, 443, 3000, 8080, 5000, 8888, 5173, 4321]]
                            if web_ports:
                                port = web_ports[0]
                            else:
                                port = int(all_ports[0])

                    last_modified = "-"
                    if created_at:
                        last_modified = created_at[:16]

                    containers.append({
                        "name": name,
                        "status": simple_status,
                        "raw_status": status,
                        "image": image[:50],
                        "port": port,
                        "last_modified": last_modified
                    })
        return containers
    except Exception:
        return []


def container_action(name, action):
    """Fuehrt eine Aktion auf einem Container aus (start/stop/restart)"""
    if action not in ('start', 'stop', 'restart'):
        return {"success": False, "error": f"Unbekannte Aktion: {action}"}

    # Sicherheit: Container-Name validieren (nur alphanumerisch, Bindestrich, Unterstrich, Punkt)
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', name):
        return {"success": False, "error": "Ungueltiger Container-Name"}

    try:
        result = subprocess.run(
            ["docker", action, name],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"success": True, "message": f"Container '{name}' {action} erfolgreich"}
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return {"success": False, "error": error}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout bei {action} von '{name}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_container_logs(name, tail=50):
    """Holt die letzten Log-Zeilen eines Containers"""
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', name):
        return {"success": False, "error": "Ungueltiger Container-Name"}

    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), name],
            capture_output=True, text=True, timeout=10
        )
        # Docker logs gehen oft auf stderr
        output = result.stdout + result.stderr
        return {"success": True, "logs": output}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout beim Laden der Logs"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def load_yaml_simple(filepath):
    """Einfacher YAML-Parser für docker-compose"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        services = []
        container_names = []
        ports = []
        in_services = False

        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('services:'):
                in_services = True
                continue
            if in_services and stripped and not stripped.startswith('#'):
                indent = len(line) - len(line.lstrip())
                if indent == 2 and ':' in stripped:
                    service_name = stripped.split(':')[0].strip()
                    if service_name and not service_name.startswith('-'):
                        services.append(service_name)
                if 'container_name:' in stripped:
                    cn = stripped.split('container_name:')[1].strip().strip('"').strip("'")
                    if cn:
                        container_names.append(cn)
                if ':' in stripped and any(c.isdigit() for c in stripped):
                    port_match = re.search(r'["\']?(\d{2,5}):\d+', stripped)
                    if port_match:
                        ports.append(int(port_match.group(1)))

        return services, container_names, ports
    except:
        return [], [], []
