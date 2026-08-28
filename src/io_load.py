from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass(frozen=True)
class InputFile:
    organization: str
    persona: str
    path: Path

def discover_exports(data_raw_dir: Path) -> list[InputFile]:
    """
    Expects files stored like:
      data/raw/N=YOU/*Ouders*.xlsx
      data/raw/Levvel/*Jongeren*.xlsx
    """
    inputs: list[InputFile] = []
    for org_dir in data_raw_dir.iterdir():
        if not org_dir.is_dir():
            continue
        org = org_dir.name
        for xlsx in org_dir.glob("*.xlsx"):
            if xlsx.name.startswith("~$") or xlsx.name.startswith("."):
                continue  # skip Excel lock/temp files left behind when a file is open
            name = xlsx.name.lower()
            persona = None
            for p in ["ouders", "jongeren", "hulpverleners", "aanmeldteam"]:
                if p in name:
                    persona = p.title() if p != "aanmeldteam" else "Aanmeldteam"
                    break
            if persona:
                inputs.append(InputFile(org, persona, xlsx))
    return inputs

def read_forms_export(path: Path) -> pd.DataFrame:
    """Reads a Microsoft Forms export (single-sheet xlsx)."""
    return pd.read_excel(path)