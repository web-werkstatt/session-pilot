"""
Generischer Markdown-Routine-Service fuer Plan -> Sprint -> Spec -> Marker.

Markdown bleibt die fuehrende Quelle. Dieser Service kapselt:
- robustes Dateilesen mit Encoding-Fallback
- Content-Hash ohne technische Steuer-Marker
- heuristische Klassifikation von Markdown-Dateien
- Tag-Erkennung fuer #sprint-* und #spec-*
- Struktur-Extraktion fuer Sprint-/Spec-Hierarchien
- semantische Abschnittserkennung fuer Legacy-Fallbacks
"""
import hashlib
import os
import re


ENCODING_FALLBACKS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")

DEFAULT_PATTERN_CONFIG = {
    "protect": [
        r"README\.md$",
        r"INSTALL\.md$",
        r"CHANGELOG\.md$",
        r"LICENSE\.md$",
        r"CONTRIBUTING\.md$",
        r"SECURITY\.md$",
        r".*_ANLEITUNG\.md$",
        r".*_GUIDE\.md$",
        r".*_MANUAL\.md$",
        r"CLAUDE\.md$",
    ],
    "allow": [
        r".*sprint.*\.md$",
        r".*plan.*\.md$",
        r".*spec.*\.md$",
    ],
    "technical": [
        r"^##\s+Installation\b",
        r"^##\s+Setup\b",
        r"^##\s+Usage\b",
        r"^##\s+API\b",
        r"^##\s+Configuration\b",
        r"^##\s+Deployment\b",
        r"^##\s+Development\b",
        r"\bnpm run\b",
        r"\bdocker run\b",
        r"\bgit clone\b",
    ],
    "legacy_questions": [
        r"^#{2,4}\s*\*\*[A-Z][0-9]+\.[0-9]+:",
        r"^#{2,4}\s*\*\*[A-Z][0-9]+:",
        r"^#{2,4}\s*\*\*[A-Z][0-9]+\.[0-9]+:.*\*\*$",
        r"^#{2,4}\s*\*\*[A-Z][0-9]+:.*\*\*$",
        r"^#{2,4}\s*\*\*[A-Z][0-9]+\s*[-–]",
        r"^#{3,4}\s*\*\*[0-9]+\.\s+",
        r"^#{2,4}\s*\*\*Frage[0-9\s]*:",
        r"^#{2,4}\s*\*\*Q[0-9]*:",
    ],
    "sprint_heading": [
        r"^#{2,6}\s+.*#sprint-[a-z0-9][a-z0-9-]*\b",
        r"^#{2,6}\s+Sprint\b",
    ],
    "spec_heading": [
        r"^#{3,6}\s+.*#spec-[a-z0-9][a-z0-9-]*\b",
    ],
    "ignored_hash_markers": [
        r"<!--\s*HASH:.*?-->",
        r"<!--\s*File-Hash:.*?-->",
        r"<!--\s*Generated:.*?-->",
        r"<!--\s*Mode:.*?-->",
        r"<!--\s*Lines:.*?-->",
        r"<!--\s*SPLIT_POINT\s*-->",
        r"<!--\s*IMPORTANT\s*-->",
        r"<!--\s*WICHTIG\s*-->",
        r"<!--\s*NO_SPLIT\s*-->",
        r"<!--\s*KEINE_AUFTEILUNG\s*-->",
    ],
}

TAG_RE = re.compile(r"(?P<tag>#(?:sprint|spec)-[a-z0-9][a-z0-9-]*)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
TASK_BULLET_RE = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(?P<task>.+?)\s*$")
PLAN_ID_META_RE = re.compile(
    r"^(?:\*\*)?\s*plan-id\s*:?\s*(?:\*\*)?\s*(?P<plan_id>[a-z0-9_.-]+)\s*$",
    re.IGNORECASE,
)
META_LINE_RE = re.compile(r"^(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,40})\s*:\s*(?P<value>.+?)\s*$")


def _merge_config(config=None):
    merged = {}
    override = config or {}
    for key, values in DEFAULT_PATTERN_CONFIG.items():
        merged[key] = list(override.get(key, values))
    return merged


def _strip_tags(text):
    return TAG_RE.sub("", str(text or "")).strip()


def _slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "item"


def _first_content_line(lines):
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if HEADING_RE.match(stripped):
            continue
        if META_LINE_RE.match(stripped):
            continue
        match = TASK_BULLET_RE.match(line)
        if match:
            return match.group("task").strip()
        return stripped
    return ""


def _find_tags_in_line(line):
    return [match.group("tag").lower() for match in TAG_RE.finditer(str(line or ""))]


def _extract_meta_tags(lines, start_idx):
    tags = []
    meta = {}
    idx = start_idx + 1
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if HEADING_RE.match(stripped):
            break
        tags.extend(_find_tags_in_line(stripped))
        meta_match = META_LINE_RE.match(stripped)
        if meta_match:
            meta[meta_match.group("label").strip().lower()] = meta_match.group("value").strip()
            idx += 1
            continue
        break
    return tags, meta


def _extract_plan_id_from_meta(meta):
    if not meta:
        return ""
    for key, value in meta.items():
        if key.replace(" ", "-") == "plan-id":
            return str(value).strip()
    return ""


def _finalize_section(section):
    if not section:
        return section
    title = _strip_tags(section.get("raw_title") or "")
    section["title"] = title
    section["description"] = _first_content_line(section.get("lines") or [])
    return section


def read_markdown_with_fallback(path):
    """Liest Markdown mit mehreren Encodings und liefert Inhalt plus Encoding."""
    last_error = None
    for encoding in ENCODING_FALLBACKS:
        try:
            with open(path, "r", encoding=encoding) as f:
                return {
                    "path": path,
                    "content": f.read(),
                    "encoding": encoding,
                }
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise UnicodeDecodeError(
        getattr(last_error, "encoding", "unknown"),
        getattr(last_error, "object", b""),
        getattr(last_error, "start", 0),
        getattr(last_error, "end", 1),
        f"Kann Encoding fuer {path} nicht ermitteln",
    )


def compute_content_hash(text_or_lines, config=None):
    """Berechnet einen stabilen Hash ohne technische Steuer-Marker."""
    merged = _merge_config(config)
    if isinstance(text_or_lines, list):
        lines = [str(line) for line in text_or_lines]
    else:
        lines = str(text_or_lines or "").splitlines(True)

    clean_lines = []
    for line in lines:
        cleaned = line
        for pattern in merged["ignored_hash_markers"]:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        if cleaned.strip():
            clean_lines.append(cleaned.rstrip() + "\n")

    payload = "".join(clean_lines).strip()
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def classify_markdown_content(path, content, config=None):
    """Ordnet Markdown heuristisch in einen Routing-Typ ein."""
    merged = _merge_config(config)
    normalized_path = os.path.basename(str(path or ""))
    lines = str(content or "").splitlines()
    joined = "\n".join(lines)

    for pattern in merged["protect"]:
        if re.match(pattern, normalized_path, re.IGNORECASE):
            return {
                "classification": "technical_documentation",
                "reason": f"protected_filename:{pattern}",
                "confidence": 0.95,
            }

    sprint_hits = sum(1 for pattern in merged["sprint_heading"] if re.search(pattern, joined, re.IGNORECASE | re.MULTILINE))
    spec_hits = sum(1 for pattern in merged["spec_heading"] if re.search(pattern, joined, re.IGNORECASE | re.MULTILINE))
    technical_hits = sum(1 for pattern in merged["technical"] if re.search(pattern, joined, re.IGNORECASE | re.MULTILINE))
    legacy_question_hits = sum(len(re.findall(pattern, joined, re.IGNORECASE | re.MULTILINE)) for pattern in merged["legacy_questions"])
    tag_hits = len(TAG_RE.findall(joined))

    if sprint_hits or tag_hits:
        return {
            "classification": "sprint_like" if sprint_hits or any(tag.startswith("#sprint-") for tag in TAG_RE.findall(joined)) else "spec_like",
            "reason": "sprint_or_tag_structure_detected",
            "confidence": 0.84 if tag_hits else 0.72,
        }

    if spec_hits:
        return {
            "classification": "spec_like",
            "reason": "spec_structure_detected",
            "confidence": 0.72,
        }

    if legacy_question_hits >= 2 and technical_hits < 2:
        return {
            "classification": "question_catalog_like",
            "reason": "legacy_question_patterns",
            "confidence": 0.78,
        }

    if technical_hits >= 2:
        return {
            "classification": "technical_documentation",
            "reason": "technical_patterns",
            "confidence": 0.82,
        }

    return {
        "classification": "general_documentation",
        "reason": "fallback",
        "confidence": 0.4,
    }


def extract_markdown_tags(content):
    """Extrahiert Sprint-/Spec-Tags nur aus Heading- oder direkter Meta-Zeile."""
    lines = str(content or "").splitlines()
    tags = []
    for idx, line in enumerate(lines):
        heading = HEADING_RE.match(line.strip())
        if not heading:
            continue
        heading_tags = _find_tags_in_line(line)
        meta_tags, meta = _extract_meta_tags(lines, idx)
        all_tags = heading_tags + meta_tags
        for tag in all_tags:
            tags.append({
                "tag": tag,
                "kind": "sprint" if tag.startswith("#sprint-") else "spec",
                "line": idx + 1,
                "heading_level": len(heading.group("level")),
                "heading_title": _strip_tags(heading.group("title")),
                "source": "heading" if tag in heading_tags else "meta",
                "meta": meta,
            })
    return tags


def detect_semantic_split_points(content, config=None):
    """Liefert semantische Abschnittsgrenzen fuer Legacy-Fallbacks."""
    merged = _merge_config(config)
    lines = str(content or "").splitlines()
    points = [{"line": 1, "reason": "start"}] if lines else []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if HEADING_RE.match(stripped):
            points.append({"line": idx + 1, "reason": "heading"})
        if re.match(r"^---+\s*$", stripped):
            points.append({"line": idx + 1, "reason": "separator"})
            continue
        for pattern in merged["legacy_questions"]:
            if re.match(pattern, stripped, re.IGNORECASE):
                points.append({"line": idx + 1, "reason": "legacy_question"})
                break

    unique = []
    seen = set()
    for point in points:
        key = (point["line"], point["reason"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique


def scan_markdown_structure(content, source_path="", config=None):
    """Extrahiert Sprint-/Spec-Struktur aus Markdown."""
    lines = str(content or "").splitlines()
    classification = classify_markdown_content(source_path, content, config=config)
    tags = extract_markdown_tags(content)
    sections = []
    current_sprint = None
    current_spec = None

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        heading = HEADING_RE.match(line)
        if not heading:
            if current_spec is not None:
                current_spec["lines"].append(raw_line)
                task_match = TASK_BULLET_RE.match(raw_line)
                if task_match:
                    current_spec["tasks"].append(task_match.group("task").strip())
            elif current_sprint is not None:
                current_sprint["lines"].append(raw_line)
                task_match = TASK_BULLET_RE.match(raw_line)
                if task_match:
                    current_sprint["tasks"].append(task_match.group("task").strip())
            continue

        level = len(heading.group("level"))
        raw_title = heading.group("title").strip()
        heading_tags = _find_tags_in_line(raw_title)
        meta_tags, meta = _extract_meta_tags(lines, idx)
        combined_tags = heading_tags + meta_tags
        sprint_tag = next((tag for tag in combined_tags if tag.startswith("#sprint-")), "")
        spec_tag = next((tag for tag in combined_tags if tag.startswith("#spec-")), "")
        title = _strip_tags(raw_title)
        plan_id = _extract_plan_id_from_meta(meta)

        if sprint_tag or title.lower().startswith("sprint "):
            if current_spec is not None:
                current_sprint["specs"].append(_finalize_section(current_spec))
                current_spec = None
            if current_sprint is not None:
                sections.append(_finalize_section(current_sprint))
            current_sprint = {
                "type": "sprint",
                "line": idx + 1,
                "level": level,
                "raw_title": raw_title,
                "title": title,
                "sprint_tag": sprint_tag,
                "plan_id": plan_id,
                "meta": meta,
                "lines": [],
                "tasks": [],
                "specs": [],
            }
            continue

        if current_sprint is not None and level > current_sprint["level"]:
            if current_spec is not None:
                current_sprint["specs"].append(_finalize_section(current_spec))
            current_spec = {
                "type": "spec",
                "line": idx + 1,
                "level": level,
                "raw_title": raw_title,
                "title": title,
                "spec_tag": spec_tag,
                "meta": meta,
                "lines": [],
                "tasks": [],
            }

    if current_spec is not None and current_sprint is not None:
        current_sprint["specs"].append(_finalize_section(current_spec))
    if current_sprint is not None:
        sections.append(_finalize_section(current_sprint))

    return {
        "source_path": source_path,
        "classification": classification,
        "tags": tags,
        "sprints": sections,
        "split_points": detect_semantic_split_points(content, config=config),
        "content_hash": compute_content_hash(content, config=config),
    }


def suggest_tag_from_title(title, prefix):
    """Erzeugt einen stabilen lesbaren Tag aus einem Titel."""
    normalized_prefix = str(prefix or "").strip("#").strip()
    if normalized_prefix not in ("sprint", "spec"):
        raise ValueError("prefix muss sprint oder spec sein")
    return f"#{normalized_prefix}-{_slugify(title)}"


def build_tag_update_plan(content):
    """Ermittelt fehlende Sprint-/Spec-Tags und liefert einen Update-Plan."""
    lines = str(content or "").splitlines()
    updates = []
    current_sprint_level = None

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        heading = HEADING_RE.match(stripped)
        if not heading:
            continue

        level = len(heading.group("level"))
        raw_title = heading.group("title").strip()
        title = _strip_tags(raw_title)
        heading_tags = _find_tags_in_line(raw_title)
        meta_tags, _ = _extract_meta_tags(lines, idx)
        all_tags = heading_tags + meta_tags
        has_sprint_tag = any(tag.startswith("#sprint-") for tag in all_tags)
        has_spec_tag = any(tag.startswith("#spec-") for tag in all_tags)
        is_sprint_heading = title.lower().startswith("sprint ")

        if is_sprint_heading:
            current_sprint_level = level
            if not has_sprint_tag:
                updates.append({
                    "line_index": idx,
                    "line_number": idx + 1,
                    "kind": "sprint",
                    "title": title,
                    "tag": suggest_tag_from_title(title, "sprint"),
                })
            continue

        if current_sprint_level is not None and level > current_sprint_level and not has_spec_tag:
            updates.append({
                "line_index": idx,
                "line_number": idx + 1,
                "kind": "spec",
                "title": title,
                "tag": suggest_tag_from_title(title, "spec"),
            })
            continue

        if current_sprint_level is not None and level <= current_sprint_level:
            current_sprint_level = None

    return updates


def apply_tag_update_plan(content, updates):
    """Schreibt fehlende Tags direkt in die Heading-Zeile."""
    if not updates:
        return str(content or "")

    lines = str(content or "").splitlines()
    updates_by_index = {item["line_index"]: item for item in updates}

    for idx, raw_line in enumerate(lines):
        update = updates_by_index.get(idx)
        if not update:
            continue
        heading = HEADING_RE.match(raw_line.strip())
        if not heading:
            continue
        if update["tag"] in raw_line:
            continue
        prefix = heading.group("level")
        title = heading.group("title").strip()
        cleaned_title = _strip_tags(title)
        lines[idx] = f"{prefix} {cleaned_title} {update['tag']}"

    updated = "\n".join(lines)
    if str(content or "").endswith("\n"):
        updated += "\n"
    return updated
