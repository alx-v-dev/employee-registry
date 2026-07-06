import re


PHONE_ALLOWED_PATTERN = re.compile(r"^[+\d\s().-]+$")


def normalize_name_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def normalize_phone_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_phone_e164(value: str | None) -> str:
    phone = (value or "").strip()
    if not phone or not phone.startswith("+") or phone.count("+") != 1:
        raise ValueError
    if not PHONE_ALLOWED_PATTERN.fullmatch(phone):
        raise ValueError

    digits = normalize_phone_digits(phone)
    if len(digits) < 8 or len(digits) > 15 or digits.startswith("0"):
        raise ValueError
    return f"+{digits}"


def employee_name_key(last_name: str, first_name: str, middle_name: str | None) -> str:
    return normalize_name_text(" ".join(part for part in (last_name, first_name, middle_name) if part))
