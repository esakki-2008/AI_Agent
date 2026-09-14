# ClipForge AI — Installation Guide

## System requirements

- Windows 10/11, macOS, or Linux
- Python 3.10 or newer
- Node.js 18 or newer
- Internet access for YouTube downloads and the first Whisper model download
- At least 8 GB RAM recommended for the Base Whisper model
- More RAM and a capable CPU/GPU are recommended for larger Whisper models

## Windows quick setup

1. Extract the ClipForge AI package to a folder you can write to.
2. Double-click `setup_windows.bat`.
3. Wait for Python and Node dependencies to finish installing.
4. Double-click `start_windows.bat`.
5. The ClipForge AI dashboard opens at `http://localhost:5173`.

The backend runs locally at `http://127.0.0.1:8000`.

## Manual setup

### Backend

```cmd
cd /d "YOUR_CLIPFORGE_FOLDER\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend

Open a second terminal:

```cmd
cd /d "YOUR_CLIPFORGE_FOLDER\frontend"
npm install
npm run dev
```

Open the Vite URL shown by the terminal, normally `http://localhost:5173`.

## YouTube support

Deno is optional but recommended for current YouTube extraction. If Deno is installed and available on PATH, ClipForge automatically uses it with yt-dlp.

## First run

The first time a Whisper model is selected, Whisper may download that model into its local cache. This can take time and requires an internet connection. Later runs reuse the cached model.

## Troubleshooting

### Backend does not start

Run:

```cmd
cd /d "YOUR_CLIPFORGE_FOLDER\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend cannot connect

Make sure the backend is running on `http://127.0.0.1:8000` and that the browser is using the frontend URL from Vite.

### YouTube download fails

Install Deno and ensure `deno --version` works in the same terminal used to start the backend. YouTube extraction can also change when YouTube changes its player or access requirements.

### Processing is slow

Whisper and video encoding are CPU/GPU intensive. Start with the `tiny` or `base` model for faster testing.
