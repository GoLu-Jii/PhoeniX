# Phoenix — Competitive Engineering Intelligence

> **Turn scattered public footprints into actionable competitive intelligence.**
> See what a tech company is building before it announces it.

[![Phoenix Hero Banner](docs/images/phoenix-hero.png)](https://youtu.be/BEzJULsvzJM)

- **Demo Video:** [https://youtu.be/BEzJULsvzJM](https://youtu.be/BEzJULsvzJM)
- **GitHub Repository:** [https://github.com/GoLu-Jii/PhoeniX](https://github.com/GoLu-Jii/PhoeniX)

---

## The Story Behind Phoenix

Imagine you're a startup founder trying to figure out what your competitors are doing. You'd have to dig through their GitHub repos, job postings, websites, and social media, then connect all the dots yourself. And even after all that, you're still mostly guessing.

**That's why I built Phoenix.**

The current prototype investigates a company's GitHub activity and compares its engineering work with what it claims on its website. The bigger vision is to bring in job postings and social media too.

Imagine a company starts hiring blockchain engineers, its GitHub shows blockchain-related development, and a few months later it announces a new blockchain product. What if you could connect those signals earlier?

**That's what Phoenix aims to do: turn scattered public information into competitive intelligence, helping founders spend less time digging and more time planning their next move.**

---

## Problem & Solution Overview

### The Problem
Tech companies announce last. They ship first. By the time a competitor issues a press release or publishes a product launch, they have already spent 3 to 6 months developing code, reorganizing repositories, and laying technical groundwork.

Founders looking for early competitive intelligence face three obstacles:
1. **Scattered Evidence:** Public traces are fragmented across repositories, commits, and corporate websites.
2. **Maintenance Noise:** Routine chores (version bumps, documentation changes, CI updates) mask genuine product moves.
3. **Say-Do Gaps:** Marketing hype frequently diverges from verifiable technical reality.

### The Solution: Phoenix
Phoenix automates competitive reconnaissance by cross-referencing public GitHub engineering activity against official marketing narratives:
- **Footprint Extraction:** Maps repositories, 45-day commit velocity, and burst pacing.
- **Narrative Harvesting:** Scrapes and distills official website taglines and product claims.
- **Say-Do Matrix Arbitration:** Uses Groq AI to evaluate claims against verifiable code evidence without ungrounded speculation.
- **Signal Filtering:** Distinctly isolates substantive functional changes from routine maintenance.

---

## Technologies & AI Tools Used

- **AI & LLM Inference:** Groq Cloud API (`llama-3.3-70b-versatile`) with two-stage chained execution, commit batching, exponential retry backoff, and strict JSON schemas.
- **Backend Infrastructure:** Python 3.11, FastAPI, Uvicorn, BeautifulSoup4 (SSRF-hardened homepage extraction), HTTPX, Pydantic.
- **Frontend & Visual System:** React 19, TypeScript, Vite, Hacktoberfest 2026 Retro-Editorial Design System (Deep forest slate `#28453a`, vibrant coral-red `#ff6f59`, warm cream `#f6f4ee`, 2px solid retro borders, 4px-6px hard drop shadows, Plus Jakarta Sans, Space Mono).
- **Code Quality & Testing:** Pytest (47 tests passing), Oxlint, ESLint.

---

## How It Works

Phoenix takes a GitHub organization URL and an optional company website URL, runs a multi-stage investigation, and uncovers the gaps between marketing promises and actual code commits:

1. **GitHub Activity Analysis:** Ingests public repositories, 45-day commit velocity, and burst pacing.
2. **Website Claim Extraction:** Pulls official product claims and marketing taglines.
3. **Say-Do Synthesis:** Cross-examines website claims against public commit reality using Groq AI.

### Company Overview & Signals

![Company Overview](docs/images/company-overview.png)

### Claim vs. Evidence Matrix

![Claim vs. Evidence Matrix](docs/images/claim-evidence-matrix.png)

---

## How the Project Evolved Through Both Challenge Cards

Phoenix was built during the 24-hour **Grevix AfterCode** hackathon, navigating two major disruptions:

### Phase 1: Ignition (00:00 - 08:00 IST) — The Foundation
- Built bounded GitHub data collection, 45-day commit parsing, language distribution analysis, and deterministic commit burst detection.
- Prototyped rule-based signal grouping and initial Groq LLM integration.

### Challenge Card 1: The Shift (08:30 - 16:00 IST) — Adapting to External Narratives
- **The Disruption:** Analyzing code in isolation only revealed half the picture; understanding strategic intent required comparing engineering traces against what companies tell the public.
- **How Phoenix Adapted:**
  - Added an SSRF-hardened BeautifulSoup web collector to scrape official company homepages.
  - Implemented a two-stage Groq LLM pipeline: Stage 1 detects code signals and bursts; Stage 2 arbitrates company claims against engineering traces to produce a Say-Do comparative matrix.
  - Implemented compact payload optimization (>99% payload size reduction) and exponential retry backoff on HTTP 429 rate limits.

### Challenge Card 2: Pressure Test (16:30 - 00:00 IST) — Real-World Feedback
- **The Disruption:** Real-world feedback gathered from external developers on Reddit highlighted a critical flaw: commit volume alone does not equal a product announcement. Routine maintenance (dependency bumps, docs, tests) was falsely inflating activity signals.
- **How Phoenix Adapted:**
  - Added "Notable Changes (Last 30 Days)" in the analysis engine and UI.
  - Separated substantive feature/functional changes from routine maintenance and chores with dedicated visual tags and interactive filter tabs.
  - Grounded all findings in inspectable supporting commit messages.

---

## Real-World Feedback — Challenge Card 2

Phoenix was shared on Reddit to get honest feedback from people outside the development process.

### What people told me
One commenter highlighted an important weakness in the current approach:
> "Instead of just listing the repos, summarize the actual big changes from the last month. Don't let standard maintenance look like a new product announcement."

This pointed out something important: a high commit count doesn't necessarily mean a company is building something new. Routine fixes, documentation updates, tests, and version bumps can make a repository look very active without indicating a major product change.

### What I changed
In response, I improved Phoenix's investigation results to distinguish meaningful engineering changes from routine maintenance. The aim is to highlight significant feature additions and functional changes from recent commit history, while treating documentation updates, tests, and housekeeping as separate activity.

Phoenix also keeps supporting commit evidence available so users can inspect why a change was highlighted, rather than taking the AI's interpretation at face value.

### Feedback evidence

![Reddit Post and Feedback](feedback/screenshots/reddit-feedback.png)

- [View Reddit Post Image](feedback/screenshots/reddit-post.png)
- [View Reddit Feedback Image](feedback/screenshots/reddit-feedback.png)

The feedback has influenced how Phoenix presents engineering signals: the goal is to explain what changed, not simply count activity.

### Development records
- [Build Log](build_log.md)
- [Decision Log](DECISIONS.md)

---

## Quickstart & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Groq API Key (https://console.groq.com)
- Optional: GitHub Personal Access Token (avoids GitHub rate limits)

### 1. Environment Setup

```bash
git clone https://github.com/GoLu-Jii/PhoeniX.git
cd PhoeniX
cp .env.example .env
```

Configure `.env`:
```env
GITHUB_TOKEN=your_github_token_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 2. Backend (FastAPI)

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --app-dir backend --port 8000
```

Backend runs at `http://127.0.0.1:8000` (Swagger docs at `/docs`).

### 3. Frontend (React 19 + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Requests to `/api` are automatically proxied to port 8000.

---

## API Endpoints

- `GET /health` - Service health check
- `POST /api/investigations` - Complete company investigation (GitHub traces + Website claims + Say-Do matrix)
- `POST /api/signals` - GitHub commit analysis and burst signals
- `POST /api/analyze` - Say-Do synthesis on pre-extracted data

---

## Running Tests

```bash
# Run all 47 backend tests
pytest backend/tests -v

# Run frontend lint and production build
cd frontend
npm run lint
npm run build
```

---

## Future Roadmap

- Job board and hiring wave tracking (Greenhouse, Lever, LinkedIn)
- Release and changelog diff monitoring
- Launch timeline predictions
- Automated competitor shift alerts

---

## License

MIT (c) 2026 Phoenix Contributors. Built for competitive intelligence & open-source verification.
