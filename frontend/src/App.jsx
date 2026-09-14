import React, { useEffect, useMemo, useRef, useState } from "react";
import { Download, Film, Gauge, History, Link2, Loader2, Play, Sparkles, Upload, Wand2, X, CheckCircle2 } from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const defaultOptions = {
  num_clips: 5,
  clip_duration: 30,
  captions: true,
  dynamic_captions: true,
  model: "base",
  smart_crop: true,
  generate_metadata: true,
  language: "auto",
  caption_style: "bold",
  crop_mode: "center",
  normalize_audio: true,
  quality: "high",
  hook_overlay: false,
  remove_filler: true,
};

const PRESETS = {
  "YouTube Shorts": { clip_duration: 30, caption_style: "bold", crop_mode: "center", quality: "high" },
  "Instagram Reels": { clip_duration: 30, caption_style: "bold", crop_mode: "blur", quality: "max" },
  TikTok: { clip_duration: 30, caption_style: "bold", crop_mode: "face", quality: "high" },
  LinkedIn: { clip_duration: 45, caption_style: "classic", crop_mode: "center", quality: "high" },
  Facebook: { clip_duration: 45, caption_style: "classic", crop_mode: "blur", quality: "high" },
  "X Video": { clip_duration: 30, caption_style: "minimal", crop_mode: "center", quality: "high" },
  "Podcast Clip": { clip_duration: 60, caption_style: "classic", crop_mode: "face", quality: "max" },
};

function App() {
  const [mode, setMode] = useState("youtube");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [options, setOptions] = useState(defaultOptions);
  const [preset, setPreset] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("clipforge-history") || "[]");
    } catch {
      return [];
    }
  });
  const fileInput = useRef(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!job?.job_id || ["completed", "failed"].includes(job.status)) return;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${API}/jobs/${job.job_id}`);
        const next = await response.json();
        setJob(next);
        if (next.status === "completed" && next.result) {
          const item = {
            job_id: next.job_id,
            created: new Date().toISOString(),
            clips: next.result.clips?.length || 0,
            source_duration: next.result.duration || 0,
            source_resolution: next.result.clips?.[0]?.resolution || "",
          };
          setHistory((old) => {
            const updated = [item, ...old.filter((x) => x.job_id !== item.job_id)].slice(0, 10);
            localStorage.setItem("clipforge-history", JSON.stringify(updated));
            return updated;
          });
        }
      } catch {
        // Keep polling on transient network errors.
      }
    }, 1800);
    return () => clearInterval(timer);
  }, [job]);

  const isBusy = job && ["queued", "processing", "downloading"].includes(job.status);
  const progress = Math.max(0, Math.min(100, Number(job?.progress || 0)));
  const result = job?.result;
  const update = (key, value) => setOptions((old) => ({ ...old, [key]: value }));
  const validYouTube = useMemo(
    () => /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i.test(url.trim()),
    [url]
  );

  function applyPreset(name) {
    setPreset(name);
    setOptions((old) => ({ ...old, ...PRESETS[name] }));
  }

  async function startProcessing(event) {
    event?.preventDefault();
    setError("");
    setJob(null);
    if (mode === "youtube" && !validYouTube) return setError("Paste a valid YouTube URL.");
    if (mode === "upload" && !file) return setError("Choose a video file first.");

    try {
      let response;
      if (mode === "youtube") {
        response = await fetch(`${API}/process-url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: url.trim(), options }),
        });
      } else {
        const data = new FormData();
        data.append("file", file);
        data.append("options", JSON.stringify(options));
        response = await fetch(`${API}/process`, { method: "POST", body: data });
      }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Could not start processing.");
      setJob(payload);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    }
  }

  function reset() {
    setJob(null);
    setError("");
    setUrl("");
    setFile(null);
    setPreset("");
    if (fileInput.current) fileInput.current.value = "";
  }

  async function copyMetadata(clip) {
    const m = clip.metadata || {};
    try {
      await navigator.clipboard.writeText(
        `${m.title || clip.title}\n\n${m.description || clip.text || ""}\n\n${(m.hashtags || []).join(" ")}`
      );
      setError("");
    } catch {
      setError("Clipboard permission was blocked. Copy the metadata manually from the result.");
    }
  }

  return (
    <main className="app-shell">
      <nav className="topbar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <span>ClipForge<span className="accent">AI</span></span>
        </div>
        <div className="local-pill"><span className="pulse" /> Local AI · No API key</div>
      </nav>

      <section className="hero">
        <div className="eyebrow"><Wand2 size={15} /> AI SHORT-FORM STUDIO</div>
        <h1>Turn long videos into <em>high-retention Shorts.</em></h1>
        <p>Transcribe locally, find strong moments, frame them for vertical video, add dynamic captions and export creator-ready assets.</p>
      </section>

      {!result && !isBusy && (
        <section className="workspace">
          <div className="input-card">
            <div className="tabs">
              <button type="button" className={mode === "youtube" ? "active" : ""} onClick={() => setMode("youtube")}><Link2 size={17} /> YouTube link</button>
              <button type="button" className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")}><Upload size={17} /> Upload video</button>
            </div>

            {mode === "youtube" ? (
              <form onSubmit={startProcessing}>
                <label className="label">YouTube URL</label>
                <div className="url-row"><Link2 size={19} /><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." /></div>
                <p className="hint">Public YouTube videos supported. Processing stays local after download.</p>
              </form>
            ) : (
              <div className="dropzone" onClick={() => fileInput.current?.click()}>
                <input ref={fileInput} type="file" accept="video/*,.mkv,.webm" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
                <div className="upload-icon"><Upload size={24} /></div>
                <strong>{file ? file.name : "Choose a video"}</strong>
                <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : "MP4, MOV, MKV, WebM or M4V · up to 2 GB"}</span>
              </div>
            )}

            <div className="divider" />
            <div className="options-head"><span>Platform presets</span><span className="pro-label">ONE-CLICK</span></div>
            <div className="tabs" style={{ marginBottom: 18, flexWrap: "wrap" }}>
              {Object.keys(PRESETS).map((name) => <button type="button" key={name} className={preset === name ? "active" : ""} onClick={() => applyPreset(name)}>{name}</button>)}
            </div>

            <div className="options-head"><span>Creator settings</span><span className="pro-label">LOCAL</span></div>
            <div className="options-grid">
              <div><label>Number of clips</label><select value={options.num_clips} onChange={(e) => update("num_clips", Number(e.target.value))}>{Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
              <div><label>Clip length</label><select value={options.clip_duration} onChange={(e) => update("clip_duration", Number(e.target.value))}>{[15, 30, 45, 60].map((n) => <option key={n} value={n}>{n} seconds</option>)}</select></div>
              <div><label>Whisper model</label><select value={options.model} onChange={(e) => update("model", e.target.value)}><option value="tiny">Tiny · fastest</option><option value="base">Base · balanced</option><option value="small">Small · accurate</option><option value="medium">Medium · best local</option></select></div>
              <div><label>Language</label><select value={options.language} onChange={(e) => update("language", e.target.value)}><option value="auto">Auto detect</option><option value="en">English</option><option value="hi">Hindi</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="ml">Malayalam</option><option value="kn">Kannada</option></select></div>
              <div><label>Caption style</label><select value={options.caption_style} onChange={(e) => { setPreset(""); update("caption_style", e.target.value); }}><option value="bold">Bold creator</option><option value="classic">Classic</option><option value="minimal">Minimal</option></select></div>
              <div><label>Vertical framing</label><select value={options.crop_mode} onChange={(e) => { setPreset(""); update("crop_mode", e.target.value); }}><option value="center">Smart center crop</option><option value="face">Face-aware speaker crop</option><option value="blur">Blurred background</option><option value="fit">Fit with padding</option></select></div>
              <div><label>Export quality</label><select value={options.quality} onChange={(e) => { setPreset(""); update("quality", e.target.value); }}><option value="standard">Standard · smaller</option><option value="high">High · recommended</option><option value="max">Max · larger</option></select></div>
            </div>

            <div className="toggles">
              <label><input type="checkbox" checked={options.captions} onChange={(e) => update("captions", e.target.checked)} /><span>Auto captions</span></label>
              <label><input type="checkbox" checked={options.dynamic_captions} disabled={!options.captions} onChange={(e) => update("dynamic_captions", e.target.checked)} /><span>Dynamic word captions</span></label>
              <label><input type="checkbox" checked={options.smart_crop} onChange={(e) => update("smart_crop", e.target.checked)} /><span>9:16 framing</span></label>
              <label><input type="checkbox" checked={options.normalize_audio} onChange={(e) => update("normalize_audio", e.target.checked)} /><span>Normalize audio</span></label>
              <label><input type="checkbox" checked={options.remove_filler} onChange={(e) => update("remove_filler", e.target.checked)} /><span>Reduce filler moments</span></label>
              <label><input type="checkbox" checked={options.generate_metadata} onChange={(e) => update("generate_metadata", e.target.checked)} /><span>Titles + hashtags</span></label>
              <label><input type="checkbox" checked={options.hook_overlay} onChange={(e) => update("hook_overlay", e.target.checked)} /><span>Hook text overlay</span></label>
            </div>

            <p className="hint">Face-aware framing uses local OpenCV detection. Dynamic captions use Whisper word timestamps. Hook overlay is reserved for the selected hook text.</p>
            {error && <div className="error"><X size={17} />{error}</div>}
            <button className="generate" onClick={startProcessing} disabled={isBusy}><Play size={18} fill="currentColor" /> Generate creator-ready Shorts</button>
          </div>

          <aside className="feature-card">
            <div className="feature-title"><Gauge size={18} /> Core engine</div>
            {[['01', 'Analyze', 'Local Whisper + transcript-aware hook scoring.'], ['02', 'Select', 'Diverse moments with filler-aware ranking.'], ['03', 'Frame', 'Face-aware 9:16, center crop, fit or blurred background.'], ['04', 'Polish', 'Dynamic captions, audio normalization and quality presets.'], ['05', 'Publish', 'Thumbnails, titles, descriptions, hashtags and ZIP export.']].map(([n, t, d]) => <div className="feature" key={n}><b>{n}</b><div><strong>{t}</strong><p>{d}</p></div></div>)}
            <div className="health">
              {health ? <><span className={health.ffmpeg && health.whisper && health.opencv ? "ok" : "warn"}>●</span> Backend {health.ffmpeg && health.whisper ? "ready" : "needs setup"}</> : <><span className="warn">●</span> Backend not connected</>}
            </div>
          </aside>
        </section>
      )}

      {isBusy && (
        <section className="processing-card">
          <div className="spinner"><Loader2 size={30} /></div>
          <div className="processing-copy"><div className="eyebrow">PROCESSING</div><h2>{job.message || "Analyzing your video…"}</h2><p>Downloading, transcribing, ranking, framing and rendering locally.</p><div className="progress-track"><span style={{ width: `${progress}%` }} /></div><div className="progress-meta"><span>{progress}%</span><span>Download → Whisper → Rank → Frame → Caption → Export</span></div></div>
        </section>
      )}

      {job?.status === "failed" && (
        <section className="failed-card"><X size={25} /><div><h2>Processing failed</h2><p>{job.error || job.message}</p><button onClick={reset}>Try again</button></div></section>
      )}

      {result && (
        <section className="results">
          <div className="results-head">
            <div>
              <div className="eyebrow"><CheckCircle2 size={15} /> PROCESS COMPLETE</div>
              <h2>{result.clips?.length || 0} Shorts generated</h2>
              <p>{result.output_format || "9:16"} · {result.output_resolution || "1080x1920"} · {result.transcript_language && result.transcript_language !== "unknown" ? `Transcript: ${result.transcript_language}.` : "Local AI analysis."}</p>
            </div>
            <div className="result-actions">
              <a className="secondary" href={`${API}${result.download_all_url}`}><Download size={17} /> Download all</a>
              {result.transcript && <a className="secondary" target="_blank" rel="noreferrer" href={`${API}/transcript/${result.job_id}`}><Download size={17} /> View transcript</a>}
              <button className="primary" onClick={reset}>Process another</button>
            </div>
          </div>

          {result.transcription_error && <div className="warning">Whisper transcription failed, so fallback highlight selection was used: {result.transcription_error}</div>}

          <div className="clip-grid">
            {(result.clips || []).map((clip) => (
              <article className="clip-card" key={clip.clip_number}>
                <div className="thumb">
                  <video controls preload="metadata" poster={clip.thumbnail_url ? `${API}${clip.thumbnail_url}` : undefined} src={`${API}${clip.download_url}`} />
                  <div className="score">{Math.round(clip.score)}/100</div>
                  <div className="clip-label">9:16 · SHORT #{clip.clip_number}</div>
                </div>
                <div className="clip-body">
                  <h3>{clip.title}</h3>
                  <div className="time"><span>{formatTime(clip.start)} – {formatTime(clip.end)}</span><span>{Math.round(clip.duration)}s</span></div>
                  <p>{clip.text || "AI-selected highlight"}</p>
                  <div className="card-actions">
                    <a href={`${API}${clip.download_url}`} download><Download size={16} /> MP4</a>
                    <a href={clip.thumbnail_url ? `${API}${clip.thumbnail_url}` : "#"} download><Download size={16} /> Thumbnail</a>
                    <button onClick={() => copyMetadata(clip)}>Copy metadata</button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {result.transcript && (
            <details className="transcript">
              <summary><History size={17} /> View analyzed transcript</summary>
              <p>{result.transcript}</p>
            </details>
          )}
        </section>
      )}

      {!result && history.length > 0 && !isBusy && (
        <section className="history">
          <div className="section-title"><History size={18} /> Recent jobs</div>
          {history.slice(0, 5).map((item) => <div className="history-row" key={item.job_id}><Film size={17} /><span>{new Date(item.created).toLocaleString()}</span><b>{item.clips} clips</b><span>{Math.round(item.source_duration || 0)}s</span></div>)}
        </section>
      )}

      <footer>ClipForge AI · Local-first creator toolkit · 9:16 export · No paid AI API required</footer>
    </main>
  );
}

function formatTime(value) {
  const total = Math.max(0, Math.floor(Number(value) || 0));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default App;
