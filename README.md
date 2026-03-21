# grid-wizard-openclaw-skill
A pragmatic, source-available RLUSD⇄XRP grid engine with a lightweight UI, hot-reloadable `.env`, strict caps + pending queues, optional distance auto-cancel, and a tiny AI “breathing layer” (Dynamic Grid Optimizer + **DipsCount** dip-buyback). Built for reliability under XRPL node lag.

## Open Source

Grid Wizard OpenClaw Skill is open source under the MIT License.

Our goal is to make autonomous crypto trading tools accessible to everyone.
Developers are encouraged to fork, extend, and integrate this skill into
their own AI agents, trading systems, or OpenClaw deployments.

If you build something cool with it, we'd love to see it.


## Quickstart

```bash
python -m grid_wizard_openclaw_skill --help
python -m grid_wizard_openclaw_skill --dry-run
```

### Skill package layout
- `SKILL.md` describes usage and extension notes.
- `manifest.json` includes dependency metadata.
- `grid_wizard_openclaw_skill/entrypoint.py` provides the module entrypoint.
