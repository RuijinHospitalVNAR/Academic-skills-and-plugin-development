# Protein Drug Design Skills Plugin (protein-drug-design)

English | [简体中文](README.md)

A **full-chain** protein drug design skill plugin built on the Trae / Tashan Research Agent Skills framework. As of v0.2.0 it **absorbs all 20 skills from the former Tashan Research plugin** (24 skills in total):

- **Computation mainline** (4 in-house skills): **sequence/structure identification → AI structure prediction & batch analysis → molecular dynamics validation → binding energy & mechanism deepening**
- **Full-chain extensions** (20 adopted skills): literature research → research ideation → pre-collection experiment design & preregistration → post-collection statistical analysis → academic writing → manuscript review → presentation (slides/video/figures) **sequence/structure identification → AI structure prediction & batch analysis → molecular dynamics validation → binding energy & mechanism deepening**. All protocols and criteria are distilled from real research projects (GPCR nanobody design, A9 uricase mechanism study, 48-system 500ns MD extension analysis).

## Directory Layout

```text
protein-drug-design-plugin/
├── .trae-plugin/plugin.json          # Plugin manifest (entry declaration)
├── workflow.yaml                     # Workflow orchestration config (stages/data contracts/extension points)
├── templates/skill-template/         # New-skill skeleton template (extension entry)
└── skills/
    ├── seq-struct-analysis/          # Sequence-structure analysis pipeline
    ├── structure-prediction-analysis/ # Batch structure prediction & result analysis
    ├── md-simulation-workflow/       # Full MD simulation workflow (AMBER-first)
    └── protein-design-workflow/      # End-to-end workflow orchestrator (routing + extension API)
```

## Skills

### Computation mainline (4 in-house)

| Skill | Content | Provenance |
|---|---|---|
| **seq-struct-analysis** | Three-step family-identification (BLAST/Jackhmmer/MMseqs2 sequence layer + Foldseek/TM-align structure layer); data acquisition (NCBI E-utilities, UniProt REST, RCSB, AlphaFold DB); antibody–antigen database acquisition (**local SAbDab2 cache**, CoVAbDab, OAS, IMGT/IgBLAST, IEDB); antibody numbering (**ANARCII transformer first — VNAR requires the dedicated `-t vnar` model**); MEME motif discovery | Distilled from a full case: 290aa unknown protein → α/β-hydrolase family verdict |
| **structure-prediction-analysis** | AF3/Protenix/OpenDDE batch inference (two-stage MSA-first + multi-GPU round-robin + slim transfer); dual-axis quadrant result analysis (confidence × pose convergence, targeted-epitope mode, membrane-side accessibility) | Distilled from MC2R/MC4R VNAR design project (151 candidates × 100 seeds) |
| **md-simulation-workflow** | Full AMBER pipeline (structure prep → BCC/RESP ligand parameterization → tleap triple-guards → min/heat/equil/prod → cpptraj analysis); convergence dual-criteria (core-region RMSD + block-average SEM); five-engine comparison (AMBER/GROMACS/NAMD/CHARMM/OpenMM); CpHMD three prohibitions; QM/MM SCF-convergence root-cause rule; MM/GBSA(PBSA) protocols | Distilled from A9 uricase (4 systems) + 48-system 500–769ns extension project |
| **protein-design-workflow** | Task routing rules, five-stage data contracts, empirical compute-scheduling baselines, four-step onboarding for new skills/engines, inter-stage checkpoints | Orchestration layer design |

### Full-chain extensions (20 adopted)

| Category | Skills |
|---|---|
| Literature & ideation | scispark, sci-employee-deep-research, giiisp-paper-search-apis |
| Design & statistics | experiment-design (preregistration/DOE/power), statistical-analysis, research-baseline-builder |
| Writing & review | academic-writing, scientific-humanization, papercheck, thesis-audit-reviewer |
| Presentation | visual-deck-builder, practical-course-producer, manim-agent, giiisp-scientific-image-generation |
| Tooling & meta | find-science-skills, skill-criticagent, mcp-criticagent |
| Memory & profile | cognitive-profile, research-dream |
| Platform | world-threads-entry (Tashan TopicLab/OpenClaw) |

## Workflow Overview

```text
FASTA ──[seq-struct-analysis]──> family verdict + structural anchor + homolog clusters
   └──[structure-prediction-analysis]──> model.cif + confidence ──> quadrant / pocket analysis
          └──[md-simulation-workflow]──> prmtop (guarded) ──> trajectories + convergence ──> ΔG±SEM / mechanism
```

## Installation

### Option 1: As a Trae plugin
Place this directory under `~/.trae-cn/plugins/<registry>/protein-drug-design/<version>/`. Skills auto-register after restart (descriptions enter the system prompt and load on trigger).

### Option 2: Direct skill install (instant for the agent)
Copy any skill directory under `skills/` into the user-level skills directory:
```bash
for s in md-simulation-workflow seq-struct-analysis protein-design-workflow; do
  cp -r skills/$s ~/.trae-cn/skills/
done
```
Skills become triggerable in the next session. Machine-specific absolute paths referenced by `structure-prediction-analysis` (Amber22, remote servers, etc.) must be rewritten when migrating to another host.

### Option 3: Read-only reference
Every `SKILL.md` and `references/` file is self-contained and can be read directly as a computational protocol handbook for protein drug design.

## Data Sources & Acknowledgements

The data-acquisition module relies on the following public services and databases (each under its own license):

| Resource | Purpose | Source |
|---|---|---|
| NCBI E-utilities / BLAST | Sequence search & acquisition | ncbi.nlm.nih.gov |
| UniProt REST | Protein annotation | uniprot.org |
| RCSB PDB / AlphaFold DB | Structure downloads | rcsb.org / alphafold.ebi.ac.uk |
| SAbDab2 & its AI/ML training set | Antibody–antigen structures with splits (local cache verified SAbDabupdate=20260430) | Capel et al. 2026, bioRxiv doi:10.64898/2026.06.16.732554; data at Zenodo record 20083995 (CC-BY 4.0) |
| CoVAbDab / OAS | Antibody sequence databases | OPIG (opig.stats.ox.ac.uk) |
| ANARCII | Antibody numbering (transformer, native VNAR/VHH models) | github.com/oxpig/ANARCII (BSD-3) |
| MMseqs2 / HMMER / Foldseek | Sequence & structure search | respective official repositories |

## Extending

- **Add a new skill**: copy `templates/skill-template/` → `skills/<new-skill>/`, write the frontmatter (description = trigger conditions only) → register the stage in `workflow.yaml` → add trigger keywords to `plugin.json`.
- **Add a new MD engine**: register an entry in `md-simulation-workflow/references/md-engine-comparison.md`; no orchestrator changes needed.
- **Shared conventions**: official tools first (hand-written scripts must be cross-checked against official output); completion is judged by finalization markers, never by file existence; all parameters carry provenance; one handoff file per project.

## Changelog

- **0.2.0** (2026-09-20): **absorbed all 20 Tashan Research skills** (4 trigger-overlapping skills annotated with boundary statements), registered 6 full-chain stages in workflow.yaml, uninstalled the original Tashan plugin to avoid double-triggering.
- **0.1.1** (2026-09-20): data-acquisition module (general + antibody–antigen databases + local SAbDab2 cache); ANARCII numbering guidelines; internal-endpoint sanitization.
- **0.1.0** (2026-09-20): initial skeleton — four skills + workflow config + extension template.

## License

For research use only. When citing protocols from this plugin, please also cite the corresponding upstream tools and databases (see Acknowledgements).
