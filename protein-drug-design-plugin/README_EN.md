# Protein Drug Design & Full-Chain Research Skills Plugin (protein-drug-design)

English | [简体中文](README.md)

A **full-chain** protein drug design skill plugin (v0.4.0, **47 skills**):

- **Computation mainline** (4 in-house skills, empirically distilled): **sequence/structure identification → AI structure prediction & batch analysis → molecular dynamics validation → binding energy & mechanism deepening**
- **Management & meta**: skill-manager (skill lifecycle governance)
- **Full-chain extensions** (39 adopted skills): literature research → research ideation → pre-collection experiment design & preregistration → post-collection statistical analysis → academic writing → manuscript review → presentation (slides/video/figures/patent drafts/experiment logs)

## Directory Layout

```text
protein-drug-design-plugin/
├── .trae-plugin/plugin.json          # Plugin manifest (entry declaration)
├── workflow.yaml                     # Workflow config (11 stages/data contracts/extension points)
├── install.sh                        # Multi-IDE / desktop-agent installer
├── data/                             # Skill ledger + append-only audit log (skill-manager)
├── templates/skill-template/         # New-skill skeleton template
└── skills/                           # 47 skills (incl. skill-manager)
    ├── (computation mainline, 4)     # seq-struct-analysis / structure-prediction-analysis /
    │                                 # md-simulation-workflow / protein-design-workflow
    ├── (management & meta, 5)        # skill-manager / periodic-review / project-viz /
    │                                 # cognitive-profile / research-dream
    ├── (research chain, 18)          # academic-writing / bizard / scispark / experiment-design /
    │                                 # statistical-analysis / papercheck / visual-deck-builder / ...
    └── (nature-skills, 20)           # nature-writing / nature-reviewer / nature-paper-card /
                                      # nature-figure / nature-paper-to-patent / ...
```

## Skills

### Computation mainline (4 in-house)

| Skill | Content | Provenance |
|---|---|---|
| **seq-struct-analysis** | Three-step family identification (BLAST/Jackhmmer/MMseqs2 + Foldseek/TM-align); data acquisition (NCBI/UniProt/RCSB/AFDB + **local SAbDab2 cache**/CoVAbDab/OAS/IMGT/IEDB); antibody numbering (**ANARCII transformer first — VNAR requires `-t vnar`**); MEME motif discovery | Full case: 290aa unknown protein → α/β-hydrolase verdict |
| **structure-prediction-analysis** | AF3/Protenix/OpenDDE batch inference (MSA-first + multi-GPU round-robin + slim transfer); dual-axis quadrant analysis (targeted epitope + membrane-side accessibility) | MC2R/MC4R VNAR project (151 candidates × 100 seeds) |
| **md-simulation-workflow** | Full AMBER pipeline (BCC/RESP parameterization → tleap triple-guards → equilibration/production → cpptraj); convergence dual-criteria (core-region RMSD + block-average SEM); five-engine comparison; CpHMD/QM/MM/MM-GBSA protocols | A9 uricase + 48-system 500–769ns extension |
| **protein-design-workflow** | Task routing, 11-stage data contracts, compute-scheduling baselines, extension onboarding | Orchestration layer |

### Management & meta

**skill-manager** — skill lifecycle governance: semi-automatic add (compare-then-decide absorb/merge/reject), ledger + append-only audit log, single & batch modes (see dedicated section below).

**periodic-review** — cross-project periodic review (daily/weekly/monthly/quarterly/annual; meta-workflow skill, not registered in workflow.yaml stages): aggregates per-project `handoff-*.md` into a weekly status matrix (machine-aggregated section vs. user-decision section kept separate; the latest weekly "priorities" act as the default action order for subsequent sessions); monthly priority-fulfillment audit & lesson-promotion review; quarterly publication/delivery anchor assessment (forward-looking layer); new-session cold-start protocol. Ships a portable **daily_audit trio** in `scripts/` (read-only static auditor v1.1: cron-03:00 output anomaly patrol with `--since-days` time window, headerless BLAST TSV false-positive guard, same-file dedup; 5-step deployment guide in SKILL.md).

**project-viz** — Mermaid project-progress visualization: gantt/timeline progress charts, pipeline/workflow diagrams, handoff-text→timeline retrospectives; a pre-commit hook auto-refreshes the progress chart on handoff changes.

**cognitive-profile / research-dream** — (adopted) incremental user-preference profiling / research memory consolidation (USER·SOUL·MEMORY + periodic "dream" consolidation).

### Full-chain extensions (38 adopted)

| Category | Skills |
|---|---|
| Literature & ideation | scispark, sci-employee-deep-research, giiisp-paper-search-apis, nature-academic-search, nature-literature-pipeline, nature-citation, nature-paper-card |
| Design & statistics | experiment-design (preregistration/DOE/power), statistical-analysis, research-baseline-builder, nature-statistics, nature-experiment-log |
| Writing & review | academic-writing, scientific-humanization, papercheck, thesis-audit-reviewer, nature-writing, nature-polishing, nature-reader, nature-reviewer, nature-response, nature-ref-verifier |
| Presentation & translation | visual-deck-builder, bizard (798-example biomedical figure atlas), practical-course-producer, manim-agent, giiisp-scientific-image-generation, nature-paper2ppt, nature-image2ppt, nature-figure, nature-paper-to-patent |
| Proposals & data compliance | nature-proposal-writer, nature-data, nature-downloader |
| Tooling & meta | find-science-skills, skill-criticagent, mcp-criticagent, nature-shared |

> Trigger-surface governance: the 4 skills overlapping the computation mainline (experiment-design / statistical-analysis / scispark / research-baseline-builder) carry **boundary statements** in their descriptions (e.g. "MD convergence criteria go to md-simulation-workflow") to prevent double-triggering.

## Workflow Overview

```text
[0a]scispark ideation ─[0b]experiment-design preregistration
  v
FASTA ──[seq-struct-analysis]──> family verdict + structural anchor
   └──[structure-prediction-analysis]──> model.cif + confidence ──> quadrant / pocket analysis
          └──[md-simulation-workflow]──> prmtop (guarded) ──> trajectories + convergence ──> ΔG±SEM / mechanism
                └─[statistical-validation]─[writing]─[review]─[presentation]
```

Full contracts for the 11 stages: [workflow.yaml](workflow.yaml).

## Installation (multi-IDE / desktop agents)

**Zero-command install**: paste the prompt from [agent-install.md](agent-install.md) to your AI assistant — it clones, detects, installs and verifies automatically (Chinese & English prompts included).

The repo ships `install.sh`, which copies `skills/` into each tool's skill directory:

| Target | Command | Skill directory |
|---|---|---|
| Trae / Trae CN | `bash install.sh trae` | `~/.trae-cn/skills` (or `~/.trae/skills`) |
| Claude Code | `bash install.sh claude` | `~/.claude/skills` |
| OpenAI Codex CLI | `bash install.sh codex` | `~/.codex/skills` (`$CODEX_HOME`) |
| Cursor | `bash install.sh cursor` | `~/.agents/skills` + rules pointer line |
| Windsurf | `bash install.sh windsurf` | `~/.agents/skills` + rules pointer line |
| OpenCode | `bash install.sh opencode` | `~/.config/opencode/skills` |
| OpenClaw / desktop agents | `bash install.sh openclaw` | `~/.agents/skills` (agents-skills spec) |
| Help | `bash install.sh list` | — |

Rationale: the Agent Skills spec (agentskills.io) is the emerging cross-tool standard; tools differ only in skill-directory location. Cursor/Windsurf have no native loader — the script prints a pointer line to add to project rules. Community CLI alternative: `npx skills add RuijinHospitalVNAR/Academic-skills-and-plugin-development --skill '*' --yes --copy`.

### Skill visibility & language strategy

Skills have two layers: **description** (always-on in the system prompt, decides triggering — what the audience sees first) is fully bilingual (Chinese skills carry an `EN:` summary line; English skills carry Chinese trigger aliases). **Bodies & references** (loaded on trigger) remain primarily Chinese: the provenance records are native Chinese and mechanical translation would distort them; heavy references will be English-localized incrementally as needed.

## Skill Lifecycle Management (skill-manager)

The built-in `skill-manager` skill governs add/merge/remove for all plugin skills:

- **ADD (semi-automatic)**: signal capture (≥2 recurrences / >1h debugging / user-named) → draft generation (asks the user at key points) → `compare.py` similarity vs existing skills (description Jaccard + body bigram + trigger conflicts) → three-way decision (**absorb / merge / reject**) → `ledger.py` registration
- **REMOVE**: signals (platform sunset / long-untriggered / superseded) → user confirmation → automatic tar backup + three-location cleanup + workflow.yaml reference removal
- **Traceable & auditable**: `data/skills-ledger.json` (full decision history per skill) + `data/audit-log.jsonl` (**append-only**, with user_confirmed flag)
- **Single & batch modes**: individual commands or `ledger.py batch <file>`; `--dry-run` supported

## Data Sources & Acknowledgements

| Resource | Purpose | Source |
|---|---|---|
| NCBI E-utilities / BLAST / IgBLAST | Sequence search & acquisition | ncbi.nlm.nih.gov |
| UniProt REST | Protein annotation | uniprot.org |
| RCSB PDB / AlphaFold DB | Structure downloads | rcsb.org / alphafold.ebi.ac.uk |
| SAbDab2 & AI/ML training set | Antibody–antigen structures with splits | Capel et al. 2026, bioRxiv doi:10.64898/2026.06.16.732554; Zenodo 20083995 (CC-BY 4.0) |
| CoVAbDab / OAS | Antibody sequence databases | OPIG (opig.stats.ox.ac.uk) |
| Bizard atlas | [openbiox/Bizard](https://github.com/openbiox/Bizard) | 798 reproducible R/Python/Julia figure tutorials & gallery index (CC-BY-NC) |
| ANARCII | Antibody numbering (transformer, native VNAR model) | github.com/oxpig/ANARCII (BSD-3) |
| MMseqs2 / HMMER / Foldseek / MEME Suite | Sequence/structure search & motifs | respective official channels |
| nature-skills | 20 adopted skills | github.com/Yuan1z0825/nature-skills (Apache-2.0) |

## Extending

- **Add a skill**: go through the skill-manager flow, or manually copy `templates/skill-template/` → trigger-only frontmatter → register in `workflow.yaml` → add keywords to `plugin.json` → `ledger.py add`.
- **Add an MD engine**: register in `md-simulation-workflow/references/md-engine-comparison.md`; zero orchestrator changes.
- **Shared conventions**: official tools first; completion judged by finalization markers, never file existence; all parameters carry provenance; one handoff per project.

## Changelog

- **0.7.0** (2026-11-12): periodic-review deepened into the five-layer review — new daily layer (portable daily_audit trio v1.1: --since-days time window / headerless BLAST TSV false-positive guard / same-file dedup), monthly/quarterly/annual procedures, new-session cold-start protocol; README reconciliation (bizard / cognitive-profile / research-dream registered, 0.5–0.6 changelog backfilled).
- **0.6.0** (2026-10-19): added project-viz (#47, Mermaid progress/pipeline visualization + pre-commit auto-refresh hook).
- **0.5.0** (2026-10-08): adopted bizard (openbiox/Bizard, CC-BY-NC, 798-example biomedical figure atlas); periodic-review (#46, cross-project periodic review) joined on 2026-10-15 under this version.
- **0.4.0** (2026-09-20): added the skill-manager lifecycle module (semi-automatic generation → compare-based absorb/merge/reject → ledger + audit; single/batch modes; all 47 skills registered).
- **0.3.0** (2026-09-20): adopted the complete nature-skills suite (20 skills, bilingual descriptions); added multi-IDE/desktop installer `install.sh`; removed platform-bound world-threads-entry.
- **0.2.0** (2026-09-20): adopted 20 research-chain skills (4 boundary statements), 6 full-chain stages registered.
- **0.1.1** (2026-09-20): data-acquisition module (general + antibody–antigen + local SAbDab2 cache); ANARCII guidelines; endpoint sanitization.
- **0.1.0** (2026-09-20): initial skeleton.

## License

In-house portions are for research use. Adopted skills retain their original licenses (nature-skills under Apache-2.0; others per their release terms, with upstream attribution preserved inside each skill directory). When citing protocols, please also cite the upstream tools and databases (see Acknowledgements).
