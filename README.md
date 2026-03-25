<!-- BlackRoad SEO Enhanced -->

# ulackroad newsletter engine

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad Media](https://img.shields.io/badge/Org-BlackRoad-Media-2979ff?style=for-the-badge)](https://github.com/BlackRoad-Media)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**ulackroad newsletter engine** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---


> Email newsletter creation, scheduling, and analytics

Part of the [BlackRoad OS](https://blackroad.io) ecosystem — [BlackRoad-Media](https://github.com/BlackRoad-Media)

---

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
    body_md="# Hello!

This week's highlights...",
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
