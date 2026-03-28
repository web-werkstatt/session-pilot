"""Check-Interface und Registry fuer Quality Checks."""

from auto_coder.report import Issue


class BaseCheck:
    """Abstrakte Basisklasse fuer alle Quality Checks."""

    name: str = "base"
    description: str = ""

    def run(self, project_path: str) -> list[Issue]:
        """Fuehrt Check aus, gibt Issues zurueck."""
        raise NotImplementedError

    def is_applicable(self, project_path: str) -> bool:
        """Prueft ob Check fuer dieses Projekt relevant ist."""
        return True
