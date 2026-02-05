import json
import logging
from typing import Any, Dict, List, Tuple

import anthropic
from sqlalchemy.orm import Session

from newsletter.config import get_settings, get_newsletter_config
from newsletter.models import Post, PostAnalysis, Newsletter, NewsletterItem
from newsletter.analyzer.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER

logger = logging.getLogger(__name__)


def _select_posts_for_sections(
    session: Session, sections: List[Dict[str, Any]]
) -> Dict[str, List[Tuple[Post, PostAnalysis]]]:
    """Select top-scoring posts for each newsletter section."""
    # Get all analyzed posts that aren't skipped
    analyzed = (
        session.query(Post, PostAnalysis)
        .join(PostAnalysis)
        .filter(PostAnalysis.category != "skip")
        .order_by(
            (PostAnalysis.relevance_score + PostAnalysis.quality_score).desc()
        )
        .all()
    )

    used_ids = set()
    grouped = {}

    # First pass: assign top story (highest combined score)
    for section in sections:
        key = section["key"]
        if key != "top_story":
            continue
        max_items = section.get("max_items", 1)
        items = []
        for post, analysis in analyzed:
            if post.id in used_ids:
                continue
            if analysis.category in section.get("categories", []):
                items.append((post, analysis))
                used_ids.add(post.id)
                if len(items) >= max_items:
                    break
        grouped[key] = items

    # Second pass: fill remaining sections
    for section in sections:
        key = section["key"]
        if key == "top_story":
            continue
        max_items = section.get("max_items", 5)
        categories = section.get("categories", [])
        items = []
        for post, analysis in analyzed:
            if post.id in used_ids:
                continue
            if analysis.category in categories:
                items.append((post, analysis))
                used_ids.add(post.id)
                if len(items) >= max_items:
                    break
        grouped[key] = items

    return grouped


def _build_sections_description(sections: List[Dict[str, Any]]) -> str:
    lines = []
    for s in sections:
        lines.append(f"- **{s['title']}** ({s['key']}): {s['description']} [max {s.get('max_items', 5)} items]")
    return "\n".join(lines)


def _build_grouped_posts_json(
    grouped: Dict[str, List[Tuple[Post, PostAnalysis]]]
) -> str:
    data = {}
    for section_key, items in grouped.items():
        data[section_key] = []
        for post, analysis in items:
            data[section_key].append({
                "reddit_id": post.reddit_id,
                "subreddit": post.subreddit,
                "title": post.title,
                "body": post.body[:300] if post.body else "",
                "score": post.score,
                "permalink": post.permalink,
                "category": analysis.category,
                "tool_tags": analysis.tool_tags,
                "summary": analysis.summary,
                "key_insight": analysis.key_insight,
            })
    return json.dumps(data, indent=2)


def _call_claude_synthesize(
    client: anthropic.Anthropic,
    sections_description: str,
    grouped_posts_json: str,
    model: str,
    max_tokens: int,
) -> Dict[str, Any]:
    user_prompt = SYNTHESIS_USER.format(
        sections_description=sections_description,
        grouped_posts_json=grouped_posts_json,
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYNTHESIS_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


def synthesize_newsletter(
    session: Session, frequency: str = "daily"
) -> Newsletter:
    settings = get_settings()
    nl_config = get_newsletter_config()
    sections = nl_config["sections"]
    claude_config = nl_config.get("claude", {})

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = claude_config.get("synthesis_model", "claude-sonnet-4-20250514")
    max_tokens = claude_config.get("max_tokens_synthesis", 4096)

    # Select posts for each section
    grouped = _select_posts_for_sections(session, sections)

    total_posts = sum(len(items) for items in grouped.values())
    if total_posts == 0:
        logger.warning("No posts available for newsletter")
        newsletter = Newsletter(
            edition_title="No posts available",
            frequency=frequency,
            post_count=0,
        )
        session.add(newsletter)
        session.commit()
        return newsletter

    logger.info(f"Synthesizing newsletter from {total_posts} posts across {len(grouped)} sections")

    sections_description = _build_sections_description(sections)
    grouped_posts_json = _build_grouped_posts_json(grouped)

    result = _call_claude_synthesize(
        client, sections_description, grouped_posts_json, model, max_tokens
    )

    # Create newsletter
    newsletter = Newsletter(
        edition_title=result.get("edition_title", "AI Coding Newsletter"),
        frequency=frequency,
        post_count=total_posts,
        metadata_json=result,
    )
    session.add(newsletter)
    session.flush()

    # Create newsletter items
    display_order = 0
    for section_key, items in grouped.items():
        section_data = result.get("sections", {}).get(section_key, {})
        section_items = section_data.get("items", [])
        items_map = {item["reddit_id"]: item for item in section_items}

        for post, analysis in items:
            item_data = items_map.get(post.reddit_id, {})
            ni = NewsletterItem(
                newsletter_id=newsletter.id,
                post_id=post.id,
                section=section_key,
                display_order=display_order,
                headline=item_data.get("headline", post.title),
                blurb=item_data.get("blurb", analysis.summary),
            )
            session.add(ni)
            display_order += 1

    session.commit()
    logger.info(f"Newsletter #{newsletter.id} created: '{newsletter.edition_title}'")
    return newsletter
