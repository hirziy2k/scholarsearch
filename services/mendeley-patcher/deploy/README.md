# Mendeley Patcher - Deployment Package

## Quick Start

1. Copy `mendeley-patcher.exe` to any folder on your laptop
2. Double-click the .exe or run from Command Prompt
3. Follow the on-screen instructions

## First Time Setup

```bash
mendeley-patcher.exe setup
```

This will prompt you to enter your Mendeley API credentials (client_id: 24963).

## Authorization

```bash
mendeley-patcher.exe auth
```

This will:
1. Open your browser to Mendeley
2. You authorize the app
3. Browser redirects back automatically
4. Tokens are saved securely

## Run Full Pipeline

```bash
mendeley-patcher.exe full "C:\path\to\your\thesis.docx" "C:\path\to\references.bib"
```

**Important:** The `.bib` file is NOT bundled with the executable. You must provide both files at runtime. This means:
- Update your `.bib` file anytime without needing to recompile
- Only transfer the updated `.bib` file to your laptop (not the entire .exe)
- The executable remains static while your references evolve

This will:
1. Extract UUIDs from your Word document
2. Fetch metadata from Mendeley + Crossref
3. Compare with clean references
4. Launch web dashboard at http://localhost:8585

## Web Dashboard

After running the pipeline, open your browser to:
```
http://localhost:8585
```

Use the dashboard to:
- Review metadata corrections
- Approve changes
- Execute patches
- Rollback if needed

## Requirements

- Windows 10/11
- Microsoft Word installed
- Mendeley Reference Manager installed
- Internet connection

## Troubleshooting

If you get "Permission denied" errors:
- Close Microsoft Word
- Wait for OneDrive to finish syncing
- Try again

If the browser doesn't open:
- Manually go to http://localhost:8585
