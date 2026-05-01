# Cleo — AI Sales Coach for Clean Energy Installers

# Presentation Link
https://drive.google.com/drive/folders/1txEkJplzoX1lyu9aEIrVuP7AD1lHu_kl?usp=sharing

> Built at Q-Hack 2026 for the Cloover Challenge

## The Problem

Every day, thousands of energy installer sales reps in Germany drive hours to customer meetings — underprepared. They lack context on subsidies, can't articulate why *now* is the right time, and have no structured way to present financing. The result: low conversion rates, wasted trips, and missed revenue for the energy transition.

## Our Solution

**Cleo** is an AI-powered sales coach that prepares installers with a personalized, compelling pitch before they walk through the customer's door.

Think of it as a co-pilot for the drive. The rep selects a lead, and Cleo:

1. **Researches** the market — regional subsidies (KfW, BAFA), energy prices, competitor landscape
2. **Analyzes** the customer situation — solar potential, heating costs, optimal product bundles
3. **Builds a strategy** — value proposition, savings estimates, financing options, objection handling
4. **Generates a report** — structured PDF with tiered packages, financing comparison, and pitch guidance

All through a natural conversation — text or voice.

## Key Features

- **Conversational AI Agent** — Multi-phase pipeline (Research, Analysis, Financing, Strategy, Report) that asks smart questions, not dumb ones
- **Voice Mode** — Talk to Cleo hands-free with a digital avatar (Gemini STT + ElevenLabs TTS + browser speech)
- **Real-time Web Research** — Tavily-powered search for current subsidies, energy prices, and market data
- **Document RAG** — Upload product brochures or price lists as PDFs; Cleo uses them in research
- **Personalized Offer Tiers** — Starter / Recommended / Full Independence packages with realistic German market pricing
- **Financing Scenarios** — Cash, KfW loan + subsidy, full financing with monthly payment breakdowns
- **PDF Export** — Professional slide-format report matching the Cloover brand
- **Persistent Conversations** — Pick up where you left off; messages and reports survive page reloads

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, Tailwind CSS, Framer Motion |
| **Backend** | FastAPI, SQLAlchemy, SQLite (async) |
| **LLM** | Gemini 2.5 Flash (multi-provider: Gemini / Anthropic / OpenAI) |
| **Speech** | Gemini STT, ElevenLabs TTS, Web Speech API fallback |
| **Search** | Tavily API for real-time web research |
| **PDF** | pypdf (extraction), jsPDF (generation) |
| **Deploy** | Vercel (frontend), Render (backend) |

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐
│   Frontend   │────>│            FastAPI Backend            │
│  React/Vite  │<────│                                      │
└─────────────┘     │  ┌──────────────────────────────────┐│
                    │  │       Sales Supervisor            ││
                    │  │  (Phase-based orchestrator)       ││
                    │  └──┬───┬───┬───┬───┬───┬───────────┘│
                    │     │   │   │   │   │   │            │
                    │     v   v   v   v   v   v            │
                    │  Data  Rsrch Anlys Fin  Strat  Pitch  │
                    │  Agent Agent Agent Agent Agent Agent  │
                    │     │         │               │       │
                    │     v         v               v       │
                    │  Tavily   PVGIS/SMARD      Gemini     │
                    │  Search   APIs             LLM        │
                    └──────────────────────────────────────┘
```

## Agent Pipeline

| Phase | Agent | What it does |
|-------|-------|-------------|
| 1. Data Gathering | `data_gathering` | Collects customer info (skipped when lead data is pre-loaded) |
| 2. Research | `research` | Web search for subsidies, energy prices, competitors |
| 3. Analysis | `analysis` | Geocoding, solar yield (PVGIS), electricity prices (SMARD), bundle tiers |
| 4. Financing | `financial` | KfW/BAFA subsidy application, payment scenarios, age-based alerts |
| 5. Strategy | `strategy` | Value proposition, talking points, objection handling |
| 6. Report | `pitch_deck` | Generates structured pitch deck |

The supervisor auto-chains phases and only pauses for meaningful installer input.

## Demo Flow

1. **Login** — Select a lead from the dashboard
2. **Lead Detail** — Review customer data, upload relevant PDFs
3. **Talk to Cleo** — Agent researches, analyzes, and builds strategy
4. **Voice Mode** — Switch to hands-free conversation with Cleo's avatar
5. **Generate Report** — Structured PDF with packages, financing, and pitch guidance

## Running Locally

```bash
# Prerequisites: Python 3.11+, Node.js 18+, Git

# Clone
git clone https://github.com/hvaddoriya2550-spec/Qhack-2026.git
cd Qhack-2026

# Setup
bash infra/scripts/setup.sh

# Configure
cp backend/.env.example backend/.env
# Add your API keys: GEMINI_API_KEY, SEARCH_API_KEY, ELEVENLABS_API_KEY

# Run
bash dev.sh start

# Open http://localhost:5173
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `SEARCH_API_KEY` | Yes | Tavily search API key |
| `ELEVENLABS_API_KEY` | No | ElevenLabs TTS (falls back to browser speech) |
| `LLM_PROVIDER` | No | `gemini` (default), `anthropic`, or `openai` |

## Team

Built by the Cloover Challenge team at Q-Hack 2026.

## License

MIT
