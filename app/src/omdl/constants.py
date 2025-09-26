import re

PROVIDERS = ("youtube", "instagram", "tiktok", "facebook", "x")

URL_PATTERNS = {
    "youtube": re.compile(
        r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", re.IGNORECASE
    ),
    "instagram": re.compile(r"(https?://)?(www\.)?instagram\.com/.+", re.IGNORECASE),
    "tiktok": re.compile(r"(https?://)?(www\.)?tiktok\.com/.+", re.IGNORECASE),
    "facebook": re.compile(r"(https?://)?(www\.)?facebook\.com/.+", re.IGNORECASE),
    "x": re.compile(r"(https?://)?(www\.)?(twitter\.com|x\.com)/.+", re.IGNORECASE),
}
