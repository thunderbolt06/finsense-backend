"""Finance news tool handler using RSS feeds."""
import json
from datetime import datetime
from typing import Any

import feedparser

from utils.http_client import get_async_client
from utils.logging import logger

# Free finance RSS feeds
FINANCE_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=finance",
]


async def get_finance_news(topic: str) -> str:
    """Get finance news articles about a specific topic.

    Args:
        topic: Topic or keyword to search for

    Returns:
        JSON string with finance news articles
    """
    logger.info(
        f"Fetching finance news: topic={topic}"
    )
    
    try:
        topic_lower = topic.lower()
        all_articles: list[dict[str, Any]] = []
        feeds_processed = 0
        feeds_failed = 0
        
        # Fetch and parse RSS feeds
        for feed_url in FINANCE_RSS_FEEDS:
            try:
                # Use httpx to fetch RSS feed
                async with get_async_client() as client:
                    response = await client.get(feed_url, timeout=10.0)
                    response.raise_for_status()
                    feed_content = response.text
                
                # Parse RSS feed
                feed = feedparser.parse(feed_content)
                
                # Filter articles by topic keyword
                for entry in feed.entries[:20]:  # Limit per feed
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    link = entry.get("link", "")
                    
                    # Check if topic appears in title or summary
                    title_lower = title.lower()
                    summary_lower = summary.lower()
                    
                    if topic_lower in title_lower or topic_lower in summary_lower:
                        # Parse published date
                        published = None
                        if "published" in entry:
                            try:
                                published_dt = entry.published_parsed
                                if published_dt:
                                    published = datetime(*published_dt[:6]).isoformat()
                            except Exception:
                                pass
                        
                        all_articles.append({
                            "title": title,
                            "link": link,
                            "summary": summary[:500] if summary else "",  # Limit summary length
                            "published": published or entry.get("published", ""),
                            "source": feed.feed.get("title", "Finance News"),
                        })
                        
            except Exception as e:
                feeds_failed += 1
                logger.warning(
                    f"Error fetching RSS feed {feed_url} for topic {topic}: {e}"
                )
                continue
            
            feeds_processed += 1
        
        # Remove duplicates (by link)
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            if article["link"] not in seen_links:
                seen_links.add(article["link"])
                unique_articles.append(article)
        
        # Sort by published date (most recent first) and limit to top 10
        unique_articles.sort(
            key=lambda x: x["published"] if x["published"] else "",
            reverse=True
        )
        top_articles = unique_articles[:10]
        
        result = {
            "topic": topic,
            "article_count": len(top_articles),
            "articles": top_articles,
        }
        
        if len(top_articles) == 0:
            result["message"] = f"No articles found for topic '{topic}'. Try a different keyword."
            logger.warning(
                f"No finance news articles found for topic '{topic}' (feeds_processed={feeds_processed}, feeds_failed={feeds_failed})"
            )
        else:
            sample_titles = [article["title"][:100] for article in top_articles[:3]]
            logger.info(
                f"Finance news retrieved successfully: {topic} (articles={len(top_articles)}, feeds_processed={feeds_processed}, feeds_failed={feeds_failed}, samples={sample_titles})"
            )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(
            f"Error fetching finance news for topic '{topic}': {e}",
            exc_info=True,
        )
        return json.dumps({
            "error": str(e),
            "topic": topic,
        }, indent=2)

