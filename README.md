# Competitor Radar

**AI Competitive Intelligence for Fintech** — built for the Lyzr AI Weekly Challenge #1: Agents for GTM

Competitor Radar discovers your real competitors, tracks what they're doing, and gives your team response options — without ever automatically changing your pricing on its own.

## The problem

Competitive intelligence in fast-moving markets (like fintech and bank-to-bank payments) is usually either:
- **Manual and stale** — someone checks competitor pricing pages once a quarter and builds a battlecard nobody updates again, or
- **Reactive and dangerous** — a competitor drops their price, and the team's instinct is to immediately match it, without checking whether it's a one-off promo or a real trend, and without considering non-price responses.

Competitor Radar is built to fix both problems: continuous detection instead of stale manual checks, and disciplined human-reviewed options instead of automatic price wars.

## How it works

Three agents, run in sequence:

### 1. Competitor Finder
Takes a plain-language description of your company (what you do, who you serve, what region you operate in) and searches live to identify 3–5 real, currently operating competitors. It:
- Separates competitors by region if you mention expansion markets
- Prioritizes competitors that actually match your business model (e.g. infrastructure/API players, not just the most famous consumer app), rather than defaulting to whichever names are most well-known
- Rates each match's confidence as HIGH / MEDIUM / LOW instead of presenting every guess with false certainty

### 2. Competitor Analyst
Takes one competitor (chosen by a human from the Finder's list) plus an optional previous observation, and:
- Searches for current public pricing, fees, transfer limits, settlement speed, and feature information
- Compares it against the last known state
- Flags only material changes (not cosmetic wording differences)
- Classifies a detected change as **ONE-OFF** or **TREND** — and says so explicitly when there isn't enough history to know

### 3. Response Options
Takes a detected change and generates response options for a human to review. Hard rules baked into this agent:
- Never recommends price-matching as the only or default option
- At least 2 of 3 options are always non-price responses (positioning, service/reliability levers, targeted response, or hold-and-monitor)
- If the change is a one-off or unclassified, "hold and monitor" is always one of the options
- Every output ends with explicit routing to a human decision-maker — **no automated action is ever taken**

## Why the restraint matters

It would be easy to build an agent that sees a competitor's price change and auto-generates a matching counter-offer. That's not competitive intelligence — it's an automated price war trigger, and it's visible to customers as soon as it happens. Competitor Radar is deliberately designed to shorten the time between "a competitor moved" and "a human has full context," not to close that loop automatically. Detection and analysis are the agent's job. Strategy stays human.

## Architecture

```
Company description
        ↓
  Competitor Finder  (web search, region-aware, category-matched)
        ↓
  [human selects a competitor to monitor]
        ↓
  Competitor Analyst  (search + compare vs. previous observation)
        ↓
  Response Options  (never price-matching only, always human-routed)
```

Built with [Lyzr Agent Studio](https://www.lyzr.ai/). Frontend built with Antigravity.

## Current scope and honest limitations

This is a challenge-scoped MVP, and it's built to be upfront about what's automated and what isn't:

- **Discovery is one-time per company.** A company's competitive landscape doesn't change weekly, so this runs once to establish the competitor set.
- **Monitoring is manually triggered.** A user re-runs the Analyst agent when they want a fresh check, providing the last known observation. Persistent, scheduled, fully automated tracking (no human re-triggering required) is the natural next iteration, using structured storage instead of manual snapshot input.
- **Competitor selection is a human step, by design.** After discovery, a person chooses which competitor(s) to actually monitor rather than the system auto-tracking everything it finds. This keeps judgment in the loop on what actually matters to the business.

## Tech stack

- Lyzr Agent Studio (agent orchestration, web search tools)
- Python backend (`main.py`, `lib/lyzr_service.py`)
- Static frontend (HTML/CSS/JS)
- Built and deployed with Antigravity

## Running locally

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your own Lyzr API credentials (never commit your real `.env`)
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run:
   ```
   python main.py
   ```

## Roadmap

- Persistent snapshot storage so monitoring doesn't require manual re-entry of prior observations
- Scheduled, automated recurring checks per tracked competitor
- Slack/email delivery of Response Options output for direct team routing
- Broader competitor category diversity (consumer + infra) surfaced by default in a single Finder pass

---

Built for the Lyzr AI Weekly Challenge #1: Agents for GTM.