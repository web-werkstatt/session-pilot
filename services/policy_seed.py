"""
ADR-002 Stufe 1b: Seed-Defaults fuer Policy-Schicht.

Expliziter Bootstrap-Aufruf fuer eine initiale Rollen- und Tool-Profile-
Liste. Wird NICHT automatisch beim Boot ausgefuehrt - nur auf expliziten
Wunsch (Admin-Button im UI, Python-Shell-Aufruf, REST-Endpoint).

Die Seed-Daten sind Vorschlaege, keine harte Wahrheit. Joseph kann sie
jederzeit via upsert_role / upsert_tool_profile aendern, deaktivieren
oder ergaenzen. Re-Run ueberschreibt bestehende Eintraege NICHT - nur
neue Defaults werden hinzugefuegt. Damit bleiben manuelle Anpassungen
von Joseph erhalten, auch wenn spaeter neue Defaults ergaenzt werden.

Es werden keine initialen role_tool_policies angelegt. Die muessen
manuell gesetzt werden oder durch Perplexity-Reviews entstehen und
dann von Joseph approved werden.
"""
from typing import Any, Dict, List

from services.policy_service import (
    get_role,
    get_tool_profile,
    upsert_role,
    upsert_tool_profile,
)


# Sechs Arbeits-Rollen als Vorschlag. Aenderbar, erweiterbar.
DEFAULT_ROLES: List[Dict[str, Any]] = [
    {
        "role_id": "programming",
        "name": "Programming / Backend",
        "description": "Backend-Implementierung, APIs, Services, Refactors, modulare Codearbeit.",
    },
    {
        "role_id": "saas_webdesign",
        "name": "SaaS / Webdesign",
        "description": "SaaS-Flows, Landingpages, visuelles UI, Positionierung, produktnahe Web-Erlebnisse.",
    },
    {
        "role_id": "ux_ui",
        "name": "UX / UI",
        "description": "Nutzerfluss, Screens, Design-Regeln, Komponenten, Frontend-Feinschliff.",
    },
    {
        "role_id": "code_fix",
        "name": "Code-Fix / Cleanup",
        "description": "Fixes, Dead Code, Regression-Risiken, Stilkonformitaet, kleinere Korrektur-Patches.",
    },
    {
        "role_id": "quality_review",
        "name": "Quality Review",
        "description": "Qualitaetspruefung, Test-Auswertung, Review von Code-Aenderungen, Second Pass.",
    },
    {
        "role_id": "research_review",
        "name": "Research / Review",
        "description": "Architektur-Abgleich, externe Recherche, Meta-Review, Konsistenzpruefung.",
    },
]


# Fuenf Tool-Profile als Vorschlag. strengths/weaknesses bewusst leer,
# damit sie durch Review-Historie oder manuelle Pflege entstehen,
# nicht spekulativ gesetzt werden.
DEFAULT_TOOL_PROFILES: List[Dict[str, Any]] = [
    {
        "tool_id": "claude-code-opus-4-6",
        "cli": "claude-code",
        "model": "claude-opus-4-6",
        "provider": "anthropic",
        "notes": "Claude Code CLI mit Opus 4.6 (1M Context).",
    },
    {
        "tool_id": "codex",
        "cli": "codex",
        "model": None,
        "provider": "openai",
        "notes": "OpenAI Codex CLI. Modell wird von CLI gewaehlt.",
    },
    {
        "tool_id": "gemini-cli",
        "cli": "gemini-cli",
        "model": None,
        "provider": "google",
        "notes": "Gemini CLI. Modell wird von CLI gewaehlt.",
    },
    {
        "tool_id": "hermes",
        "cli": "hermes",
        "model": None,
        "provider": "nousresearch",
        "notes": "Hermes / Nous Research. Zweitmodell fuer Review- und Fix-Pfade.",
    },
    {
        "tool_id": "perplexity",
        "cli": "perplexity-api",
        "model": "sonar",
        "provider": "perplexity",
        "notes": "Perplexity in der Reviewer-Rolle der AI-Control-Plane. Nicht als Executor vorgesehen.",
    },
]


def seed_defaults() -> Dict[str, int]:
    """Legt Default-Rollen und Tool-Profile an, wenn sie noch nicht existieren.

    Idempotent: Bestehende Eintraege werden NICHT ueberschrieben - Josephs
    manuelle Anpassungen (z.B. deaktivierte Rollen, geaenderte Namen)
    bleiben erhalten. Re-Run kann spaeter hinzugefuegte Defaults nachziehen.

    Returns:
        Dict mit Count-Infos: {'roles_created': n, 'tool_profiles_created': n}.
    """
    roles_created = 0
    for role in DEFAULT_ROLES:
        if get_role(role["role_id"]) is None:
            upsert_role(
                role_id=role["role_id"],
                name=role["name"],
                description=role.get("description"),
                active=True,
            )
            roles_created += 1

    profiles_created = 0
    for profile in DEFAULT_TOOL_PROFILES:
        if get_tool_profile(profile["tool_id"]) is None:
            upsert_tool_profile(
                tool_id=profile["tool_id"],
                cli=profile["cli"],
                model=profile.get("model"),
                provider=profile.get("provider"),
                strengths=None,
                weaknesses=None,
                notes=profile.get("notes"),
                active=True,
            )
            profiles_created += 1

    return {
        "roles_created": roles_created,
        "tool_profiles_created": profiles_created,
    }
