"""Detection of optional Kali utilities."""
from __future__ import annotations

import shutil

TOOLS = ["nmap", "masscan", "rustscan", "naabu", "nikto", "nuclei", "ffuf", "feroxbuster", "gobuster", "whatweb", "sqlmap", "hydra", "john", "hashcat", "nc", "socat", "tcpdump", "tshark", "dig", "dnsrecon", "subfinder", "amass", "enum4linux-ng", "smbclient", "ldapsearch", "nxc", "bloodhound-python", "searchsploit", "msfconsole"]


def detect_tools() -> list[dict[str, str]]:
    found = []
    for name in TOOLS:
        path = shutil.which(name)
        version = "-"
        if path:
            from .runner import run_command
            result = run_command([path, "--version"], timeout=5)
            text = (result.stdout or result.stderr).splitlines()
            version = text[0][:60] if text else "installed"
        found.append({"tool": name, "status": "Installed" if path else "Missing", "version": version})
    return found
