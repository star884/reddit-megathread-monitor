import json
import os
import re
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
    if not WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL is missing")

    author = getattr(entry, "author", "Unknown")

    comment = getattr(entry, "summary", "")
    comment = (
        comment.replace("<br />", "\n")
               .replace("<br/>", "\n")
               .replace("&gt;", ">")
               .replace("&amp;", "&")
    )

    comment = re.sub(r"<[^>]+>", "", comment).strip()

    if len(comment) > 1800:
        comment = comment[:1800] + "..."

    payload = {
        "username": "Reddit Comment Monitor",
        "embeds": [
            {
                "title": f"💬 New comment by u/{author}",
                "description": comment or "*No comment text available.*",
                "url": entry.link,
                "color": 0xFF5700,
                "footer": {
                    "text": "r/Doraemon • Click the title to open the comment"
                }
            }
        ]
    }

    response = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    response.raise_for_status()


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

    # If the previous comment disappeared from the RSS feed,
    # reseed instead of posting everything.
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
