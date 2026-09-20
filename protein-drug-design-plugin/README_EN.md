# Protein Drug Design & Full-Chain Research Skills Plugin (protein-drug-design)

English | [简体中文](README.md)

A **full-chain** protein drug design skill plugin built on the Tashan Research Agent Skills framework (v0.4.0, **44 skills**):

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
└── skills/                           # 44 skills (incl. skill-manager)
    ├── (computation mainline, 4)     # seq-struct-analysis / structure-prediction-analysis /
    │                                 # md-simulation-workflow / protein-design-workflow
    ├── (management, 1)               # skill-manager (add/merge/remove + ledger & audit)
    ├── (Tashan Research, 19)         # academic-writing / scispark / experiment-design /
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

### Full-chain extensions (39 adopted)

| Category | Skills |
|---|---|
| Literature & ideation | scispark, sci-employee-deep-research, giiisp-paper-search-apis, nature-academic-search, nature-literature-pipeline, nature-citation, nature-paper-card |
| Design & statistics | experiment-design (preregistration/DOE/power), statistical-analysis, research-baseline-builder, nature-statistics, nature-experiment-log |
| Writing & review | academic-writing, scientific-humanization, papercheck, thesis-audit-reviewer, nature-writing, nature-polishing, nature-reader, nature-reviewer, nature-response, nature-ref-verifier |
| Presentation & translation | visual-deck-builder, practical-course-producer, manim-agent, giiisp-scientific-image-generation, nature-paper2ppt, nature-image2ppt, nature-figure, nature-paper-to-patent |
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
| ANARCII | Antibody numbering (transformer, native VNAR model) | github.com/oxpig/ANARCII (BSD-3) |
| MMseqs2 / HMMER / Foldseek / MEME Suite | Sequence/structure search & motifs | respective official channels |
| Tashan Research (tashan-research-skills) | 19 adopted skills (original plugin uninstalled; backup kept locally) | UCAS Tashan (tashan.ac.cn) |
| nature-skills | 20 adopted skills | github.com/Yuan1z0825/nature-skills (Apache-2.0) |

## Extending

- **Add a skill**: go through the skill-manager flow, or manually copy `templates/skill-template/` → trigger-only frontmatter → register in `workflow.yaml` → add keywords to `plugin.json` → `ledger.py add`.
- **Add an MD engine**: register in `md-simulation-workflow/references/md-engine-comparison.md`; zero orchestrator changes.
- **Shared conventions**: official tools first; completion judged by finalization markers, never file existence; all parameters carry provenance; one handoff per project.

## Changelog

- **0.4.0** (2026-09-20): added the skill-manager lifecycle module (semi-automatic generation → compare-based absorb/merge/reject → ledger + audit; single/batch modes; all 44 skills registered).
- **0.3.0** (2026-09-20): adopted the complete nature-skills suite (20 skills, bilingual descriptions); added multi-IDE/desktop installer `install.sh`; removed platform-bound world-threads-entry.
- **0.2.0** (2026-09-20): absorbed all 20 Tashan Research skills (4 boundary statements), 6 full-chain stages registered; original plugin uninstalled.
- **0.1.1** (2026-09-20): data-acquisition module (general + antibody–antigen + local SAbDab2 cache); ANARCII guidelines; endpoint sanitization.
- **0.1.0** (2026-09-20): initial skeleton.

## License

In-house portions are for research use. Adopted skills retain their original licenses (Tashan entries per their release terms; nature-skills under Apache-2.0). When citing protocols, please also cite the upstream tools and databases (see Acknowledgements).
