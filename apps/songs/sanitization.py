import re
import unicodedata


CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HORIZONTAL_SPACE_PATTERN = re.compile(r"[^\S\r\n]+")
EXCESSIVE_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def normalize_text(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = CONTROL_CHAR_PATTERN.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = HORIZONTAL_SPACE_PATTERN.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = EXCESSIVE_NEWLINE_PATTERN.sub("\n\n", text)
    return text.strip()


def normalize_single_line(value):
    return " ".join(normalize_text(value).split())


def quote_for_prompt(value):
    text = normalize_text(value)
    if not text:
        return "None provided."
    escaped = text.replace('"""', '\\"\\"\\"')
    return f'"""{escaped}"""'
