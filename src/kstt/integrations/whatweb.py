"""WhatWeb command adapter."""
def command(target: str) -> list[str]:
    return ["whatweb", "--log-json=-", target]
