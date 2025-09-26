from .youtube import YouTubeProvider
from .instagram import InstagramProvider
from .tiktok import TikTokProvider
from .facebook import FacebookProvider
from .x import XProvider

PROVIDER_CLASS_MAP = {
    "youtube": YouTubeProvider,
    "instagram": InstagramProvider,
    "tiktok": TikTokProvider,
    "facebook": FacebookProvider,
    "x": XProvider,
}

