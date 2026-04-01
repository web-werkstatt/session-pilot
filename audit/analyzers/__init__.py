"""
SPEC-AUDIT-ANALYZER-LLM-001 + GATING-001: LLM-basierter Audit-Analyzer via Perplexity.
Opt-in via AUDIT_LLM_ANALYZER_ENABLED=1. Gating via AUDIT_LLM_DEFAULT_MODE,
AUDIT_LLM_ALLOWED_PRIORITIES, AUDIT_LLM_ALLOWED_RISK_LEVELS und per-Requirement llm_mode.
Aendert niemals AuditResult.status, ergaenzt nur evidence["llm_review"].
"""
import json

from config import (
    AUDIT_LLM_ANALYZER_ENABLED,
    AUDIT_LLM_MAX_REQUIREMENTS,
    AUDIT_LLM_DEFAULT_MODE,
    AUDIT_LLM_ALLOWED_PRIORITIES,
    AUDIT_LLM_ALLOWED_RISK_LEVELS,
)


# ---------------------------------------------------------------------------
# Prompt-Bausteine
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Du bist ein Code-Review-Assistent fuer ein Spec-Audit-System.
Du bewertest, ob geaenderte Dateien realistisch ein bestimmtes Requirement abdecken.

Antworte ausschliesslich mit validem JSON in diesem Format:
{"opinion": "<confirm|strengthen|question|unknown>", "comment": "<kurze Begruendung>"}

Regeln:
- "confirm": Die geaenderten Dateien decken das Requirement plausibel ab.
- "strengthen": Die Dateien decken es ab UND gehen darueber hinaus.
- "question": Zweifel, ob die Dateien das Requirement wirklich erfuellen.
- "unknown": Nicht genug Information fuer eine Einschaetzung.
- Keine spekulativen Aussagen ohne Bezug zu den gegebenen Inputs.
- Antworte NUR mit dem JSON-Objekt, kein weiterer Text."""


def _build_user_prompt(spec_id, req, current_status, changed_files):
    """Baut den User-Prompt fuer ein einzelnes Requirement."""
    criteria_text = ""
    if req.acceptance_criteria:
        criteria_text = "\n".join(f"- {c}" for c in req.acceptance_criteria)

    areas_text = ", ".join(req.affected_areas) if req.affected_areas else "(keine)"
    files_text = ", ".join(changed_files[:50]) if changed_files else "(keine)"

    parts = [
        f"Spec: {spec_id}",
        f"Requirement: {req.key} - {req.title}",
    ]
    if req.description:
        parts.append(f"Beschreibung: {req.description}")
    if criteria_text:
        parts.append(f"Akzeptanzkriterien:\n{criteria_text}")
    parts.append(f"Betroffene Bereiche: {areas_text}")
    parts.append(f"Geaenderte Dateien: {files_text}")
    parts.append(f"Bisheriger Status (regelbasiert): {current_status}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LLM-Antwort parsen
# ---------------------------------------------------------------------------

_VALID_OPINIONS = {"confirm", "strengthen", "question", "unknown"}


def _parse_llm_response(content):
    """Extrahiert opinion + comment aus LLM-Antwort. Gibt dict oder None."""
    try:
        # LLM koennte JSON in Markdown-Codeblock wrappen
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        data = json.loads(text)
        opinion = data.get("opinion", "").lower().strip()
        comment = data.get("comment", "").strip()

        if opinion not in _VALID_OPINIONS:
            opinion = "unknown"
        if not comment:
            comment = "(kein Kommentar)"

        return {"opinion": opinion, "comment": comment}
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Einzelnes Requirement analysieren
# ---------------------------------------------------------------------------

def _analyze_single_requirement(spec_id, req, result, changed_files):
    """Ruft Perplexity fuer ein Requirement auf, gibt erweiterten AuditResult zurueck."""
    from services.perplexity_service import (
        PerplexityAPIError,
        PerplexityConfigError,
        PerplexityRequestError,
        query_perplexity,
    )

    user_msg = _build_user_prompt(spec_id, req, result.status.value, changed_files)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    evidence = dict(result.evidence) if result.evidence else {}

    try:
        response = query_perplexity(messages, temperature=0.0)
        parsed = _parse_llm_response(response.get("content", ""))

        if parsed:
            evidence["llm_review"] = parsed
        else:
            evidence["llm_review"] = {"opinion": "unknown", "comment": "LLM-Antwort nicht parsbar"}

    except (PerplexityConfigError, PerplexityRequestError, PerplexityAPIError) as e:
        evidence["llm_review_error"] = str(e)
    except Exception as e:
        evidence["llm_review_error"] = f"Unerwarteter Fehler: {e}"

    return result.model_copy(update={"evidence": evidence})


# ---------------------------------------------------------------------------
# Gating: Config-Parser
# ---------------------------------------------------------------------------

def _parse_csv_filter(raw):
    """Parst comma-separated String in ein Set. Leerer String = leeres Set."""
    if not raw or not raw.strip():
        return set()
    return {v.strip().lower() for v in raw.split(",") if v.strip()}


# Gecacht pro Prozess (Modul-Level)
_ALLOWED_PRIORITIES = _parse_csv_filter(AUDIT_LLM_ALLOWED_PRIORITIES)
_ALLOWED_RISK_LEVELS = _parse_csv_filter(AUDIT_LLM_ALLOWED_RISK_LEVELS)


# ---------------------------------------------------------------------------
# Gating: Entscheidung pro Requirement
# ---------------------------------------------------------------------------

def _should_run_llm(spec, requirement):
    """Entscheidet ob LLM-Analyzer fuer dieses Requirement laufen soll.

    Evaluation-Order:
    1. DEFAULT_MODE == "off" -> False
    2. ANALYZER_ENABLED == False -> False
    3. requirement.llm_mode == "off" -> False
    4. requirement.llm_mode == "on" -> True
    5. Priority-Filter (wenn gesetzt)
    6. Risk-Level-Filter auf Spec-Ebene (wenn gesetzt)
    7. Sonst: True
    """
    if AUDIT_LLM_DEFAULT_MODE == "off":
        return False

    if not AUDIT_LLM_ANALYZER_ENABLED:
        return False

    llm_mode = getattr(requirement, "llm_mode", "inherit")

    if llm_mode == "off":
        return False
    if llm_mode == "on":
        return True

    # Filter: Priority
    if _ALLOWED_PRIORITIES:
        req_prio = requirement.priority.value.lower() if hasattr(requirement.priority, "value") else str(requirement.priority).lower()
        if req_prio not in _ALLOWED_PRIORITIES:
            return False

    # Filter: Risk-Level (Spec-Ebene)
    if _ALLOWED_RISK_LEVELS:
        spec_risk = (getattr(spec, "risk_level", None) or "").lower()
        if spec_risk not in _ALLOWED_RISK_LEVELS:
            return False

    return True


# ---------------------------------------------------------------------------
# Public hook
# ---------------------------------------------------------------------------

def run_analyzers(spec, results, input_facts):
    """Hook fuer audit/service.py. Gibt results zurueck, ggf. mit LLM-Evidence.

    Gating bestimmt pro Requirement ob LLM laeuft. Max AUDIT_LLM_MAX_REQUIREMENTS
    LLM-Calls pro Audit-Lauf.
    """
    if AUDIT_LLM_DEFAULT_MODE == "off":
        return results
    if not AUDIT_LLM_ANALYZER_ENABLED:
        return results

    changed_files = input_facts.get("changed_files", [])
    llm_calls = 0

    enriched = []
    for result in results:
        req = _find_requirement(spec, result.requirement_key)
        if req and llm_calls < AUDIT_LLM_MAX_REQUIREMENTS and _should_run_llm(spec, req):
            result = _analyze_single_requirement(
                spec.spec_id, req, result, changed_files
            )
            llm_calls += 1
        enriched.append(result)

    return enriched


def _find_requirement(spec, key):
    """Findet Requirement by key in spec."""
    for req in spec.requirements:
        if req.key == key:
            return req
    return None
