import os
import pytest
from newsletter_engine import (
    NewsletterEngine, Subscriber, Newsletter, SendRecord,
    SubscriberStatus, NewsletterStatus, create_engine,
)


@pytest.fixture
def engine(tmp_path):
    return NewsletterEngine(db_path=str(tmp_path / "test_newsletter.db"))


@pytest.fixture
def engine_with_subs(engine):
    engine.subscribe("alice@example.com", "Alice", tags=["tech", "news"])
    engine.subscribe("bob@example.com", "Bob", tags=["tech"])
    engine.subscribe("carol@example.com", "Carol", tags=["news", "lifestyle"])
    engine.subscribe("dave@example.com", "Dave", tags=["tech", "lifestyle"])
    return engine


class TestSubscribers:
    def test_subscribe_new(self, engine):
        sub = engine.subscribe("test@example.com", "Test User", tags=["tech"])
        assert sub.id is not None
        assert sub.email == "test@example.com"
        assert sub.status == SubscriberStatus.ACTIVE.value

    def test_subscribe_normalizes_email(self, engine):
        sub = engine.subscribe("TEST@EXAMPLE.COM", "Test")
        assert sub.email == "test@example.com"

    def test_subscribe_invalid_email(self, engine):
        with pytest.raises(ValueError, match="Invalid email"):
            engine.subscribe("not-an-email", "Bad User")

    def test_subscribe_reactivates_unsubscribed(self, engine):
        engine.subscribe("test@example.com", "Test")
        engine.unsubscribe("test@example.com")
        resub = engine.subscribe("test@example.com", "Test Again")
        assert resub.status == SubscriberStatus.ACTIVE.value

    def test_unsubscribe(self, engine):
        engine.subscribe("test@example.com", "Test")
        result = engine.unsubscribe("test@example.com")
        assert result is True
        sub = engine.get_subscriber_by_email("test@example.com")
        assert sub.status == SubscriberStatus.UNSUBSCRIBED.value

    def test_mark_bounced(self, engine):
        engine.subscribe("test@example.com", "Test")
        result = engine.mark_bounced("test@example.com")
        assert result is True
        sub = engine.get_subscriber_by_email("test@example.com")
        assert sub.status == SubscriberStatus.BOUNCED.value

    def test_subscriber_count(self, engine_with_subs):
        count = engine_with_subs.subscriber_count("active")
        assert count == 4

    def test_segment_by_tag(self, engine_with_subs):
        tech_subs = engine_with_subs.segment(["tech"])
        emails = [s.email for s in tech_subs]
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails
        assert "carol@example.com" not in emails


class TestNewsletters:
    def test_create_newsletter(self, engine):
        nl = engine.create_newsletter("Hello World", "# Hello\n\nContent here.", "Hello")
        assert nl.id is not None
        assert nl.status == NewsletterStatus.DRAFT.value
        assert nl.word_count > 0

    def test_preview_text_defaults(self, engine):
        nl = engine.create_newsletter("Test", "Body text here.", "")
        assert nl.preview_text != ""

    def test_schedule_newsletter(self, engine):
        nl = engine.create_newsletter("Scheduled", "Body.", "Preview")
        scheduled = engine.schedule(nl.id, "2030-01-01T09:00:00+00:00")
        assert scheduled.status == NewsletterStatus.SCHEDULED.value
        assert scheduled.scheduled_at == "2030-01-01T09:00:00+00:00"

    def test_cancel_newsletter(self, engine):
        nl = engine.create_newsletter("To Cancel", "Body.", "Preview")
        result = engine.cancel_newsletter(nl.id)
        assert result is True
        fetched = engine.get_newsletter(nl.id)
        assert fetched.status == NewsletterStatus.CANCELLED.value

    def test_cannot_schedule_sent_newsletter(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Test", "Body.", "Preview")
        engine_with_subs.send(nl.id)
        with pytest.raises(ValueError):
            engine_with_subs.schedule(nl.id, "2030-01-01T09:00:00+00:00")


class TestSendingAndAnalytics:
    def test_send_newsletter(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Weekly", "Content.", "Preview")
        result = engine_with_subs.send(nl.id)
        assert result["sent"] == 4
        assert result["batches"] >= 1

    def test_send_with_tag_filter(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Tech Only", "Content.", "Preview")
        result = engine_with_subs.send(nl.id, target_tags=["tech"])
        assert result["sent"] == 3  # alice, bob, dave

    def test_cannot_send_twice(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Once", "Content.", "Preview")
        engine_with_subs.send(nl.id)
        with pytest.raises(ValueError, match="already sent"):
            engine_with_subs.send(nl.id)

    def test_record_open(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Track", "Content.", "Preview")
        engine_with_subs.send(nl.id)
        result = engine_with_subs.record_open(nl.id, "alice@example.com")
        assert result is True

    def test_record_click(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Track", "Content.", "Preview")
        engine_with_subs.send(nl.id)
        result = engine_with_subs.record_click(nl.id, "alice@example.com", "https://blackroad.io")
        assert result is True

    def test_analytics_open_rate(self, engine_with_subs):
        nl = engine_with_subs.create_newsletter("Analytics Test", "Content.", "Preview")
        engine_with_subs.send(nl.id)
        engine_with_subs.record_open(nl.id, "alice@example.com")
        engine_with_subs.record_open(nl.id, "bob@example.com")
        stats = engine_with_subs.analytics(nl.id)
        assert stats["total_sent"] == 4
        assert stats["total_opened"] == 2
        assert stats["open_rate"] == 0.5

    def test_overall_stats(self, engine_with_subs):
        stats = engine_with_subs.overall_stats()
        assert stats["active_subscribers"] == 4
        assert "total_newsletters" in stats

    def test_export_subscribers(self, engine_with_subs):
        exported = engine_with_subs.export_subscribers()
        assert len(exported) == 4
        assert "email" in exported[0]
        assert "tags" in exported[0]

    def test_create_engine_factory(self, tmp_path):
        e = create_engine(str(tmp_path / "factory.db"))
        assert e is not None
        e.subscribe("test@example.com", "Test")
        assert e.subscriber_count() == 1


class TestRenderHtml:
    """Tests for the HTML rendering method using Jinja2 templates."""

    TEMPLATES_DIR = os.path.join(
        os.path.dirname(__file__), "..", "templates"
    )

    def test_render_html_basic(self, engine):
        nl = engine.create_newsletter(
            "BlackRoad Weekly",
            "# Hello\n\nWelcome to BlackRoad.",
            "Welcome to BlackRoad.",
        )
        html = engine.render_html(nl.id, templates_dir=self.TEMPLATES_DIR)
        assert "<html" in html.lower()
        assert "BlackRoad Weekly" in html

    def test_render_html_contains_body(self, engine):
        nl = engine.create_newsletter(
            "Test Issue",
            "## Section\n\nSome **bold** content.",
            "Some bold content.",
        )
        html = engine.render_html(nl.id, templates_dir=self.TEMPLATES_DIR)
        assert "<strong>bold</strong>" in html

    def test_render_html_extra_context(self, engine):
        nl = engine.create_newsletter("Context Test", "Body.", "Preview.")
        html = engine.render_html(
            nl.id,
            templates_dir=self.TEMPLATES_DIR,
            extra_context={"issue_label": "Issue #42"},
        )
        assert "Issue #42" in html

    def test_render_html_not_found(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.render_html("nonexistent-id", templates_dir=self.TEMPLATES_DIR)

