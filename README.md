# grid-wizard-openclaw-skill
A pragmatic, source-available RLUSD⇄XRP grid engine with a lightweight UI, hot-reloadable `.env`, strict caps + pending queues, optional distance auto-cancel, and a tiny AI “breathing layer” (Dynamic Grid Optimizer + **DipsCount** dip-buyback). Built for reliability under XRPL node lag.

## Open Source

Grid Wizard OpenClaw Skill is open source under the MIT License.

Our goal is to make autonomous crypto trading tools accessible to everyone.
Developers are encouraged to fork, extend, and integrate this skill into
their own AI agents, trading systems, or OpenClaw deployments.

If you build something cool with it, we'd love to see it.

## Local development

### Local run command (skill entrypoint)

```bash
PYTHONPATH=src python -m grid_wizard_openclaw_skill --manifest manifest/skill_manifest.json
```

### CI-friendly commands

Run each command individually:

```bash
python -m compileall -q src tests scripts
python scripts/validate_manifest.py
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

Or run everything at once:

```bash
./scripts/ci_checks.sh
```

These commands are designed to run in a clean environment without installing third-party packages.
