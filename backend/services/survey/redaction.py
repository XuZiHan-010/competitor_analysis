import re

EMAIL_PATTERN = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\-\s]{7,}\d)(?!\d)")
CHINESE_NAME_PATTERN = re.compile(r"(姓名|受访者|联系人)[:：]\s*[\u4e00-\u9fa5]{2,4}")


def redact_sensitive_text(text: str) -> str:
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    redacted = CHINESE_NAME_PATTERN.sub(
        lambda match: f"{match.group(1)}：[REDACTED_NAME]", redacted
    )
    return redacted
