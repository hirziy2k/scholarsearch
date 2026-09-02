# Mendeley Patcher - Standalone Deployment

A self-contained executable for correcting Mendeley metadata in Microsoft Word documents.

## Quick Start (3 minutes)

### Step 1: Transfer to Target Laptop
Copy `mendeley-patcher.exe` + `references.bib` to the laptop with Word/Mendeley.

### Step 2: First-Time Setup
```
mendeley-patcher.exe setup
```
This opens your browser for OAuth authorization. Credentials are stored securely in Windows Credential Manager.

### Step 3: Run Full Pipeline
```
mendeley-patcher.exe full thesis.docx references.bib
```
This:
1. Extracts UUIDs from your .docx
2. Fetches metadata from Mendeley + Crossref APIs
3. Computes diffs
4. **Opens web browser automatically** for review and execution

### Step 4: Review & Execute in Browser
The web interface opens at `http://localhost:8585`:

1. **Review tab**: Check boxes for corrections to approve
2. **Execute tab**: Click "Execute Now" to apply patches
3. **Rollback tab**: One-click revert if anything goes wrong

**No terminal interaction required after Step 3.**

---

## Architecture

| Problem | Solution |
|---------|----------|
| Unsigned .exe blocked by Defender | Runs as Python script on target, no .exe needed |
| Excel corrupts UTF-8 in CSV | HTML dashboard with JavaScript |
| Browser can't write local files | Embedded localhost server handles all I/O |
| Context-switching CLI/browser | Single web interface for approve + execute |
| No rollback mechanism | Immutable snapshots before each PATCH |

## Commands

```
mendeley-patcher.exe setup                    # First-time OAuth setup
mendeley-patcher.exe serve                    # Launch web interface only
mendeley-patcher.exe full <docx> [bib]        # Run pipeline + web interface
mendeley-patcher.exe status                   # Show statistics
mendeley-patcher.exe clear                    # Clear stored credentials
```

## Files

```
mendeley-patcher.exe         # Standalone executable
references.bib               # Your correct APA references (user-provided)
output/
  snapshots/                 # Rollback snapshots (auto-created)
  patch_log.json             # Audit trail
patcher.db                   # SQLite database (created at runtime)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No valid access token" | Run `mendeley-patcher.exe setup` |
| Browser doesn't open | Copy `http://localhost:8585` into your browser |
| "401 Unauthorized" | Run `mendeley-patcher.exe auth` |
| Defender blocks .exe | Run as Python script instead: `python orchestrator.py serve` |
| Rollback needed | Click "Rollback" tab in web interface |
