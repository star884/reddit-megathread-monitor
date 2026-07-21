import json
import os
import sys
from pathlib import Path

import feedparser
import requests

FEED_URL = "https://www.reddit.com/r/Doraemon/comments/1t1w6yf/.rss"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
SEEN_PATH = Path("seen.json")
MAX_SEEN = 300

def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        pass
    return set()

def save_seen(seen: set[str]) -> None:
    trimmed = list(seen)[-MAX_SEEN:]
    SEEN_PATH.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")

def entry_key(entry) -> str:
    # Prefer a stable id if present
    for field in ("id", "guid", "link"):
        value = getattr(entry, field, None)
        if value:
            return str(value)
    # Fallback: title + published
    title = getattr(entry, "title", "")
    published = getattr(entry, "published", "")
    return f"{title}|{published}"

def clean_text(value: str) -> str:
    return " ".join((value or "").split()).strip()

def discord_post(entry) -> None:
    if not WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL is missing")

    author = clean_text(getattr(entry, "author", "Unknown"))
    title = clean_text(getattr(entry, "title", "New Reddit comment"))
    summary = clean_text(getattr(entry, "summary", "")) or clean_text(getattr(entry, "description", ""))
    link = clean_text(getattr(entry, "link", FEED_URL))

    content = None
    if len(summary) > 3500:
        summary = summary[:3500] + "..."

    payload = {
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": summary or "(No text available)",
                "color": 0x5865F2,
                "footer": {"text": f"by {author}"},
            }
        ]
    }

    r = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    r.raise_for_status()

def main() -> int:
    seen = load_seen()

    feed = feedparser.parse(FEED_URL)

    if getattr(feed, "bozo", False):
        # Feed may still be readable even if bozo is set, so do not hard fail unless it is unusable.
        print("Feed parser warning:", getattr(feed, "bozo_exception", "unknown"))

    entries = list(getattr(feed, "entries", []))
    if not entries:
        print("No entries found.")
        return 0

    new_entries = []
    for entry in entries:
        key = entry_key(entry)
        if key not in seen:
            new_entries.append((key, entry))

    # Post oldest new items first
    new_entries.reverse()

    if not new_entries:
        print("No new items.")
        return 0

    for key, entry in new_entries:
        try:
            discord_post(entry)
            seen.add(key)
            print("Posted:", key)
        except Exception as e:
            print(f"Failed to post {key}: {e}", file=sys.stderr)
            return 1

    save_seen(seen)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
