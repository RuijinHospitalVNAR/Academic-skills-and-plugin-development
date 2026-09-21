# Academic Skills and Plugin Development

English | [简体中文](README.md)

A repository for **Agent Skills plugin development** for research and protein drug design. The main deliverable is [protein-drug-design-plugin/](protein-drug-design-plugin/) — a 44-skill full-chain research plugin — alongside reusable security infrastructure for safe development (three-layer secret protection).

## Repository Layout

```text
Academic-skills-and-plugin-development/
├── protein-drug-design-plugin/   # ★ core plugin (44 skills, bilingual README, install-and-use)
│   ├── README.md / README_EN.md  #    full plugin docs (skill list / workflow / multi-IDE install)
│   ├── install.sh                #    one-shot adapter for Trae/Claude Code/Codex/Cursor etc. (8 targets)
│   └── skills/                   #    44 skills
├── scripts/
│   ├── secret-scan.py            # local pre-commit secret scanner
│   └── secret-scan-ci.py         # server-side enforced scan (incl. full-history blobs)
└── .github/workflows/secret-scan.yml
```

## Core Plugin: protein-drug-design (44 skills)

- **Computation mainline** (4 in-house, empirically distilled): sequence/structure identification → AF3 structure prediction & batch analysis → molecular dynamics (AMBER-first) → binding energy & mechanism deepening
- **Management**: skill-manager (skill lifecycle: add/merge/remove + auditable ledger)
- **Full chain** (39 adopted): literature research, research ideation, experiment design, statistical analysis, academic writing, manuscript review, presentation (slides/video/figures/patents/experiment logs)

Quick install (details in the [plugin README](protein-drug-design-plugin/README_EN.md)):

```bash
git clone https://github.com/RuijinHospitalVNAR/Academic-skills-and-plugin-development.git
cd Academic-skills-and-plugin-development/protein-drug-design-plugin
bash install.sh trae     # or claude / codex / cursor / windsurf / opencode / openclaw
```

## Security Infrastructure (practiced in this repo)

This repository went through a full leak remediation (history rewrite + key rotation) and built a reusable three-layer defense from the lessons:

| Layer | Tool | Blocks |
|---|---|---|
| File level | `.gitignore` | key/credential files being added |
| Local content level | `scripts/secret-scan.py` (pre-commit hook) | tokens/private keys/IPs/local paths leaking at commit time |
| Server-enforced | `scripts/secret-scan-ci.py` (GitHub Actions) | `--no-verify` bypasses + **full-history blob smuggling** |

Scan rules: private-key blocks, GitHub/OpenAI/AWS/Slack/HuggingFace/Google tokens, hardcoded credentials, public IPs (local ranges & version numbers exempted), local user/data paths. Both scanners share one rule library — keep them in sync.

## License

In-house portions are for research use; adopted skills retain their original licenses (see the [plugin acknowledgements](protein-drug-design-plugin/README_EN.md#data-sources--acknowledgements)).
