<div align="center">

<img src="https://img.shields.io/badge/Quectosoft%20Technologies%20LLP-OpenEngage%20Agentic%20Marketing-01696f?style=for-the-badge&logo=mailbox&logoColor=white" alt="Quectosoft Technologies LLP"/>

# 📧 OpenEngage
## Agentic AI-Powered Marketing Automation Platform

### *An open-source, multi-agent, LLM-powered marketing automation stack that plans campaigns, writes emails, scores leads, syncs CRMs, and explains your analytics — on top of Mautic.*

[![License: QSAL-1.0](https://img.shields.io/badge/License-QSAL--1.0-01696f.svg?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-61dafb?style=flat-square&logo=react&logoColor=white)](https://react.dev)
[![Mautic](https://img.shields.io/badge/Automation-Mautic%205-ff6b35?style=flat-square)](https://mautic.org)
[![LangGraph](https://img.shields.io/badge/Agents-LangGraph%20%7C%20Multi--LLM-7c3aed?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Ollama](https://img.shields.io/badge/Default%20LLM-Ollama%20%7C%20Qwen3:8b-00b894?style=flat-square)](https://ollama.com)
[![ChromaDB](https://img.shields.io/badge/Memory-ChromaDB%20%7C%20Postgres-e63946?style=flat-square)](https://www.trychroma.com)
[![Docker](https://img.shields.io/badge/Runtime-Docker%20%7C%20GCP-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-❤️-ea4aaa?style=flat-square&logo=github-sponsors)](https://github.com/sponsors/quectosofttech)

<br/>

**Author:** [Subrit Dikshit](mailto:subrit@quectosofttech.com)  
**Emails:** [subrit@gmail.com](mailto:subrit@gmail.com) · [subrit@quectosofttech.com](mailto:subrit@quectosofttech.com)  
**Organisation:** Quectosoft Technologies LLP · India

<br/>

> **Give it a business goal in natural language. OpenEngage plans the campaign, finds the audience, writes the emails, scores the leads, syncs Salesforce/HubSpot, and tells you what worked — all on top of Mautic.**

<br/>

[🚀 Quick Start](#-quick-start) · [✨ What Makes It Different](#-what-makes-this-different) · [🏗️ Architecture](#-architecture) · [📁 Repository Structure](#-repository-structure) · [🧠 LLM Providers](#-llm-providers) · [🤝 Contributing](#-contributing) · [💼 Sponsorship & Commercial Use](#-sponsorship--commercial-use) · [📄 License](#-license)

</div>

---

## ✨ What Makes This Different

| Feature | Description |
|---|---|
| 🧠 **Agentic AI Layer** | LangGraph supervisor + 5 specialist agents (Campaign Strategy, Email Copywriter, Lead Scoring, Segmentation, Analytics Analyst) orchestrate on top of Mautic. |
| 📧 **AI Campaign Recommendations** | Plans 4–8 week multi-channel nurtures, A/B tests, goal KPIs — something neither Mautic nor Marketo does natively. |
| ✍️ **AI Email Copywriter** | Generates subject-line variants and full HTML emails, integrated directly into GrapesJS with personalization tokens. |
| 🎯 **Transparent Lead Scoring** | Rule-based, additive scoring with explainable rules — patent-safe alternative to opaque ML scoring. |
| 📊 **Analytics Analyst** | Reads Superset dashboards via API and explains ROI, attribution, and what to fix next. |
| 🔌 **Deep Integrations** | First-class adapters for Salesforce, HubSpot, Adobe Marketo bulk migration, CSV import with dedup, and web tracking JS snippet. |
| 🧩 **Mautic-Native Friendly** | Designed as a sidecar AI layer around Mautic’s APIs and webhooks — no forked core. |
| 🧱 **Prod-Ready Stack** | JWT auth, rate limiting, TLS Nginx, Prometheus/Grafana, CI/CD, Docker Compose, Alembic migrations, and tests. |

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React 18)                         │
│  Dashboard · Campaign Builder · GrapesJS Email Editor · Copilot│
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP/WS
┌──────────────────────▼──────────────────────────────────────────┐
│      AI GATEWAY (FastAPI + LangGraph + JWT + Prometheus)       │
│   /api/*   REST  · /ws/copilot/* WebSocket · /webhooks/*       │
└──────┬───────────────┬──────────────────────────────────────────┘
       │               │ Celery tasks
┌──────▼───────┐  ┌────▼─────────────────────────────────────────┐
│ 🤖 Orchestr. │  │ Celery Workers (campaign · email · scoring   │
│  Agent       │  │                 · agents · crm_sync)         │
│  ├─ Campaign │  └────┬─────────────────────────────────────────┘
│  ├─ Email    │       │ API bridge
│  ├─ Scoring  │  ┌────▼─────────────────────────────────────────┐
│  ├─ Segment  │  │ Mautic Core (PHP/Symfony)                    │
│  └─ Analyst  │  │ Contacts · Segments · Campaigns · Emails     │
└──────┬───────┘  └────┬─────────────────────────────────────────┘
       │ RAG            │ DB, cache, vectors
       ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATA LAYER: PostgreSQL · Redis · ChromaDB · MinIO · Ollama     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker 24+ and Docker Compose v2  
- Python 3.12+ (for dev)  
- [Ollama](https://ollama.com) installed and running  
- 16 GB RAM minimum (32 GB recommended)

### 1 — Clone & Configure

```bash
git clone https://github.com/Quectosoft-Technologies-LLP/openengage.git
cd openengage

cp .env.example .env
# Edit .env:
# - Set JWT_SECRET (32+ chars)
# - Set DATABASE_URL / REDIS_URL
# - Leave LLM_PROVIDER=ollama for default local usage
```

### 2 — Start Stack

```bash
docker compose up -d

# Run database migrations
docker compose exec ai_gateway alembic upgrade head

# Bootstrap models & Superset
chmod +x setup.sh && ./setup.sh
```

### 3 — Open the UI

| Service | URL |
|---|---|
| OpenEngage UI | http://localhost:3000 |
| AI Gateway API | http://localhost:8000/docs |
| Mautic | http://localhost:8080 |
| Superset | http://localhost:8088 |
| Grafana | http://localhost:3002 |

---

## 📁 Repository Structure

```text
openengage/
├── README.md
├── LICENSE                     ← QSAL-1.0
├── CONTRIBUTING.md
├── .env.example
├── docker-compose.yml
├── setup.sh
│
├── ai_gateway/
│   ├── main.py                 ← FastAPI app (JWT, CORS, metrics)
│   ├── llm/registry.py         ← Multi-provider LLM registry (Ollama default)
│   ├── agents/
│   │   ├── orchestrator.py     ← LangGraph supervisor
│   │   ├── campaign_strategy.py
│   │   ├── email_copywriter.py
│   │   ├── lead_scoring.py
│   │   ├── segmentation.py
│   │   └── analytics_analyst.py
│   ├── middleware/             ← auth, security headers, logging
│   ├── routers/
│   │   ├── agents.py
│   │   ├── import_contacts.py
│   │   ├── health.py
│   │   └── webhooks/…
│   ├── models/db_models.py
│   ├── workers/                ← Celery app + tasks
│   └── tests/
│       ├── test_migrations.py
│       ├── test_api.py
│       └── pytest.ini
│
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   ├── hooks/useCopilot.js
│   │   └── components/
│   │       ├── Dashboard/…
│   │       ├── CampaignBuilder/…
│   │       ├── EmailEditor/…
│   │       ├── CopilotChat/…
│   │       └── Contacts/ContactsPage.jsx
│   └── tailwind.config.js
│
├── integrations/
│   ├── salesforce/adapter.py
│   ├── hubspot/adapter.py
│   ├── marketo_migration/migrate.py
│   ├── csv_import/importer.py
│   └── webhooks/
│       ├── router.py
│       └── tracker.js
│
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 001_initial.py
│       ├── 002_scoring_attribution.py
│       └── 003_integrations.py
│
└── infra/
    ├── nginx/nginx.conf
    └── monitoring/
        ├── prometheus.yml
        └── grafana/dashboards/openengage.json
```

---

## 🧠 LLM Providers

OpenEngage uses a **universal LLM registry**. Default is **Ollama** (local, no keys). You can switch providers via environment variables, without changing agent code.

```env
LLM_PROVIDER=ollama      # default — fully local
LLM_PROVIDER=openai      # GPT-4o / GPT-4o-mini / o3-mini
LLM_PROVIDER=claude      # Claude 3.5 Haiku / Sonnet
LLM_PROVIDER=gemini      # Gemini 2.0 Flash / 2.5 Pro
LLM_PROVIDER=grok        # xAI Grok 3
LLM_PROVIDER=llamacpp    # local GGUF via llama-server
LLM_PROVIDER=azure_openai
```

| Provider | Local | Key | Notes |
|---|:---:|:---:|---|
| **Ollama** | ✅ | ❌ | Default; `qwen3:8b`, `llama3.1`, `gemma3` |
| OpenAI | ❌ | ✅ | GPT-4o family |
| Claude | ❌ | ✅ | Long-context, structured reasoning |
| Gemini | ❌ | ✅ | Multimodal, Google ecosystem |
| Grok | ❌ | ✅ | Real-time + X/Twitter context |
| llama.cpp | ✅ | ❌ | Any GGUF via `llama-server` |
| Azure OpenAI | ❌ | ✅ | Enterprise deployments |

---

## 🤝 Contributing

We welcome PRs from developers, marketers, and AI enthusiasts.

```bash
git checkout -b feat/your-feature
cd ai_gateway && pytest tests/ -v
cd ../frontend && npm test
git commit -m "feat: your feature"
git push origin feat/your-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards, commit style, and patent-safety notes.

---

## 💼 Sponsorship & Commercial Use

OpenEngage is licensed under **QSAL-1.0 (Quectosoft Agentic AI License)** — free for:

- Students, hobbyists, researchers, educators  
- Non-profits and open-source tooling

**Commercial use (for-profit, agencies, SaaS, consultants)** requires either:

- A commercial license — email **subrit@quectosofttech.com**, subject: `"OpenEngage Commercial License"`  
- Or an agreed GitHub Sponsor tier: [github.com/sponsors/quectosofttech](https://github.com/sponsors/quectosofttech)

See [LICENSE](LICENSE) for full terms.

---

## 📄 License

> **Quectosoft Technologies LLP Agentic AI License (QSAL-1.0)**  
> Copyright (c) 2026 Quectosoft Technologies LLP  
> Author: **Subrit Dikshit**

Free for education, research, and non-commercial use; commercial use requires sponsorship or a paid license.

---

## 📬 Contact

| Channel | Details |
|---|---|
| 📧 Personal | [subrit@gmail.com](mailto:subrit@gmail.com) |
| 📧 Work | [subrit@quectosofttech.com](mailto:subrit@quectosofttech.com) |
| 🌐 Org | Quectosoft Technologies LLP |
| 🐛 Issues | [GitHub Issues](https://github.com/Quectosoft-Technologies-LLP/openengage/issues) |
| ❤️ Sponsors | [GitHub Sponsors](https://github.com/sponsors/quectosofttech) |

---

<div align="center">

**Built with ❤️ by Quectosoft Technologies LLP and the OpenEngage community.**

*If this project helps you, please ⭐ star the repo and share it with someone who should be running agentic marketing on open source.*

</div>
