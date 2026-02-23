# BlackRoad Newsletter Engine

> Email newsletter creation, scheduling, and analytics — part of the BlackRoad Media suite.

[![CI](https://github.com/BlackRoad-Media/blackroad-newsletter-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-Media/blackroad-newsletter-engine/actions/workflows/ci.yml)

## Features

- **Subscriber management**: Subscribe, unsubscribe, bounce handling
- **Newsletter authoring**: Markdown body with preview text
- **Scheduling**: Future-date scheduling
- **Batch sending**: Configurable batch size (default 100)
- **Engagement tracking**: Opens, clicks, bounces
- **Segmentation**: Tag-based audience filtering
- **Analytics**: Open rate, click rate, bounce rate per newsletter
- **SQLite persistence**: All data stored locally

## Quick Start

```bash
pip install -r requirements.txt
python newsletter_engine.py
```

## Usage

```python
from newsletter_engine import create_engine

engine = create_engine()

# Add subscribers
engine.subscribe("alice@example.com", "Alice", tags=["tech", "news"])

# Create newsletter
nl = engine.create_newsletter(
    subject="Weekly Digest #1",
    body_md="# Hello!\n\nThis week's highlights...",
    preview="This week's highlights",
)

# Send
result = engine.send(nl.id)
print(f"Sent to {result['sent']} subscribers")

# Track engagement
engine.record_open(nl.id, "alice@example.com")
engine.record_click(nl.id, "alice@example.com", "https://blackroad.io")

# Analytics
stats = engine.analytics(nl.id)
print(f"Open rate: {stats['open_rate']:.1%}")
```

## Testing

```bash
pytest tests/ -v --cov=newsletter_engine
```

## License

Proprietary — © BlackRoad OS, Inc.
