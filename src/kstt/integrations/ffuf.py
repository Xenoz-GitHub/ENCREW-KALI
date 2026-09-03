"""ffuf command adapter."""
def command(url: str, wordlist: str) -> list[str]:
    return ["ffuf", "-u", url, "-w", wordlist, "-of", "json"]
