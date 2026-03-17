#!/bin/bash
# Project Dashboard - Installationsskript (Bare-Metal / ohne Docker)
# Getestet auf Debian/Ubuntu

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="project-dashboard"
SERVICE_USER="${USER}"

echo "=== Project Dashboard Setup ==="
echo ""

# 1. Python-Abhängigkeiten prüfen
echo "[1/5] Prüfe Python-Abhängigkeiten..."
if ! command -v python3 &>/dev/null; then
    echo "FEHLER: python3 nicht gefunden. Bitte installieren: sudo apt install python3 python3-pip"
    exit 1
fi

pip3 install --user -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || \
    pip3 install -r "$SCRIPT_DIR/requirements.txt"
echo "  -> Python-Pakete installiert"

# 2. PostgreSQL prüfen
echo "[2/5] Prüfe PostgreSQL..."
if ! command -v psql &>/dev/null; then
    echo "  PostgreSQL nicht gefunden."
    echo "  Installation: sudo apt install postgresql postgresql-client"
    echo "  Oder verwende Docker: docker compose up -d db"
    echo ""
    read -p "  Fortfahren ohne PostgreSQL? (Sessions-Feature deaktiviert) [j/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
        exit 1
    fi
else
    echo "  -> PostgreSQL gefunden"
fi

# 3. .env erstellen
echo "[3/5] Konfiguration..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "  -> .env aus .env.example erstellt"
    echo "  WICHTIG: Bitte $SCRIPT_DIR/.env anpassen!"
    echo ""
else
    echo "  -> .env existiert bereits"
fi

# 4. JSON-Datenspeicher initialisieren
echo "[4/5] Initialisiere Datenspeicher..."
for f in groups.json relations.json ideas.json; do
    if [ ! -f "$SCRIPT_DIR/$f" ]; then
        echo '{}' > "$SCRIPT_DIR/$f"
        echo "  -> $f erstellt"
    fi
done

# 5. systemd-Service einrichten
echo "[5/5] Systemd-Service..."
read -p "  Systemd-Service einrichten? [j/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[jJyY]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    sudo tee "$SERVICE_FILE" > /dev/null <<UNIT
[Unit]
Description=Projekt-Dashboard Web-Server
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/app.py
Restart=always
RestartSec=10
StandardOutput=append:${SCRIPT_DIR}/dashboard.log
StandardError=append:${SCRIPT_DIR}/dashboard.log
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=${SCRIPT_DIR}/.env

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    echo "  -> Service gestartet: sudo systemctl status $SERVICE_NAME"
else
    echo "  -> Übersprungen. Manuell starten: python3 $SCRIPT_DIR/app.py"
fi

echo ""
echo "=== Setup abgeschlossen ==="
echo "Dashboard: http://localhost:5055"
echo ""
echo "Nächste Schritte:"
echo "  1. .env anpassen (Gitea-Token, DB-Passwort, Projekt-Pfad)"
echo "  2. PostgreSQL-Datenbank erstellen (für Sessions-Feature)"
echo "  3. Browser öffnen: http://localhost:5055"
