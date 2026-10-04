"""
LinkDrop - Input Validators
"""
from typing import Tuple, Optional
from core.security import validate_url_security

def validate_media_url(raw_url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates input URL format and security checks.
    """
    if not raw_url or not isinstance(raw_url, str):
        return False, "Please enter a valid URL.", None

    cleaned = raw_url.strip()
    if len(cleaned) > 2048:
        return False, "URL length exceeds the permissible limit.", None

    is_safe, error_msg, normalized = validate_url_security(cleaned)
    if not is_safe:
        return False, error_msg, None

    return True, "", normalized
