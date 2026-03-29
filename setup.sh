#!/bin/bash
# SessionPilot - Interactive Setup
# Inspired by Vite's create-vite experience

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
ask()  { echo -en "  ${CYAN}?${NC} $1"; }
info() { echo -e "  ${DIM}$1${NC}"; }

# ============================================================
echo ""
echo -e "${BOLD}  SessionPilot${NC} ${DIM}— AI Coding Dashboard${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *)       PLATFORM="other" ;;
esac
ok "Platform: ${BOLD}$PLATFORM${NC}"

# ============================================================
# 1. Check Python
# ============================================================
echo ""
echo -e "${BOLD}  Prerequisites${NC}"
echo ""

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 9 ]; then
            PYTHON_CMD="$cmd"
            ok "Python ${PY_VERSION}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.9+ not found"
    if [ "$PLATFORM" = "linux" ]; then
        info "Install: sudo apt install python3 python3-pip python3-venv"
    elif [ "$PLATFORM" = "macos" ]; then
        info "Install: brew install python3"
    elif [ "$PLATFORM" = "windows" ]; then
        info "Install: https://www.python.org/downloads/"
    fi
    exit 1
fi

# Check pip
if $PYTHON_CMD -m pip --version &>/dev/null; then
    ok "pip"
else
    fail "pip not found"
    info "Install: $PYTHON_CMD -m ensurepip --upgrade"
    exit 1
fi

# Check PostgreSQL
DB_AVAILABLE=false
if command -v psql &>/dev/null; then
    PG_VERSION=$(psql --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1)
    ok "PostgreSQL ${PG_VERSION}"
    DB_AVAILABLE=true
else
    warn "PostgreSQL not found ${DIM}(Sessions/Timesheets/Usage Monitor disabled)${NC}"
    if [ "$PLATFORM" = "linux" ]; then
        info "Install: sudo apt install postgresql postgresql-client"
    elif [ "$PLATFORM" = "macos" ]; then
        info "Install: brew install postgresql@16 && brew services start postgresql@16"
    fi
    echo ""
    ask "Continue without PostgreSQL? ${DIM}[Y/n]${NC} "
    read -r REPLY
    if [[ "$REPLY" =~ ^[nN]$ ]]; then
        exit 0
    fi
fi

# Check optional tools
if command -v git &>/dev/null; then
    ok "Git $(git --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)"
else
    warn "Git not found ${DIM}(Git status features disabled)${NC}"
fi

if command -v docker &>/dev/null; then
    ok "Docker $(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)"
else
    warn "Docker not found ${DIM}(Container monitoring disabled)${NC}"
fi

if command -v rg &>/dev/null; then
    ok "ripgrep"
else
    warn "ripgrep (rg) not found ${DIM}(Search falls back to grep)${NC}"
fi

# ============================================================
# 2. Configuration
# ============================================================
echo ""
echo -e "${BOLD}  Configuration${NC}"
echo ""

# --- Projects directory ---
if [ "$PLATFORM" = "macos" ]; then
    DEFAULT_PROJECTS="$HOME/Projects"
elif [ "$PLATFORM" = "windows" ]; then
    DEFAULT_PROJECTS="$HOME/Projects"
else
    DEFAULT_PROJECTS="/mnt/projects"
fi

ask "Projects directory: ${DIM}($DEFAULT_PROJECTS)${NC} "
read -r PROJECTS_INPUT
PROJECTS_DIR="${PROJECTS_INPUT:-$DEFAULT_PROJECTS}"

if [ -d "$PROJECTS_DIR" ]; then
    PROJECT_COUNT=$(find "$PROJECTS_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)
    ok "Found ${BOLD}${PROJECT_COUNT}${NC} projects in $PROJECTS_DIR"
else
    warn "Directory does not exist yet: $PROJECTS_DIR"
    ask "Create it? ${DIM}[Y/n]${NC} "
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[nN]$ ]]; then
        mkdir -p "$PROJECTS_DIR"
        ok "Created $PROJECTS_DIR"
    fi
fi

# --- Port ---
DEFAULT_PORT=5055

is_port_in_use() {
    local port=$1
    if [ "$PLATFORM" = "macos" ]; then
        lsof -iTCP:"$port" -sTCP:LISTEN &>/dev/null
    elif [ "$PLATFORM" = "linux" ]; then
        ss -tlnp 2>/dev/null | grep -q ":$port " || \
        netstat -tlnp 2>/dev/null | grep -q ":$port "
    else
        # Fallback: try to bind
        ($PYTHON_CMD -c "import socket; s=socket.socket(); s.bind(('',${port})); s.close()" 2>/dev/null) && return 1 || return 0
    fi
}

find_free_port() {
    local port=$1
    while true; do
        if ! is_port_in_use "$port"; then
            echo "$port"
            return
        fi
        port=$((port + 1))
        if [ "$port" -gt 65535 ]; then
            echo "$1"
            return
        fi
    done
}

FREE_PORT=$(find_free_port $DEFAULT_PORT)

if [ "$FREE_PORT" != "$DEFAULT_PORT" ]; then
    warn "Port $DEFAULT_PORT is in use"
    ask "Port: ${DIM}($FREE_PORT)${NC} "
else
    ask "Port: ${DIM}($DEFAULT_PORT)${NC} "
fi
read -r PORT_INPUT
DASHBOARD_PORT="${PORT_INPUT:-$FREE_PORT}"

# Check chosen port
FINAL_PORT=$(find_free_port "$DASHBOARD_PORT")
if [ "$FINAL_PORT" != "$DASHBOARD_PORT" ]; then
    warn "Port $DASHBOARD_PORT is also in use, using $FINAL_PORT instead"
    DASHBOARD_PORT="$FINAL_PORT"
fi
ok "Port: ${BOLD}$DASHBOARD_PORT${NC}"

# --- Database ---
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="project_dashboard"
DB_USER="dashboard"
DB_PASS=""

if [ "$DB_AVAILABLE" = true ]; then
    echo ""
    ask "Database name: ${DIM}($DB_NAME)${NC} "
    read -r INPUT; DB_NAME="${INPUT:-$DB_NAME}"

    ask "Database user: ${DIM}($DB_USER)${NC} "
    read -r INPUT; DB_USER="${INPUT:-$DB_USER}"

    # Generate random password if not set
    RANDOM_PW=$(head -c 16 /dev/urandom 2>/dev/null | base64 | tr -d '/+=' | head -c 16)
    ask "Database password: ${DIM}($RANDOM_PW)${NC} "
    read -r INPUT; DB_PASS="${INPUT:-$RANDOM_PW}"

    ok "Database: ${BOLD}$DB_NAME${NC} (user: $DB_USER)"
fi

# --- Gitea (optional) ---
echo ""
ask "Configure Gitea integration? ${DIM}[y/N]${NC} "
read -r REPLY
GITEA_URL=""
GITEA_TOKEN=""
GITEA_USER=""
if [[ "$REPLY" =~ ^[yY]$ ]]; then
    ask "Gitea URL: "
    read -r GITEA_URL
    ask "Gitea API token: "
    read -r GITEA_TOKEN
    ask "Gitea username: "
    read -r GITEA_USER
    ok "Gitea: $GITEA_URL"
fi

# ============================================================
# 3. Install
# ============================================================
echo ""
echo -e "${BOLD}  Installing${NC}"
echo ""

# Python packages
echo -n "  Installing Python packages..."
$PYTHON_CMD -m pip install --user -r "$SCRIPT_DIR/requirements.txt" -q 2>/dev/null || \
    $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt" -q 2>/dev/null
ok "Python packages installed"

# Write .env
cat > "$SCRIPT_DIR/.env" <<EOF
# SessionPilot Configuration (generated by setup.sh)

DASHBOARD_PROJECTS_DIR=$PROJECTS_DIR
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=$DASHBOARD_PORT

DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
EOF

if [ -n "$GITEA_URL" ]; then
    cat >> "$SCRIPT_DIR/.env" <<EOF

GITEA_URL=$GITEA_URL
GITEA_TOKEN=$GITEA_TOKEN
GITEA_USER=$GITEA_USER
EOF
fi
ok ".env written"

# Initialize JSON data stores
for f in groups.json relations.json ideas.json; do
    [ ! -f "$SCRIPT_DIR/$f" ] && echo '{}' > "$SCRIPT_DIR/$f"
done
[ ! -f "$SCRIPT_DIR/scheduled_tasks.json" ] && echo '{"tasks":[]}' > "$SCRIPT_DIR/scheduled_tasks.json"
[ ! -f "$SCRIPT_DIR/external_links.json" ] && echo '[]' > "$SCRIPT_DIR/external_links.json"
[ ! -f "$SCRIPT_DIR/account_plans.json" ] && echo '{}' > "$SCRIPT_DIR/account_plans.json"
ok "Data stores initialized"

# Database setup
if [ "$DB_AVAILABLE" = true ] && [ -n "$DB_PASS" ]; then
    echo ""
    ask "Create database now? ${DIM}(requires postgres superuser)${NC} [Y/n] "
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[nN]$ ]]; then
        # Determine how to run psql as superuser
        if [ "$PLATFORM" = "macos" ]; then
            # macOS Homebrew: current user is usually the superuser
            PSQL_SU="psql -d postgres"
        else
            # Linux: postgres system user
            PSQL_SU="sudo -u postgres psql"
        fi

        # Create user
        if $PSQL_SU -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1; then
            ok "User '$DB_USER' already exists"
        else
            if $PSQL_SU -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null; then
                ok "User '$DB_USER' created"
            else
                warn "Could not create user automatically"
                info "Create manually: $PSQL_SU"
                info "  CREATE USER $DB_USER WITH PASSWORD 'your-password';"
            fi
        fi

        # Create database
        if $PSQL_SU -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1; then
            ok "Database '$DB_NAME' already exists"
        else
            if $PSQL_SU -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null; then
                ok "Database '$DB_NAME' created"
            else
                warn "Could not create database automatically"
                info "Create manually: $PSQL_SU"
                info "  CREATE DATABASE $DB_NAME OWNER $DB_USER;"
            fi
        fi
        info "Tables are created automatically on first start"
    fi
fi

# ============================================================
# 4. Service setup
# ============================================================
echo ""
echo -e "${BOLD}  Start${NC}"
echo ""

if [ "$PLATFORM" = "linux" ]; then
    ask "Install as systemd service? ${DIM}(auto-start on boot)${NC} [Y/n] "
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[nN]$ ]]; then
        SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
        sudo tee "$SERVICE_FILE" > /dev/null <<UNIT
[Unit]
Description=SessionPilot Dashboard
After=network.target postgresql.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=$(which $PYTHON_CMD) ${SCRIPT_DIR}/app.py
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
        sudo systemctl enable "$SERVICE_NAME" &>/dev/null
        sudo systemctl restart "$SERVICE_NAME"

        sleep 2
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            ok "Service running"
        else
            fail "Service failed to start. Check: journalctl -u $SERVICE_NAME -n 20"
        fi
    else
        info "Start manually: $PYTHON_CMD $SCRIPT_DIR/app.py"
    fi
else
    info "Start with: cd $SCRIPT_DIR && $PYTHON_CMD app.py"
fi

# ============================================================
# 5. AI Account detection
# ============================================================
echo ""
echo -e "${BOLD}  AI Accounts${NC}"
echo ""

FOUND_ACCOUNTS=0
for dir in "$HOME"/.claude "$HOME"/.claude-*; do
    if [ -d "$dir/projects" ]; then
        NAME=$(basename "$dir" | sed 's/^\.claude-//' | sed 's/^\.claude$/claude/')
        ok "Claude: ${BOLD}$NAME${NC} ${DIM}($dir)${NC}"
        FOUND_ACCOUNTS=$((FOUND_ACCOUNTS + 1))
    fi
done
[ -d "$HOME/.codex/sessions" ] && { ok "Codex ${DIM}($HOME/.codex)${NC}"; FOUND_ACCOUNTS=$((FOUND_ACCOUNTS + 1)); }
[ -d "$HOME/.gemini/tmp" ] && { ok "Gemini ${DIM}($HOME/.gemini)${NC}"; FOUND_ACCOUNTS=$((FOUND_ACCOUNTS + 1)); }

if [ "$FOUND_ACCOUNTS" -eq 0 ]; then
    warn "No AI coding accounts found"
    info "Sessions will appear once you use Claude Code, Codex, or Gemini CLI"
fi

# ============================================================
# Done
# ============================================================
echo ""
echo -e "  ${GREEN}${BOLD}Done!${NC}"
echo ""
echo -e "  ${BOLD}Open:${NC}  http://localhost:$DASHBOARD_PORT"
echo ""

if [ "$DB_AVAILABLE" = false ]; then
    echo -e "  ${DIM}Tip: Install PostgreSQL to enable Sessions, Timesheets, and Usage Monitor${NC}"
    echo ""
fi
