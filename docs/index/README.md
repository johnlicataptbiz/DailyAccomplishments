# Documentation Index

**Last Updated:** 2025-12-15

This index maps all documentation in the repository, indicating what's current vs. archived.

## Getting Started (Priority Reading)

| Document | Purpose | Time to Read |
|----------|---------|--------------|
| **[README.md](../../README.md)** | Project overview, features, quick start | 5 min |
| **[QUICKSTART.md](../../QUICKSTART.md)** | Get up and running in 10 minutes | 10 min |
| **[INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md)** | Integrate with existing activity trackers | 15 min |
| **[examples/README.md](../../examples/README.md)** | API reference and code examples | 10 min |

## Planning & Roadmap

| Document | Purpose |
|----------|---------|
| **[ROADMAP.md](../../ROADMAP.md)** | Future features, planned integrations, and enhancements |

## Design & Architecture

| Document | Purpose |
|----------|---------|
| **[docs/design/IMPROVEMENTS.md](../design/IMPROVEMENTS.md)** | Technical architecture and engineering decisions |
| **[docs/design/Daily_Work_Story_Engine_Design_Overview.md](../design/Daily_Work_Story_Engine_Design_Overview.md)** | Narrative-first "Daily Work Story Engine" specification |
| **[docs/design/Methodology_Updated.md](../design/Methodology_Updated.md)** | Timeline aggregation methodology and definitions |
| **[docs/design/INTEGRATION_TASKS.md](../design/INTEGRATION_TASKS.md)** | Historical integration task tracking (reference) |

## Operations & Maintenance

| Document | Purpose |
|----------|---------|
| **[docs/ops/HANDOFF.md](../ops/HANDOFF.md)** | Production operations and automation guide |
| **[docs/ops/PR_CLEANUP_GUIDE.md](../ops/PR_CLEANUP_GUIDE.md)** | PR hygiene and cleanup procedures |
| **[docs/ops/BRANCH_CLEANUP_README.md](../ops/BRANCH_CLEANUP_README.md)** | Branch cleanup workflow |
| **[docs/ops/BRANCH_CLEANUP_CHECKLIST.md](../ops/BRANCH_CLEANUP_CHECKLIST.md)** | Branch cleanup checklist |
| **[docs/ops/GIT_CONFIG_FIX.md](../ops/GIT_CONFIG_FIX.md)** | Git configuration guidance |
| **[docs/ops/DEVELOPER_CONNECT_FIX.md](../ops/DEVELOPER_CONNECT_FIX.md)** | Developer auth and connectivity notes |
| **[docs/ops/STOP_AUTO_UPDATES_CHECKLIST.md](../ops/STOP_AUTO_UPDATES_CHECKLIST.md)** | Disabling automation checklist |

## Deployment & Hosting

| Document | Purpose |
|----------|---------|
| **[docs/RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md)** | Railway deployment guide |
| **[docs/REPORTS_HOSTING.md](../REPORTS_HOSTING.md)** | Reports hosting configuration |
| **[docs/RECOVERY_MODE.md](../RECOVERY_MODE.md)** | Recovery procedures |

## Archived Documentation

**Location:** `docs/legacy/`

These documents are preserved for historical reference but are not actively maintained:

- `DELIVERY_SUMMARY.md` — Legacy delivery summary
- `FINAL_SUMMARY.md` — Final summary snapshot
- `IMPLEMENTATION_COMPLETE.md` — Implementation completion notes
- `INTEGRATION_COMPLETION_SUMMARY.md` — Integration completion summary
- `README_2.md`, `README_3.md`, `README_4.md` — Historical README versions
- `SETUP_2.md` — Legacy setup guide
- `SUMMARY-2025-12-01.md` — Point-in-time summary
- `pr_closure_recommendations.md` — PR cleanup recommendations

## Removed/Consolidated Documents

The following documents have been consolidated into other files:

- `TODO.md` → Merged into **[ROADMAP.md](../../ROADMAP.md)**
- `FUTURE_UPDATES.md` → Merged into **[ROADMAP.md](../../ROADMAP.md)**
- `ARCHIVE.md` → Information preserved in this index
- `SETUP.md` → Content covered in **[INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md)**

## Quick Navigation

**Need to...** | **See this document**
---|---
Get started quickly | [QUICKSTART.md](../../QUICKSTART.md)
Integrate with my tracker | [INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md)
Understand the API | [examples/README.md](../../examples/README.md)
See future plans | [ROADMAP.md](../../ROADMAP.md)
Deploy to production | [docs/ops/HANDOFF.md](../ops/HANDOFF.md)
Understand architecture | [docs/design/IMPROVEMENTS.md](../design/IMPROVEMENTS.md)
Fix a deployment issue | [docs/RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md)

## Contributing

When adding new documentation:
1. Add it to the appropriate section above
2. Keep the Quick Navigation table updated
3. If replacing a document, list it in "Removed/Consolidated Documents"
4. Archive outdated docs to `docs/legacy/` instead of deleting
