# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-20
### Added
- Contextual best-practices engine: archetype classification, confidence-rated
  applicability, and impact-gated flagging over a declarative YAML rule catalog.
- Coverage of seven areas of Fabric governance (tenant settings & administration,
  capacity & cost, workspace governance, roles & access, domains & data mesh,
  data security, monitoring & deployment).
- Read-only admin API collectors (tenant settings, capacities, workspaces, domains,
  pipelines) with Fabric-notebook and service-principal token providers.
- JSON and Lakehouse Delta writers; `scan()` / `scan_from_signals()` entry points.
- One-click deploy notebook (`notebooks/00_deploy.ipynb` / `.py`) that provisions the
  findings Lakehouse, runs the scan, and deploys a Direct Lake semantic model with
  prebuilt measures. Manual `notebooks/01_run_scanner.py` path also provided.
- Power BI `.pbip` project (Direct Lake semantic model + starter report) and an
  auto-deploy path via `semantic-link-labs`.
- Optional Azure OpenAI rationale enrichment (never decides status/applicability).

[Unreleased]: https://github.com/Diaz506/fabric-best-practices-scanner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Diaz506/fabric-best-practices-scanner/releases/tag/v0.1.0
