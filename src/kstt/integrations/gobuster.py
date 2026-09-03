"""Gobuster command adapter."""
def command(url: str, wordlist: str) -> list[str]:
    return ["gobuster", "dir", "-u", url, "-w", wordlist, "-q"]
