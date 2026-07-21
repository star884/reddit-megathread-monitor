import feedparser

FEED_URL = "https://www.reddit.com/r/Doraemon/comments/1t1w6yf/.rss"

feed = feedparser.parse(FEED_URL)

print("Feed title:", feed.feed.get("title"))

print("=" * 80)

entry = feed.entries[0]

for key, value in entry.items():
    print(f"{key}:")
    print(value)
    print("-" * 80)
