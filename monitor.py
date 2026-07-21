import json
import os
from pathlib import Path

import feedparser
import requests

FEED_URL = "https://www.reddit.com/r/Doraemon/comments/1t1w6yf/.rss"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
STATE_PATH = Path("state.json")


def load_state():
    if not STATE_PATH.exists():
        return {"latest_id": None}

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"latest_id": None}


def save_state(latest_id):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"latest_id": latest_id}, f, indent=2)


def entry_key(entry):
    if hasattr(entry, "id"):
        return entry.id
    if hasattr(entry, "guid"):
        return entry.guid
    return entry.link


def discord_post(entry):
    payload = {
        "embeds": [
            {
                "title": getattr(entry, "title", "New Reddit Comment"),
                "url": entry.link,
                "description": getattr(entry, "summary", ""),
                "footer": {
                    "text": f"by {getattr(entry, 'author', 'Unknown')}"
                },
                "color": 0xFF5700
            }
        ]
    }

    r = requests.post(WEBHOOK_URL, json=payload)
    r.raise_for_status()


def main():
    state = load_state()
    latest_seen = state.get("latest_id")

    feed = feedparser.parse(FEED_URL)

    if not feed.entries:
        print("No entries found.")
        return

    newest = entry_key(feed.entries[0])

    # First run
    if latest_seen is None:
        save_state(newest)
        print("First run complete. Current newest comment saved.")
        return

    # No new comments
    if newest == latest_seen:
        print("No new comments.")
        return

    new_comments = []

    for entry in feed.entries:
        if entry_key(entry) == latest_seen:
            break
        new_comments.append(entry)

    # If old comment disappeared from feed, reseed
    if len(new_comments) == len(feed.entries):
        save_state(newest)
        print("Previous comment not found. Reseeded.")
        return

    # Post oldest first
    new_comments.reverse()

    for entry in new_comments:
        discord_post(entry)
        print("Posted:", entry.link)

    save_state(newest)


if __name__ == "__main__":
    main()
