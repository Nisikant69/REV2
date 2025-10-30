def reverse_string(s: str) -> str:
    """Return the reversed string."""
    return s[::-1]


def capitalize_words(s: str) -> str:
    """Capitalize the first letter of each word in the string."""
    return " ".join(word.capitalize() for word in s.split())
