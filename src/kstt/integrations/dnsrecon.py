"""DNSRecon command adapter."""
def command(domain: str) -> list[str]:
    return ["dnsrecon", "-d", domain, "-j", "-"]
