"""Image downloader for BGS card images."""
import re
from pathlib import Path

import httpx

import config


_SESSION: httpx.Client | None = None


def _session() -> httpx.Client:
    global _SESSION
    if _SESSION is None:
        _SESSION = httpx.Client(
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://www.beckett.com/",
            },
            follow_redirects=True,
        )
    return _SESSION


def _safe_filename(url: str) -> str:
    """Derive a filename from a URL, keeping the extension."""
    path = url.split("?")[0].rstrip("/")
    name = path.split("/")[-1]
    # strip any non-alphanumeric except . - _
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "image.jpg"


def download_image(url: str, dest: Path) -> bool:
    """Download *url* to *dest*. Returns True on success."""
    if not url:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return True  # already downloaded
    try:
        resp = _session().get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def image_paths(card_id: str) -> tuple[Path, Path]:
    """Return (front_path, back_path) for a given card_id."""
    base = Path(config.IMAGES_DIR)
    return base / f"{card_id}_front.jpg", base / f"{card_id}_back.jpg"


def download_card_images(
    card_id: str,
    front_url: str,
    back_url: str,
) -> tuple[str, str]:
    """Download front and back images. Returns (front_path_str, back_path_str)."""
    front_path, back_path = image_paths(card_id)
    download_image(front_url, front_path)
    download_image(back_url, back_path)
    return str(front_path) if front_path.exists() else "", str(back_path) if back_path.exists() else ""
