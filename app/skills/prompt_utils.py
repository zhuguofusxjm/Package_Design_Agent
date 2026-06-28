from __future__ import annotations

def render(template: str, **kwargs) -> str:
    """Safely substitute {placeholder} tokens in a template without touching
    other braces (e.g. literal JSON examples inside the prompt).

    Each kwarg key X is replaced wherever {X} appears literally. Brace pairs
    that are not a registered placeholder are left untouched.
    """
    out = template
    for key, value in kwargs.items():
        out = out.replace("{" + key + "}", str(value))
    return out
