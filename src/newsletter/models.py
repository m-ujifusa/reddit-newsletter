from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from newsletter.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reddit_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    subreddit: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    permalink: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(100), default="[deleted]")
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    top_comments: Mapped[List] = mapped_column(JSON, default=list)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    scrape_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("scrape_runs.id"), nullable=True
    )

    analysis: Mapped[Optional["PostAnalysis"]] = relationship(
        back_populates="post", uselist=False
    )
    newsletter_items: Mapped[List["NewsletterItem"]] = relationship(back_populates="post")


class PostAnalysis(Base):
    __tablename__ = "post_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    tool_tags: Mapped[List] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_insight: Mapped[str] = mapped_column(Text, default="")
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    post: Mapped["Post"] = relationship(back_populates="analysis")


class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    edition_title: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    html_content: Mapped[str] = mapped_column(Text, default="")
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[Dict] = mapped_column(JSON, default=dict)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    items: Mapped[List["NewsletterItem"]] = relationship(
        back_populates="newsletter", order_by="NewsletterItem.display_order"
    )


class NewsletterItem(Base):
    __tablename__ = "newsletter_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    newsletter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("newsletters.id"), index=True
    )
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), index=True)
    section: Mapped[str] = mapped_column(String(50))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    headline: Mapped[str] = mapped_column(Text, default="")
    blurb: Mapped[str] = mapped_column(Text, default="")

    newsletter: Mapped["Newsletter"] = relationship(back_populates="items")
    post: Mapped["Post"] = relationship(back_populates="newsletter_items")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="running")
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    new_posts: Mapped[int] = mapped_column(Integer, default=0)
    subreddits_scraped: Mapped[List] = mapped_column(JSON, default=list)
    errors: Mapped[List] = mapped_column(JSON, default=list)

    posts: Mapped[List["Post"]] = relationship()


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
