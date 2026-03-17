#!/bin/bash
# Project Dashboard - Automatisches Backup-Skript
# Sichert alle JSON-Datenspeicher, project.json Dateien und Claude Sessions
#
# Usage: backup.sh [daily|weekly]
# Cronjob: 0 1 * * * /mnt/projects/project_dashboard/scripts/backup.sh daily
#          0 2 * * 0 /mnt/projects/project_dashboard/scripts/backup.sh weekly

set -uo pipefail

BACKUP_BASE="/mnt/projects/backups/project-dashboard"
DASHBOARD_DIR="/mnt/projects/project_dashboard"
PROJECTS_DIR="/mnt/projects"
CLAUDE_DIR="/home/joshko/.claude"
LOG_FILE="$DASHBOARD_DIR/dashboard-backup.log"

TYPE="${1:-daily}"
DATE=$(date +%Y-%m-%d_%H%M)
BACKUP_DIR="$BACKUP_BASE/$TYPE/$DATE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Backup gestartet: $TYPE ==="

mkdir -p "$BACKUP_DIR"/{dashboard-data,project-jsons,claude-sessions,claude-memory}

# 1. Dashboard JSON-Datenspeicher sichern
log "Sichere Dashboard-Datenspeicher..."
for f in groups.json relations.json ideas.json; do
    if [ -f "$DASHBOARD_DIR/$f" ]; then
        cp "$DASHBOARD_DIR/$f" "$BACKUP_DIR/dashboard-data/"
        log "  -> $f gesichert"
    fi
done

# config.py sichern (ohne sensible Daten zu loggen)
if [ -f "$DASHBOARD_DIR/config.py" ]; then
    cp "$DASHBOARD_DIR/config.py" "$BACKUP_DIR/dashboard-data/"
    log "  -> config.py gesichert"
fi

# next-session.md sichern
if [ -f "$DASHBOARD_DIR/next-session.md" ]; then
    cp "$DASHBOARD_DIR/next-session.md" "$BACKUP_DIR/dashboard-data/"
    log "  -> next-session.md gesichert"
fi

# 2. Alle project.json Dateien aus /mnt/projects/ sammeln
log "Sammle project.json Dateien..."
PROJECT_COUNT=0
find "$PROJECTS_DIR" -maxdepth 2 -name "project.json" -not -path "*/node_modules/*" -not -path "*/backups/*" -not -path "*/lost+found/*" 2>/dev/null | while read -r pjson; do
    # Relativen Pfad als Verzeichnisname nutzen
    rel_path=$(dirname "${pjson#$PROJECTS_DIR/}")
    mkdir -p "$BACKUP_DIR/project-jsons/$rel_path"
    cp "$pjson" "$BACKUP_DIR/project-jsons/$rel_path/"
done
PROJECT_COUNT=$(find "$BACKUP_DIR/project-jsons" -name "project.json" 2>/dev/null | wc -l)
log "  -> $PROJECT_COUNT project.json Dateien gesichert"

# 3. Claude Sessions und Memory sichern
log "Sichere Claude Sessions und Memory..."
if [ -d "$CLAUDE_DIR/projects/-mnt-projects-project-dashboard" ]; then
    cp -r "$CLAUDE_DIR/projects/-mnt-projects-project-dashboard" "$BACKUP_DIR/claude-sessions/" 2>/dev/null || true
    log "  -> Dashboard Claude Sessions gesichert"
fi

if [ -d "$CLAUDE_DIR/projects/-mnt-projects-project-dashboard/memory" ]; then
    cp -r "$CLAUDE_DIR/projects/-mnt-projects-project-dashboard/memory" "$BACKUP_DIR/claude-memory/" 2>/dev/null || true
    log "  -> Claude Memory gesichert"
fi

# CLAUDE.md sichern
if [ -f "$DASHBOARD_DIR/CLAUDE.md" ]; then
    cp "$DASHBOARD_DIR/CLAUDE.md" "$BACKUP_DIR/dashboard-data/"
    log "  -> CLAUDE.md gesichert"
fi

# 4. Backup-Groesse berechnen
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup-Groesse: $BACKUP_SIZE"

# 5. Alte Backups rotieren
log "Rotiere alte Backups..."
if [ "$TYPE" = "daily" ]; then
    # Taeglich: Behalte die letzten 7 Tage
    KEEP=7
elif [ "$TYPE" = "weekly" ]; then
    # Woechentlich: Behalte die letzten 4 Wochen
    KEEP=4
fi

BACKUP_TYPE_DIR="$BACKUP_BASE/$TYPE"
BACKUP_COUNT=$(ls -1d "$BACKUP_TYPE_DIR"/*/ 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - KEEP))
    ls -1d "$BACKUP_TYPE_DIR"/*/ | head -n "$REMOVE_COUNT" | while read -r old_backup; do
        log "  Loesche altes Backup: $(basename "$old_backup")"
        rm -rf "$old_backup"
    done
fi

log "=== Backup abgeschlossen: $BACKUP_DIR ==="
log ""
