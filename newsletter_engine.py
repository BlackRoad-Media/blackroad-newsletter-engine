#!/usr/bin/env python3
"""
BlackRoad Newsletter Engine - Email newsletter creation, scheduling, and analytics
"""

import sqlite3
import uuid
import json
import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum


class SubscriberStatus(str, Enum):
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


class NewsletterStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Subscriber:
    id: str
    email: str
    name: str
    tags: str  # JSON list stored as string
    status: str = SubscriberStatus.ACTIVE.value
    open_rate: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @property
    def tags_list(self) -> List[str]:
        return json.loads(self.tags or "[]")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Newsletter:
    id: str
    subject: str
    body_md: str
    preview_text: str
    status: str = NewsletterStatus.DRAFT.value
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    recipient_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def word_count(self) -> int:
        return len(self.body_md.split())

    @property
    def estimated_read_time_min(self) -> int:
        return max(1, self.word_count // 200)


@dataclass
class SendRecord:
    id: str
    newsletter_id: str
    subscriber_id: str
    sent_at: str
    opened: bool = False
    clicked: bool = False
    bounced: bool = False
    opened_at: Optional[str] = None
    clicked_at: Optional[str] = None
    click_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Segment:
    name: str
    tags: List[str]
    subscriber_count: int
    created_at: str = field(default_factory=_now)


class NewsletterEngine:
    """Email newsletter creation, scheduling, and analytics engine."""

    BATCH_SIZE = 100  # subscribers per sending batch

    def __init__(self, db_path: str = "newsletter.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'active',
                    open_rate REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS newsletters (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    body_md TEXT NOT NULL,
                    preview_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    scheduled_at TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    recipient_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS send_records (
                    id TEXT PRIMARY KEY,
                    newsletter_id TEXT NOT NULL,
                    subscriber_id TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    opened INTEGER DEFAULT 0,
                    clicked INTEGER DEFAULT 0,
                    bounced INTEGER DEFAULT 0,
                    opened_at TEXT,
                    clicked_at TEXT,
                    click_url TEXT,
                    FOREIGN KEY (newsletter_id) REFERENCES newsletters(id),
                    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
                );

                CREATE TABLE IF NOT EXISTS unsubscribe_log (
                    id TEXT PRIMARY KEY,
                    subscriber_id TEXT NOT NULL,
                    newsletter_id TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_send_records_newsletter
                    ON send_records(newsletter_id);
                CREATE INDEX IF NOT EXISTS idx_send_records_subscriber
                    ON send_records(subscriber_id);
                CREATE INDEX IF NOT EXISTS idx_subscribers_status
                    ON subscribers(status);
            """)

    # ── Subscriber Management ──────────────────────────────────────────────

    def subscribe(self, email: str, name: str, tags: List[str] = None) -> Subscriber:
        """Add a new subscriber or reactivate an existing one."""
        email = email.lower().strip()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError(f"Invalid email: {email}")

        tags = tags or []
        sub_id = str(uuid.uuid4())
        now = _now()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM subscribers WHERE email=?", (email,)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE subscribers SET status='active', tags=?, updated_at=? WHERE email=?
                """, (json.dumps(tags), now, email))
                row = conn.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
                return Subscriber(**dict(row))
            else:
                conn.execute("""
                    INSERT INTO subscribers (id, email, name, tags, status, open_rate, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'active', 0.0, ?, ?)
                """, (sub_id, email, name, json.dumps(tags), now, now))

        return self.get_subscriber_by_email(email)

    def unsubscribe(self, email: str, reason: str = "") -> bool:
        """Unsubscribe a subscriber."""
        email = email.lower().strip()
        now = _now()
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM subscribers WHERE email=?", (email,)).fetchone()
            if not row:
                return False
            conn.execute("""
                UPDATE subscribers SET status='unsubscribed', updated_at=? WHERE email=?
            """, (now, email))
            conn.execute("""
                INSERT INTO unsubscribe_log (id, subscriber_id, reason, created_at)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), row["id"], reason, now))
        return True

    def mark_bounced(self, email: str) -> bool:
        """Mark an email as bounced."""
        email = email.lower().strip()
        with self._connect() as conn:
            result = conn.execute("""
                UPDATE subscribers SET status='bounced', updated_at=? WHERE email=?
            """, (_now(), email))
        return result.rowcount > 0

    def get_subscriber_by_email(self, email: str) -> Optional[Subscriber]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM subscribers WHERE email=?", (email.lower(),)).fetchone()
        return Subscriber(**dict(row)) if row else None

    def get_subscriber(self, sub_id: str) -> Optional[Subscriber]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sub_id,)).fetchone()
        return Subscriber(**dict(row)) if row else None

    def segment(self, tags: List[str]) -> List[Subscriber]:
        """Get active subscribers matching any of the given tags."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM subscribers WHERE status='active'"
            ).fetchall()
        result = []
        for row in rows:
            sub = Subscriber(**dict(row))
            sub_tags = set(sub.tags_list)
            if any(t in sub_tags for t in tags):
                result.append(sub)
        return result

    def list_subscribers(self, status: Optional[str] = None,
                         limit: int = 100) -> List[Subscriber]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM subscribers WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM subscribers ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [Subscriber(**dict(r)) for r in rows]

    def subscriber_count(self, status: str = "active") -> int:
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM subscribers WHERE status=?", (status,)
            ).fetchone()[0]

    # ── Newsletter Management ──────────────────────────────────────────────

    def create_newsletter(self, subject: str, body_md: str,
                          preview: str = "") -> Newsletter:
        """Create a new newsletter draft."""
        nl_id = str(uuid.uuid4())
        now = _now()
        preview = preview or body_md[:100].replace("\n", " ")
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO newsletters
                (id, subject, body_md, preview_text, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'draft', ?, ?)
            """, (nl_id, subject, body_md, preview, now, now))
        return self.get_newsletter(nl_id)

    def update_newsletter(self, nl_id: str, **kwargs) -> Optional[Newsletter]:
        """Update newsletter fields."""
        nl = self.get_newsletter(nl_id)
        if not nl:
            return None
        allowed = {"subject", "body_md", "preview_text"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return nl
        set_clause = ", ".join(f"{k}=?" for k in updates)
        set_clause += ", updated_at=?"
        values = list(updates.values()) + [_now(), nl_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE newsletters SET {set_clause} WHERE id=?", values)
        return self.get_newsletter(nl_id)

    def get_newsletter(self, nl_id: str) -> Optional[Newsletter]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM newsletters WHERE id=?", (nl_id,)).fetchone()
        return Newsletter(**dict(row)) if row else None

    def schedule(self, newsletter_id: str, send_at: str) -> Newsletter:
        """Schedule a newsletter for sending at a specific time."""
        nl = self.get_newsletter(newsletter_id)
        if not nl:
            raise ValueError(f"Newsletter {newsletter_id} not found")
        if nl.status not in (NewsletterStatus.DRAFT.value, NewsletterStatus.SCHEDULED.value):
            raise ValueError(f"Cannot schedule newsletter in status '{nl.status}'")

        with self._connect() as conn:
            conn.execute("""
                UPDATE newsletters SET status='scheduled', scheduled_at=?, updated_at=?
                WHERE id=?
            """, (send_at, _now(), newsletter_id))
        return self.get_newsletter(newsletter_id)

    def send(self, newsletter_id: str,
             target_tags: Optional[List[str]] = None) -> dict:
        """Send a newsletter to active subscribers (batch processing)."""
        nl = self.get_newsletter(newsletter_id)
        if not nl:
            raise ValueError(f"Newsletter {newsletter_id} not found")
        if nl.status == NewsletterStatus.SENT.value:
            raise ValueError("Newsletter already sent")

        # Get recipients
        if target_tags:
            subscribers = self.segment(target_tags)
        else:
            subscribers = self.list_subscribers(status="active")

        if not subscribers:
            return {"sent": 0, "batches": 0, "newsletter_id": newsletter_id}

        with self._connect() as conn:
            conn.execute("""
                UPDATE newsletters SET status='sending', updated_at=? WHERE id=?
            """, (_now(), newsletter_id))

        sent_count = 0
        batch_count = 0
        now = _now()

        # Process in batches
        for i in range(0, len(subscribers), self.BATCH_SIZE):
            batch = subscribers[i:i + self.BATCH_SIZE]
            batch_count += 1
            with self._connect() as conn:
                for sub in batch:
                    record_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO send_records
                        (id, newsletter_id, subscriber_id, sent_at)
                        VALUES (?, ?, ?, ?)
                    """, (record_id, newsletter_id, sub.id, now))
                    sent_count += 1

        sent_at = _now()
        with self._connect() as conn:
            conn.execute("""
                UPDATE newsletters
                SET status='sent', sent_at=?, recipient_count=?, updated_at=?
                WHERE id=?
            """, (sent_at, sent_count, sent_at, newsletter_id))

        return {
            "newsletter_id": newsletter_id,
            "sent": sent_count,
            "batches": batch_count,
            "sent_at": sent_at,
        }

    def cancel_newsletter(self, newsletter_id: str) -> bool:
        """Cancel a scheduled or draft newsletter."""
        with self._connect() as conn:
            result = conn.execute("""
                UPDATE newsletters SET status='cancelled', updated_at=?
                WHERE id=? AND status IN ('draft', 'scheduled')
            """, (_now(), newsletter_id))
        return result.rowcount > 0

    # ── Tracking ──────────────────────────────────────────────────────────

    def record_open(self, newsletter_id: str, email: str) -> bool:
        """Record an email open event."""
        sub = self.get_subscriber_by_email(email)
        if not sub:
            return False
        now = _now()
        updated = False
        with self._connect() as conn:
            result = conn.execute("""
                UPDATE send_records SET opened=1, opened_at=?
                WHERE newsletter_id=? AND subscriber_id=? AND opened=0
            """, (now, newsletter_id, sub.id))
            updated = result.rowcount > 0
        if updated:
            self._update_open_rate(sub.id)
        return updated

    def record_click(self, newsletter_id: str, email: str, link: str) -> bool:
        """Record a link click event."""
        sub = self.get_subscriber_by_email(email)
        if not sub:
            return False
        now = _now()
        with self._connect() as conn:
            result = conn.execute("""
                UPDATE send_records SET clicked=1, clicked_at=?, click_url=?
                WHERE newsletter_id=? AND subscriber_id=?
            """, (now, link, newsletter_id, sub.id))
        return result.rowcount > 0

    def _update_open_rate(self, subscriber_id: str):
        """Recalculate and update subscriber open rate."""
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE subscriber_id=?",
                (subscriber_id,)
            ).fetchone()[0]
            opened = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE subscriber_id=? AND opened=1",
                (subscriber_id,)
            ).fetchone()[0]
            rate = (opened / total) if total > 0 else 0.0
            conn.execute(
                "UPDATE subscribers SET open_rate=? WHERE id=?", (rate, subscriber_id)
            )

    def record_bounce(self, newsletter_id: str, email: str) -> bool:
        """Record an email bounce."""
        sub = self.get_subscriber_by_email(email)
        if not sub:
            return False
        with self._connect() as conn:
            conn.execute("""
                UPDATE send_records SET bounced=1
                WHERE newsletter_id=? AND subscriber_id=?
            """, (newsletter_id, sub.id))
            conn.execute("""
                UPDATE subscribers SET status='bounced', updated_at=? WHERE id=?
            """, (_now(), sub.id))
        return True

    # ── Analytics ─────────────────────────────────────────────────────────

    def analytics(self, newsletter_id: str) -> dict:
        """Get full analytics for a newsletter."""
        nl = self.get_newsletter(newsletter_id)
        if not nl:
            return {"error": "Newsletter not found"}

        with self._connect() as conn:
            total_sent = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE newsletter_id=?",
                (newsletter_id,)
            ).fetchone()[0]

            total_opened = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE newsletter_id=? AND opened=1",
                (newsletter_id,)
            ).fetchone()[0]

            total_clicked = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE newsletter_id=? AND clicked=1",
                (newsletter_id,)
            ).fetchone()[0]

            total_bounced = conn.execute(
                "SELECT COUNT(*) FROM send_records WHERE newsletter_id=? AND bounced=1",
                (newsletter_id,)
            ).fetchone()[0]

            unsub_count = conn.execute(
                "SELECT COUNT(*) FROM unsubscribe_log WHERE newsletter_id=?",
                (newsletter_id,)
            ).fetchone()[0]

        open_rate = (total_opened / total_sent) if total_sent > 0 else 0.0
        click_rate = (total_clicked / total_sent) if total_sent > 0 else 0.0
        bounce_rate = (total_bounced / total_sent) if total_sent > 0 else 0.0

        return {
            "newsletter_id": newsletter_id,
            "subject": nl.subject,
            "status": nl.status,
            "sent_at": nl.sent_at,
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_bounced": total_bounced,
            "unsubscribes": unsub_count,
            "open_rate": round(open_rate, 4),
            "click_rate": round(click_rate, 4),
            "bounce_rate": round(bounce_rate, 4),
            "word_count": nl.word_count,
            "estimated_read_time_min": nl.estimated_read_time_min,
        }

    def top_clicked_links(self, newsletter_id: str) -> List[dict]:
        """Get most clicked links in a newsletter."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT click_url, COUNT(*) as clicks
                FROM send_records
                WHERE newsletter_id=? AND clicked=1 AND click_url IS NOT NULL
                GROUP BY click_url
                ORDER BY clicks DESC
                LIMIT 10
            """, (newsletter_id,)).fetchall()
        return [{"url": r["click_url"], "clicks": r["clicks"]} for r in rows]

    def list_newsletters(self, status: Optional[str] = None,
                         limit: int = 50) -> List[Newsletter]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM newsletters WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM newsletters ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [Newsletter(**dict(r)) for r in rows]

    def overall_stats(self) -> dict:
        """Get engine-wide statistics."""
        with self._connect() as conn:
            total_subs = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
            active_subs = conn.execute(
                "SELECT COUNT(*) FROM subscribers WHERE status='active'"
            ).fetchone()[0]
            total_newsletters = conn.execute("SELECT COUNT(*) FROM newsletters").fetchone()[0]
            total_sent_emails = conn.execute("SELECT COUNT(*) FROM send_records").fetchone()[0]

        return {
            "total_subscribers": total_subs,
            "active_subscribers": active_subs,
            "total_newsletters": total_newsletters,
            "total_sent_emails": total_sent_emails,
        }

    def export_subscribers(self, status: str = "active") -> List[dict]:
        """Export subscriber list as list of dicts."""
        subs = self.list_subscribers(status=status, limit=10000)
        return [
            {
                "email": s.email,
                "name": s.name,
                "tags": s.tags_list,
                "open_rate": s.open_rate,
                "status": s.status,
            }
            for s in subs
        ]


def create_engine(db_path: str = "newsletter.db") -> NewsletterEngine:
    """Factory to create a NewsletterEngine instance."""
    return NewsletterEngine(db_path=db_path)


if __name__ == "__main__":
    engine = create_engine()

    print("BlackRoad Newsletter Engine")
    print("=" * 40)

    # Seed subscribers
    for i in range(5):
        engine.subscribe(f"user{i}@example.com", f"User {i}", tags=["tech", "news"])
    engine.subscribe("mobile@example.com", "Mobile User", tags=["mobile"])

    stats = engine.overall_stats()
    print(f"Subscribers: {stats['active_subscribers']} active")

    # Create and send
    nl = engine.create_newsletter(
        subject="BlackRoad Weekly #1",
        body_md="# Hello World\n\nWelcome to the newsletter!\n\nCheck out [our blog](https://blackroad.io/blog).",
        preview="Welcome to the newsletter!",
    )
    print(f"\nCreated newsletter: {nl.id}")
    print(f"Word count: {nl.word_count}, Read time: {nl.estimated_read_time_min} min")

    result = engine.send(nl.id)
    print(f"\nSent to {result['sent']} subscribers in {result['batches']} batch(es)")

    # Simulate engagement
    engine.record_open(nl.id, "user0@example.com")
    engine.record_open(nl.id, "user1@example.com")
    engine.record_click(nl.id, "user0@example.com", "https://blackroad.io/blog")

    analytics = engine.analytics(nl.id)
    print(f"\nAnalytics:")
    print(f"  Open rate: {analytics['open_rate']:.1%}")
    print(f"  Click rate: {analytics['click_rate']:.1%}")

    # Segment
    tech_subs = engine.segment(["tech"])
    print(f"\nTech segment: {len(tech_subs)} subscribers")
