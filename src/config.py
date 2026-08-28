from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_raw: Path
    data_mapping: Path
    outputs: Path

    @staticmethod
    def from_here() -> "ProjectPaths":
        root = Path(__file__).resolve().parents[1]
        return ProjectPaths(
            root=root,
            data_raw=root / "data" / "raw",
            data_mapping=root / "data" / "mapping",
            outputs=root / "outputs",
        )

PERSONAS = ["Ouders", "Jongeren", "Hulpverleners", "Aanmeldteam"]
ORGS = ["N=YOU", "Levvel"]