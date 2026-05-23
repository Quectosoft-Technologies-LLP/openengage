<div align="center">

<img src="https://img.shields.io/badge/OpenEngage-v1.0.0-6366f1?style=for-the-badge" />
<img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" />
<img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python" />
<img src="https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react" />
<img src="https://img.shields.io/badge/LangGraph-Multi--Agent-8b5cf6?style=for-the-badge" />
<img src="https://img.shields.io/badge/Patent%20Safe-✓-emerald?style=for-the-badge" />

# OpenEngage

**The open-source, LLM-powered marketing automation platform.**  
Built on Mautic · Extended with a LangGraph multi-agent AI layer ·  
Integrates with Salesforce, HubSpot, and Adobe Marketo.

[Quick Start](#quick-start) · [Architecture](#architecture) · [AI Agents](#ai-agents) · [Integrations](#integrations) · [Deployment](#deployment) · [Contributing](#contributing)

</div>

---

## What is OpenEngage?

OpenEngage is a **production-grade, fully open-source** marketing automation platform that does what neither [Mautic](https://mautic.org) nor Adobe Marketo Engage does well — combines a battle-tested automation engine with a **LangGraph multi-agent AI layer** for intelligent, autonomous campaign recommendations.

| Capability | Mautic | Adobe Marketo | **OpenEngage** |
|---|:---:|:---:|:---:|
| Email automation | ✅ | ✅ | ✅ |
| Lead scoring | ✅ | ✅ | ✅ (rule-based, transparent) |
| CRM sync (SF + HS) | ✅ | ✅ | ✅ |
| Drag-drop email editor | ✅ | ✅ | ✅ (GrapesJS) |
| AI campaign recommendations | ❌ | ❌ | ✅ **LangGraph** |
| NL → audience segmentation | ❌ | ❌ | ✅ **SQL agent** |
| AI email copywriting | ❌ | ❌ | ✅ **A/B variants** |
| Marketo data migration | ❌ | N/A | ✅ **Bulk export** |
| Self-hosted / on-prem | ✅ | ❌ | ✅ |
| License | GPL-3 | Proprietary | **Apache-2.0** |
| Cost | Free | $895–$3,750/mo | **Free** |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  🖥️  FRONTEND  (React 18 + TailwindCSS + GrapesJS)          │
│   Dashboard · Campaign Builder · Email Editor · Copilot     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WS
┌──────────────────────▼──────────────────────────────────────┐
│  ⚙️  AI GATEWAY  (FastAPI + Prometheus + JWT auth)           │
│   REST API · /ws/copilot WebSocket · /webhooks              │
└──────┬───────────────┬─────────────────────────────────────-┘
       │ invoke        │ tasks
┌──────▼───────┐  ┌────▼────────────────────────────────────┐
│ 🤖 LangGraph │  │ 📦 Celery Workers (4 queues)             │
│ Orchestrator │  │   campaign · email · scoring · crm_sync  │
│  ├─ Campaign │  └────┬────────────────────────────────────-┘
│  ├─ Scoring  │       │ API calls
│  ├─ Email    │  ┌────▼─────────────────────────────────────┐
│  ├─ Segment  │  │ 🔧 Mautic Core (PHP/Symfony GPL-3)       │
│  └─ Analyst  │  │   Contacts · Campaigns · Forms · Segments │
└──────┬───────┘  └────┬────────────────────────────────────-┘
       │ RAG            │ SQL/cache
       ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│  🗄️  DATA LAYER                                             │
│   PostgreSQL · Redis · ChromaDB · MinIO · Ollama            │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- NVIDIA GPU (optional, for faster LLM inference — CPU mode works)
- 16 GB RAM minimum (32 GB recommended with GPU)

```bash
# 1. Clone
git clone https://github.com/your-org/openengage.git
cd openengage

# 2. Configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET (32+ chars), DB passwords, API keys

# 3. Start all services
docker compose up -d

# 4. Bootstrap (pulls LLM models, runs migrations, seeds Superset)
chmod +x setup.sh && ./setup.sh
```

**That's it.** Access:

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| AI Gateway (API) | http://localhost:8000/docs | — |
| Mautic Core | http://localhost:8080 | admin/admin (first run) |
| Superset Analytics | http://localhost:8088 | admin/admin123 |
| Chatwoot Live Chat | http://localhost:3001 | Setup on first run |
| Postal MTA | http://localhost:5000 | Setup on first run |
| Grafana | http://localhost:3002 | admin/openengage_grafana_123 |
| MinIO Console | http://localhost:9001 | openengage/openengage123 |

---

## AI Agents

OpenEngage uses a **LangGraph supervisor pattern** — the Orchestrator Agent receives user messages and dynamically routes them to the right specialist agent.

### Using the AI Copilot (WebSocket)
```javascript
// React hook
const { messages, send, connected } = useCopilot("my-session");

send("Create a 6-week nurture campaign for fintech leads who downloaded our whitepaper");
// → Routes to Campaign Strategy Agent
// → Returns: campaign timeline, email sequence, KPIs, A/B test suggestions

send("Write 3 subject lines for a demo invite targeting CTOs");
// → Routes to Email Copywriter Agent
// → Returns: A/B/C variants with curiosity/urgency/clarity scores

send("Show me all BFSI contacts with score above 40 who haven't opened in 30 days");
// → Routes to Segmentation Agent
// → Returns: SQL WHERE clause + estimated count + re-engagement campaign suggestion
```

### REST API
```bash
# Campaign suggestion
curl -X POST http://localhost:8000/api/agents/suggest-campaign \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"industry": "BFSI", "goal": "Generate SQLs from webinar attendees", "audience_size": 2400}'

# Generate email
curl -X POST http://localhost:8000/api/agents/generate-email \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{"session_id": "s1", "message": "Follow-up email for demo no-shows, professional tone"}'
```

### Swapping LLM Models
Edit `ai_gateway/agents/orchestrator.py` — one line:
```python
self.llm = ChatOllama(model="llama3.1:8b")    # Llama 3.1
self.llm = ChatOllama(model="qwen3:8b")        # Qwen 3
self.llm = ChatOllama(model="gemma3:12b")      # Gemma 3
# Point to a fine-tuned model loaded in your local Ollama instance
```

---

## Integrations

### Marketo → OpenEngage Migration
```bash
# Set credentials in .env, then run:
cd integrations/marketo_migration
python migrate.py
# Output: ✅ Imported: 12,847 | Deduped: 234 | Errors: 3 | Templates: 48
```

### Salesforce Sync
```bash
# Trigger manual pull (or auto-runs every 30 min via Celery Beat)
curl -X POST http://localhost:8000/api/integrations/sync/salesforce \
  -H "Authorization: Bearer YOUR_JWT"
```

Configure Salesforce → OpenEngage outbound messages:
1. Salesforce Setup → Outbound Messages → New
2. Endpoint URL: `https://your-openengage.com/webhooks/salesforce`
3. Fields: `Email`, `Status`, `Title`, `Company`

### HubSpot Sync
```bash
curl -X POST http://localhost:8000/api/integrations/sync/hubspot \
  -H "Authorization: Bearer YOUR_JWT"
```

Configure HubSpot webhooks:
1. HubSpot portal → Settings → Integrations → Private Apps
2. Webhook URL: `https://your-openengage.com/webhooks/hubspot`
3. Subscribe: `contact.creation`, `contact.propertyChange`

### CSV Import with Deduplication
```bash
# Upload CSV
curl -X POST http://localhost:8000/api/contacts/import \
  -H "Authorization: Bearer YOUR_JWT" \
  -F "file=@my_contacts.csv" \
  -F "on_conflict=update"
# Returns: { "job_id": "abc-123" }

# Poll status
curl http://localhost:8000/api/contacts/import/abc-123
# Returns: { "inserted": 1842, "updated": 312, "duplicates_in_csv": 47, ... }
```

Supported CSV column aliases: `email`, `e-mail`, `mail`, `emailaddress` → all map to `email`. Auto-detects comma, semicolon, tab, and pipe delimiters.

### Web Tracking Snippet
```html
<!-- Add to your website <head> -->
<script src="https://your-openengage.com/tracker.js" async></script>
<script>
  // After user login/form submit:
  OpenEngage.identify("user@company.com");
  OpenEngage.track("demo_requested", { plan: "enterprise" });
</script>
```

---

## Deployment

### Docker Compose (Single Server)
```bash
# Production start
ENV=production docker compose -f docker-compose.yml up -d

# Run migrations
docker compose exec ai_gateway alembic upgrade head

# Scale workers
docker compose up -d --scale worker=4
```

### GCP / Kubernetes
```bash
# GCP VM (asia-south1 — closest to Noida)
gcloud compute instances create openengage-prod \
  --machine-type=n2-standard-8 \
  --zone=asia-south1-a \
  --boot-disk-size=100GB \
  --image-family=ubuntu-2204-lts \
  --accelerator=type=nvidia-tesla-t4,count=1

# Deploy
scp -r . openengage-prod:/opt/openengage
ssh openengage-prod "cd /opt/openengage && ./setup.sh"
```

### Environment Variables
Copy `.env.example` → `.env`. Required keys:

```env
JWT_SECRET=your_32_char_minimum_secret_key_here
DATABASE_URL=postgresql://postgres:STRONG_PASS@db:5432/openengage
REDIS_URL=redis://redis:6379/0
OLLAMA_URL=http://ollama:11434
ALLOWED_ORIGINS=https://your-openengage.com
```

---

## Patent Safety

OpenEngage deliberately avoids all identified Adobe/Marketo patented methods:

| ❌ Avoided | Patent | Safe Alternative Used |
|---|---|---|
| Sentiment-weighted lead scoring | US20160140627A1 | Additive rule-based points |
| Time-decay probabilistic scoring | US10657559B2 | Simple open/click counters |
| ML-predicted resource allocation | US11025713B2 | Static Celery priority queues |
| Probabilistic multi-order attribution | US10475067B2 | Standard linear attribution |
| Social sentiment → auto campaigns | US10528987B2 | No social sentiment engine |
| Lead intelligence via social tokens | US20130238435A1 | Standard UTM parameters |

> ⚠️ This is not legal advice. Consult a patent attorney before commercial deployment.

---

## Project Structure

```
openengage/
├── ai_gateway/                 # FastAPI AI layer
│   ├── agents/                 # LangGraph specialist agents
│   │   ├── orchestrator.py     # Supervisor router
│   │   ├── campaign_strategy.py
│   │   ├── lead_scoring.py
│   │   ├── email_copywriter.py
│   │   ├── segmentation.py
│   │   └── analytics_analyst.py
│   ├── middleware/             # Auth, security headers, logging
│   ├── models/                 # SQLAlchemy ORM
│   ├── routers/                # FastAPI route handlers
│   └── workers/                # Celery tasks + beat scheduler
├── frontend/                   # React 18 + TailwindCSS
│   └── src/
│       ├── components/         # Dashboard, CampaignBuilder, EmailEditor, CopilotChat
│       ├── hooks/              # useCopilot (WebSocket)
│       └── api/                # Axios client
├── integrations/
│   ├── salesforce/             # Bi-directional SF sync
│   ├── hubspot/                # Bi-directional HS sync + webhooks
│   ├── marketo_migration/      # Full Marketo bulk export + import
│   ├── csv_import/             # CSV parser + deduplication pipeline
│   └── webhooks/               # Inbound webhook router + JS tracker
├── alembic/                    # DB migrations (3 revisions)
├── infra/
│   ├── nginx/                  # TLS-terminating reverse proxy
│   └── monitoring/             # Prometheus + Grafana config
├── .github/workflows/          # CI/CD (test → scan → build → deploy to GCP)
├── docker-compose.yml          # Full 12-service stack
├── setup.sh                    # One-command bootstrap
└── .env.example                # All environment variables documented
```

---

## Tech Stack

| Layer | Technology | License |
|---|---|---|
| Marketing Core | [Mautic 5](https://mautic.org) | GPL-3.0 |
| AI Gateway | FastAPI + Uvicorn | MIT |
| Multi-Agent AI | LangGraph + LangChain | MIT |
| LLM Runtime | Ollama (Qwen3, Llama3.1) | MIT |
| Vector Store | ChromaDB | Apache-2.0 |
| Email Editor | GrapesJS | BSD-3 |
| Analytics | Apache Superset | Apache-2.0 |
| Live Chat | Chatwoot | AGPL-3.0 |
| Email MTA | Postal | BSL-1.1 |
| Task Queue | Celery + Redis | BSD |
| Database | PostgreSQL 16 | PostgreSQL |
| Monitoring | Prometheus + Grafana | Apache-2.0 |
| CI/CD | GitHub Actions | — |
| Frontend | React 18 + TailwindCSS | MIT |

---

## Production Checklist

Before going live, verify:

- [ ] `JWT_SECRET` set to 32+ random chars in `.env`
- [ ] All default passwords changed in `.env`
- [ ] `ENV=production` set (disables Swagger UI)
- [ ] `ALLOWED_ORIGINS` set to your actual domain
- [ ] TLS certificate installed at `infra/nginx/ssl/`
- [ ] Alembic migrations run: `alembic upgrade head`
- [ ] Ollama models pulled: `ollama pull qwen3:8b && ollama pull nomic-embed-text`
- [ ] Postal MTA configured with your SMTP relay
- [ ] Grafana dashboard connected to Prometheus
- [ ] GitHub Actions secrets set: `GCP_SA_KEY`, `GITHUB_TOKEN`
- [ ] Salesforce/HubSpot webhook URLs configured with HMAC secrets

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

```bash
# Development setup
git clone https://github.com/your-org/openengage
cd openengage
cp .env.example .env         # Set ENV=development
docker compose up -d db redis chromadb ollama
cd ai_gateway && pip install -r requirements.txt
uvicorn main:app --reload    # API at localhost:8000
cd ../frontend && npm install && npm start  # UI at localhost:3000
```

### Branch Strategy
- `main` — production-ready, protected
- `develop` — integration branch
- `feature/*` — feature branches → PR to develop
- `hotfix/*` — emergency fixes → PR to main

---

## Roadmap

- [ ] **v1.1** — Contacts UI (CSV upload UI, CRM sync dashboard)
- [ ] **v1.2** — Mautic native plugin (replace API bridge with direct plugin)
- [ ] **v1.3** — Multi-tenant workspace support
- [ ] **v1.4** — Agent self-improvement (fine-tune on your own campaign data)
- [ ] **v2.0** — Kubernetes Helm chart + GCP Marketplace listing

---

## Sponsorship

OpenEngage is maintained by **Quectosoft Technologies LLP** and the open-source community.

Your sponsorship helps us:
- Ship enterprise features faster (multi-tenant workspaces, advanced attribution, AI self-improvement)
- Maintain integrations (Salesforce, HubSpot, Marketo, Postal, Superset)
- Keep the core platform Apache-2.0 and self-hostable forever

### How to Sponsor

- **GitHub Sponsors:** Enable on the Quectosoft Technologies LLP org and add this project.
- **Custom Support / SLAs:** For production SLAs, dedicated support, and roadmap influence, contact:
  - Email: `support@quectosoft.com`
  - Website: `https://www.quectosoft.com` (replace with your actual site)
- **Enterprise Deployments:** We offer paid help with on-prem / VPC deployment on AWS, GCP, Azure.

### Sponsor Recognition

Sponsors can opt-in to be listed in the README:

- **Platinum** — logo + link + short tagline
- **Gold** — logo + link
- **Silver** — text link

If you sponsor this project and want to be listed, open a PR adding yourself to the **Sponsors** section or email us with your logo and preferred link.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

> Built with ❤️ by the OpenEngage community.  
> Powered by [Mautic](https://mautic.org) · [LangGraph](https://github.com/langchain-ai/langgraph) · [Ollama](https://ollama.com)

---

## LLM Providers

OpenEngage ships with **7 LLM provider integrations** via a universal registry.
**Default is Ollama** — fully local, no API key, no data leaves your server.

Switch providers by changing one environment variable — **zero agent code changes needed.**

```env
LLM_PROVIDER=ollama      # default — local, free, private
LLM_PROVIDER=openai      # GPT-4o, GPT-4o-mini, o3-mini
LLM_PROVIDER=claude      # Claude 3.5 Haiku / Sonnet 3.7 / Opus
LLM_PROVIDER=gemini      # Gemini 2.0 Flash / 2.5 Pro
LLM_PROVIDER=grok        # xAI Grok-3 / Grok-3-mini
LLM_PROVIDER=llamacpp    # Any local GGUF model via llama-server
LLM_PROVIDER=azure_openai # Azure OpenAI (enterprise data residency)
```

### Provider Comparison

| Provider | Local | API Key | Best For | Default Model |
|---|:---:|:---:|---|---|
| **Ollama** ✅ | ✅ | ❌ | Privacy, cost-zero, on-prem | `qwen3:8b` |
| OpenAI | ❌ | ✅ | Highest quality, production SaaS | `gpt-4o-mini` |
| Claude | ❌ | ✅ | Long context, nuanced copy | `claude-3-5-haiku` |
| Gemini | ❌ | ✅ | Multimodal, Google ecosystem | `gemini-2.0-flash` |
| Grok | ❌ | ✅ | Real-time data, X/Twitter context | `grok-3-mini` |
| llama.cpp | ✅ | ❌ | Fine-tuned GGUF models, GPU servers | any GGUF |
| Azure OpenAI | ❌ | ✅ | Enterprise compliance, EU data residency | `gpt-4o` |

### Per-Agent LLM Override
```python
# agents/email_copywriter.py — use GPT-4o just for copy quality
from llm.registry import get_llm

class EmailCopywriterAgent:
    def __init__(self):
        # Override: use OpenAI for best copy, even if global provider is Ollama
        self.llm = get_llm(provider="openai", temperature=0.7)
```

### llama.cpp Setup (local GGUF models)
```bash
# Pull and run any GGUF model
wget https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/qwen3-8b-q4_k_m.gguf
llama-server -m qwen3-8b-q4_k_m.gguf --port 8080 -c 4096 --n-gpu-layers 35
# Set in .env:
LLM_PROVIDER=llamacpp
LLAMACPP_URL=http://localhost:8080
```
