# grid-wizard-openclaw-skill

A pragmatic, source-available RLUSD⇄XRP grid engine with a lightweight UI, hot-reloadable `.env`, strict caps + pending queues, optional distance auto-cancel, and a tiny AI “breathing layer” (Dynamic Grid Optimizer + **DipsCount** dip-buyback). Built for reliability under XRPL node lag.

## Open Source

Grid Wizard OpenClaw Skill is open source under the MIT License.

Our goal is to make autonomous crypto trading tools accessible to everyone.
Developers are encouraged to fork, extend, and integrate this skill into
their own AI agents, trading systems, or OpenClaw deployments.

If you build something cool with it, we'd love to see it.

---

## Install

1. Clone this repository.
2. Create your runtime environment file:

```bash
cp .env.example .env
```

3. Edit `.env` and set real wallet + API credentials.
4. Keep `DRY_RUN=true` for your first validation run.

## Verify

Use these checks before enabling live execution:

1. Confirm the skill instructions exist:

```bash
test -f SKILL.md && echo "SKILL.md found"
```

2. Confirm environment template is available:

```bash
test -f .env.example && echo ".env.example found"
```

3. Validate your `.env` includes required secrets and endpoints.

## First runnable flow (API-only smoke test)

After your engine process is running on `PORT` (default `8787`), run:

```bash
# 1) Health check
curl -sS http://localhost:8787/health

# 2) Start strategy (requires API key from .env)
curl -sS -X POST http://localhost:8787/control/start \
  -H "x-api-key: $API_KEY"

# 3) Inspect live state
curl -sS http://localhost:8787/state \
  -H "x-api-key: $API_KEY"

# 4) Pause strategy safely
curl -sS -X POST http://localhost:8787/control/pause \
  -H "x-api-key: $API_KEY"
```

Expected behavior:

- `/health` returns an `ok`-style response.
- `/control/start` returns accepted/armed status.
- `/state` includes grid levels, pending queues, and risk cap counters.
- `/control/pause` confirms strategy is paused.

## First release tag

Tag the first release after merging to your default branch:

```bash
git tag -a v0.1.0 -m "First release: baseline skill + env + API smoke flow"
git push origin v0.1.0
```
