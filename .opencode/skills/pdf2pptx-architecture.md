# PDF-to-PPTX — Consolidated Skill Notice

> **This file is now a pointer.** The canonical, actively-loaded skill is
> `.opencode/skills/pdf2pptx-architecture/SKILL.md` (the MCP-based conversion workflow),
> and the enterprise self-hosted platform design is retained at
> `.opencode/skills/pdf2pptx-architecture/reference/enterprise-platform.md`.

## What lives where

| File | Purpose | Auto-loaded? |
|------|---------|--------------|
| `.opencode/skills/pdf2pptx-architecture/SKILL.md` | Active MCP conversion skill (pdf-tools + powerpoint) | ✅ yes |
| `.opencode/skills/pdf2pptx-architecture/reference/enterprise-platform.md` | Enterprise microservice reference (FastAPI/Redis/AWS/Docker) | ❌ no (reference only) |

## Behavior

- opencode discovers and loads `SKILL.md` automatically (frontmatter `name` + `description`).
- The `reference/` subfolder is intentionally **not** auto-loaded — it's kept available for
  humans building a self-hosted version but does not bloat the active skill.
