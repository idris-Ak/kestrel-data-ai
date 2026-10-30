# Project approach

## Problem, goal and scope

Head office receives inconsistent feedback from 24 dealerships and cannot compare customer experience reliably. The goal was to consolidate those files, establish what can be trusted, analyse negative-feedback themes and trends, and recommend priorities with approximate value. The [brief](BRIEF.md) defines the required deliverables; the [README](../README.md) gives the business answers.

Success meant reconciling every source observation, preserving context and uncertainty, measuring AI performance, answering each business question with clear denominators, and reproducing the calculations. A terminal Q&A interface explains committed aggregate results with source citations; each question is independent and has no raw-comment access.

## Discovery and solution design

The work began with the business questions and success measures, then inspected the supplied files and reference tables. Research and design review compared preparation, privacy, interpretation and evaluation approaches. This led to a small local pipeline with explicit source readers, a traceable SQLite dataset, validation rules, evaluated comment classification and aggregate reporting.

## Implementation and verification

- **Data foundation:** retained native fields and source locations, linked proven copies, separated test records, online reviews and aggregate-only ratings, and preserved unresolved cases through eligibility flags.
- **Quality and privacy:** reconciled counts, protected original hashes and checked reference amounts and joins. Local redaction limited model input to permitted text/context; privacy checks and AI review do not guarantee anonymity.
- **AI interpretation:** compared a keyword baseline and model configurations against blind AI reference labels. Haiku met the acceptance targets and the budget; same-family references and timeliness over-tagging remain explicit limitations. Broader exploration and additional Sonnet validation were limited by API cost.
- **Business analysis:** applied documented rating/mapping assumptions, uncertainty intervals, sensitivity checks and value scenarios. Reproduction used the original pack and hash-pinned private labels; committed evidence contains aggregates only.

## AI collaboration

Claude Code led development, data foundation/preparation and substantial orchestration. ChatGPT/Codex supported research, review and final integration through delegated workstreams. Review corrected a revenue join, excessive name masking and incomplete cache identity. Automated checks and reproduction verify specific properties; no human labelling or privacy certification is claimed. [Methods](METHODS.md) records the evidence and remaining limitations.
