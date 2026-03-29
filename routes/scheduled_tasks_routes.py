"""
Scheduled Tasks Routes - Verwaltung geplanter Aufgaben
"""
import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

scheduled_tasks_bp = Blueprint('scheduled_tasks', __name__)

TASKS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'scheduled_tasks.json'
)

TASK_TEMPLATES = {
    "health-check": {
        "name": "Dashboard Health Check",
        "cron": "23 8 * * *",
        "cron_human": "Daily at 8:23",
        "type": "health-check",
        "prompt": (
            "Check the status of the Project Dashboard:\n"
            "1. systemctl is-active project-dashboard\n"
            "2. curl -s http://localhost:5055/api/data | head -5\n"
            "3. df -h /mnt/projects | tail -1\n"
            "4. ls -lt /mnt/projects/backups/project-dashboard/daily/ | head -3\n"
            "Create a brief status report (OK/Warning/Error)."
        ),
    },
    "backup": {
        "name": "Backup Verification",
        "cron": "17 2 * * *",
        "cron_human": "Daily at 2:17",
        "type": "backup",
        "prompt": (
            "Check if the dashboard backup was successful:\n"
            "1. Is today's backup directory present?\n"
            "2. Are important files non-empty? (groups.json, relations.json, ideas.json)\n"
            "3. Check backup log: tail -20 dashboard-backup.log\n"
            "Only on error: create alert."
        ),
    },
    "issue-tracker": {
        "name": "Issue Check",
        "cron": "0 9 * * *",
        "cron_human": "Daily at 9:00",
        "type": "issue-tracker",
        "prompt": (
            "Check if GitHub Issue #{issue_number} has been closed.\n"
            "1. curl -s https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}\n"
            "2. Check the 'state' field in the response.\n"
            "3. If closed: report date and version of the fix.\n"
            "4. If open: briefly confirm it is still open."
        ),
    },
}

CRON_DESCRIPTIONS = {
    "* * * * *": "Every minute",
    "*/5 * * * *": "Every 5 minutes",
    "*/15 * * * *": "Every 15 minutes",
    "*/30 * * * *": "Every 30 minutes",
    "0 * * * *": "Hourly",
    "0 */2 * * *": "Every 2 hours",
    "0 */6 * * *": "Every 6 hours",
    "0 0 * * *": "Daily at midnight",
    "0 9 * * *": "Daily at 9:00",
    "0 9 * * 1-5": "Weekdays at 9:00",
    "0 0 * * 0": "Weekly (Sunday)",
    "0 0 1 * *": "Monthly (1st of month)",
}


def load_tasks():
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"tasks": []}


def save_tasks(data):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def describe_cron(cron_expr):
    """Erzeugt menschenlesbare Beschreibung eines Cron-Ausdrucks."""
    if cron_expr in CRON_DESCRIPTIONS:
        return CRON_DESCRIPTIONS[cron_expr]

    parts = cron_expr.split()
    if len(parts) != 5:
        return cron_expr

    parts_list = parts
    minute, hour, dom, dow = parts_list[0], parts_list[1], parts_list[2], parts_list[4]
    desc_parts = []

    if minute.startswith("*/"):
        return f"Every {minute[2:]} minutes"
    if hour.startswith("*/"):
        return f"Every {hour[2:]} hours"

    if minute != "*" and hour != "*":
        time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
        if dow == "1-5":
            desc_parts.append(f"Weekdays at {time_str}")
        elif dow == "0" or dow == "7":
            desc_parts.append(f"Sundays at {time_str}")
        elif dom != "*":
            desc_parts.append(f"On the {dom}. at {time_str}")
        elif dow == "*" and dom == "*":
            desc_parts.append(f"Daily at {time_str}")
        else:
            desc_parts.append(f"At {time_str}")

    return " ".join(desc_parts) if desc_parts else cron_expr


@scheduled_tasks_bp.route('/scheduled-tasks')
def scheduled_tasks_page():
    return render_template('scheduled_tasks.html', active_page='scheduled_tasks')


@scheduled_tasks_bp.route('/api/scheduled-tasks')
def get_tasks():
    data = load_tasks()
    data["tasks"] = sorted(
        data["tasks"],
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    return jsonify(data)


@scheduled_tasks_bp.route('/api/scheduled-tasks', methods=['POST'])
def create_task():
    req = request.get_json()
    if not req:
        return jsonify({"error": "No data"}), 400

    name = req.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    cron = req.get("cron", "").strip()
    if not cron or len(cron.split()) != 5:
        return jsonify({"error": "Valid cron expression required (5 fields)"}), 400

    data = load_tasks()
    new_task = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "cron": cron,
        "cron_human": describe_cron(cron),
        "type": req.get("type", "custom"),
        "prompt": req.get("prompt", "").strip(),
        "enabled": True,
        "remote_trigger_id": req.get("remote_trigger_id"),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_run": None,
        "last_result": None,
    }
    data["tasks"].append(new_task)
    save_tasks(data)
    return jsonify({"success": True, "task": new_task})


@scheduled_tasks_bp.route('/api/scheduled-tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    req = request.get_json()
    if not req:
        return jsonify({"error": "No data"}), 400

    data = load_tasks()
    for task in data["tasks"]:
        if task["id"] == task_id:
            for field in ('name', 'cron', 'type', 'prompt', 'enabled',
                          'remote_trigger_id', 'last_run', 'last_result'):
                if field in req:
                    task[field] = req[field]
            if 'cron' in req:
                task['cron_human'] = describe_cron(req['cron'])
            task["updated_at"] = datetime.now().isoformat()
            save_tasks(data)
            return jsonify({"success": True, "task": task})

    return jsonify({"error": "Task not found"}), 404


@scheduled_tasks_bp.route('/api/scheduled-tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    data = load_tasks()
    original_count = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t.get("id") != task_id]

    if len(data["tasks"]) == original_count:
        return jsonify({"error": "Task not found"}), 404

    save_tasks(data)
    return jsonify({"success": True})


@scheduled_tasks_bp.route('/api/scheduled-tasks/<task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    data = load_tasks()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["enabled"] = not task["enabled"]
            task["updated_at"] = datetime.now().isoformat()
            save_tasks(data)
            return jsonify({"success": True, "task": task})

    return jsonify({"error": "Task not found"}), 404


@scheduled_tasks_bp.route('/api/scheduled-tasks/templates')
def get_templates():
    return jsonify(TASK_TEMPLATES)
