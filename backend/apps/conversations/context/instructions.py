def normalize_custom_instruction(value: str | None) -> str | None:
    """Normalize blank custom instructions to None."""
    if value is not None and not value.strip():
        return None

    return value


def build_system_instruction(
    platform_instruction: str,
    custom_instruction: str | None,
) -> str:
    """Combine platform and optional custom instructions consistently."""
    if custom_instruction is None:
        return platform_instruction

    return f"{platform_instruction}\n\n{custom_instruction}"
