"""
SPEC-AUDIT-001: Pydantic-Modelle fuer Spec-Audit-System.
Validierung und I/O-Strukturen — kein ORM, kein globales Pattern.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    MUST = "must"
    SHOULD = "should"
    COULD = "could"


class RequirementStatus(str, Enum):
    ERFUELLT = "ERFÜLLT"
    TEILWEISE = "TEILWEISE ERFÜLLT"
    UNSICHER = "UNSICHER"
    FEHLT = "FEHLT"


class OverallStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNSICHER = "UNSICHER"


class Requirement(BaseModel):
    key: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Priority = Priority.MUST
    source: Optional[str] = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    affected_areas: list[str] = Field(default_factory=list)
    sort_order: int = 0
    llm_mode: str = "inherit"


class Spec(BaseModel):
    spec_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=500)
    summary: Optional[str] = None
    project_mode: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    risk_level: Optional[str] = None
    status: str = "draft"
    requirements: list[Requirement] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("spec_id")
    @classmethod
    def spec_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("spec_id darf nicht leer sein")
        return v.strip()

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title darf nicht leer sein")
        return v.strip()


class AuditResult(BaseModel):
    requirement_key: str
    status: RequirementStatus
    notes: Optional[str] = None
    evidence: Optional[dict] = None


class AuditResponse(BaseModel):
    spec_id: str
    spec_title: str = ""
    overall_status: OverallStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_facts: dict = Field(default_factory=dict)
    results: list[AuditResult] = Field(default_factory=list)

    @property
    def duration_ms(self) -> Optional[int]:
        """Laufzeit in Millisekunden, None wenn noch nicht abgeschlossen."""
        if self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return int(delta.total_seconds() * 1000)

    @property
    def summary(self) -> dict:
        """Zaehler pro Status-Kategorie fuer schnellen Ueberblick."""
        counts = {s.value: 0 for s in RequirementStatus}
        for r in self.results:
            counts[r.status.value] += 1
        return {
            "total": len(self.results),
            "by_status": counts,
        }

