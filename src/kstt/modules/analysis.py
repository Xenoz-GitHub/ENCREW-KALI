"""Observation-to-finding correlation."""
from __future__ import annotations

import hashlib


def finding_from_observation(observation: dict) -> dict:
    evidence = observation.get("error", "")
    title = "Service observation requiring review"
    severity = "INFO"
    confidence = "POSSIBLE"
    if observation.get("kind") == "http" and observation.get("status", "") == "200":
        title = "HTTP service reachable"
    elif evidence:
        title = "Collection error requiring review"
    identifier = hashlib.sha256(f"{title}|{observation.get('target')}|{evidence}".encode()).hexdigest()[:16]
    return {"id": identifier, "title": title, "target": observation.get("target", ""), "service": observation.get("kind", ""), "severity": severity, "confidence": confidence, "evidence": evidence or str(observation), "source": "kstt", "recommendation": "Validate manually within the authorized scope."}
