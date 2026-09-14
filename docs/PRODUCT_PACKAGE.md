# ClipForge AI — Commercial Package Guide

## Recommended customer archive

```text
ClipForge-AI-v1.0.0/
├── backend/
├── frontend/
├── docs/
│   ├── INSTALLATION.md
│   └── PRODUCT_PACKAGE.md
├── COMMERCIAL_LICENSE.md
├── PRODUCT_MANIFEST.md
├── CHANGELOG.md
├── README.md
├── setup_windows.bat
└── start_windows.bat
```

## Do not ship generated development data

Before creating a paid archive, exclude:

- `node_modules/`
- `frontend/dist/`
- `uploads/` contents
- `outputs/` contents
- `__pycache__/`
- `.env`
- local editor settings
- local logs

## Customer experience

1. Customer downloads and extracts the archive.
2. Customer reads `README.md` or `docs/INSTALLATION.md`.
3. Customer runs `setup_windows.bat` on Windows.
4. Customer runs `start_windows.bat`.
5. ClipForge opens locally in the browser.

## Before each paid release

- Run `npm run build` in `frontend/`.
- Run backend dependency installation and `python -m py_compile main.py`.
- Run a local video generation test.
- Run a YouTube URL test.
- Verify captions, downloads and ZIP export.
- Review the product manifest and changelog.
- Confirm the included license matches the sales-page terms.

## Distribution rule

The public GitHub repository should be treated as the project's public code repository. The paid package should be distributed through the selected storefront or delivery service rather than relying on the public repository as the customer download.
