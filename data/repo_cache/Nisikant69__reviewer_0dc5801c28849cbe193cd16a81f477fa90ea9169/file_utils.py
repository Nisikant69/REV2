def read_file(path: str) -> str:
    """Read text from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    """Write text to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
