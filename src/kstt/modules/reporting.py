"""Case report generation."""
from __future__ import annotations

import json
from pathlib import Path
from ..database import Database


def export_case(db: Database, case_name: str, directory: Path, fmt: str = "md") -> Path:
    case = db.case(case_name)
    if not case:
        raise ValueError(f"case not found: {case_name}")
    observations = db.observations(case_name)
    findings = [item["data"] for item in db.findings(case_name)]
    payload = {"case": case, "observations": observations, "findings": findings}
    directory.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        path = directory / f"{case_name}.json"; path.write_text(json.dumps(payload, indent=2, default=str))
    else:
        path = directory / f"{case_name}.md"
        lines = [f"# KSTT Report: {case_name}", "", "## Scope", "Case data recorded by KSTT.", "", "## Observations"]
        lines.extend(f"- {item['kind']}: {item['data']}" for item in observations)
        lines += ["", "## Findings"]
        lines.extend(f"- **{item.get('title')}** ({item.get('severity')}, {item.get('confidence')}): {item.get('evidence')}" for item in findings)
        path.write_text("\n".join(lines) + "\n")
    return path
