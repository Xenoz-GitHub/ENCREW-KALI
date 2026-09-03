"""Nikto command adapter."""
def command(target: str) -> list[str]:
    return ["nikto", "-host", target, "-Format", "json"]
