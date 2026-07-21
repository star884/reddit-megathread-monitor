import os
import re

import feedparser
import requests

FEED_URL = "https://www.reddit.com/r/Doraemon/comments/1t1w6yf/.rss"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()


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
    feed = feedparser.parse(FEED_URL)

    if not feed.entries:
        print("No comments found.")
        return

    print("Posting newest comment...")
    discord_post(feed.entries[0])
    print("Done.")


if __name__ == "__main__":
    main()
