"""Nuclei command adapter."""
def command(target: str) -> list[str]:
    return ["nuclei", "-target", target, "-jsonl"]
