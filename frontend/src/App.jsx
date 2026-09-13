import React, { useEffect, useMemo, useRef, useState } from "react";
import { Download, Film, Gauge, History, Link2, Loader2, Play, Sparkles, Upload, Wand2, X } from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const defaultOptions = {
  num_clips: 5,
  clip_duration: 30,
  captions: true,
  model: "base",
  smart_crop: true,
  generate_metadata: true,
};

function App() {
  const [mode, setMode] = useState("youtube");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [options, setOptions] = useState(defaultOptions);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem("clipforge-history") || "[]"); } catch { return []; }
  });
  const fileInput = useRef(null);

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!job?.job_id || job.status === "completed" || job.status === "failed") return;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${API}/jobs/${job.job_id}`);
        const next = await response.json();
        setJob(next);
        if (next.status === "completed" && next.result) {
          const item = {
            job_id: next.job_id,
            created: new Date().toISOString(),
            clips: next.result.number_of_clips,
            source_duration: next.result.source_duration,
            source_resolution: next.result.source_resolution,
          };
          setHistory(old => {
            const updated = [item, ...old.filter(x => x.job_id !== item.job_id)].slice(0, 10);
            localStorage.setItem("clipforge-history", JSON.stringify(updated));
            return updated;
          });
        }
      } catch (e) { /* keep polling */ }
    }, 1800);
    return () => clearInterval(timer);
  }, [job]);

  const isBusy = job && ["queued", "processing"].includes(job.status);
  const progress = Math.max(0, Math.min(100, Number(job?.progress || 0)));
  const result = job?.result;

  const update = (key, value) => setOptions(old => ({ ...old, [key]: value }));

  const validYouTube = useMemo(() => /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i.test(url.trim()), [url]);

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
        Object.entries(options).forEach(([key, value]) => data.append(key, String(value)));
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
    setJob(null); setError(""); setUrl(""); setFile(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function copyMetadata(clip) {
    const metadata = clip.metadata || {};
    const text = `${metadata.title || clip.title}\n\n${metadata.description || clip.text || ""}\n\n${(metadata.hashtags || []).join(" ")}`;
    await navigator.clipboard.writeText(text);
  }

  return (
    <main className="app-shell">
      <nav className="topbar">
        <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><span>ClipForge<span className="accent">AI</span></span></div>
        <div className="local-pill"><span className="pulse" /> Local AI · No API key</div>
      </nav>

      <section className="hero">
        <div className="eyebrow"><Wand2 size={15} /> AI SHORT-FORM STUDIO</div>
        <h1>Turn long videos into <em>high-retention Shorts.</em></h1>
        <p>Paste a YouTube link or upload a video. ClipForge transcribes it locally, scores the strongest moments, crops them to 9:16 and creates ready-to-post clips.</p>
      </section>

      {!result && !isBusy && (
        <section className="workspace">
          <div className="input-card">
            <div className="tabs">
              <button className={mode === "youtube" ? "active" : ""} onClick={() => setMode("youtube")}><Link2 size={17} /> YouTube link</button>
              <button className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")}><Upload size={17} /> Upload video</button>
            </div>

            {mode === "youtube" ? (
              <form onSubmit={startProcessing}>
                <label className="label">YouTube URL</label>
                <div className="url-row"><Link2 size={19} /><input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." /></div>
                <p className="hint">Public YouTube videos supported. Downloads are processed on your machine.</p>
              </form>
            ) : (
              <div className="dropzone" onClick={() => fileInput.current?.click()}>
                <input ref={fileInput} type="file" accept="video/*,.mkv,.webm" hidden onChange={e => setFile(e.target.files?.[0] || null)} />
                <div className="upload-icon"><Upload size={24} /></div>
                <strong>{file ? file.name : "Choose a video"}</strong>
                <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : "MP4, MOV, MKV, WebM or M4V · up to 2 GB"}</span>
              </div>
            )}

            <div className="divider" />
            <div className="options-head"><span>AI generation settings</span><span className="pro-label">LOCAL</span></div>
            <div className="options-grid">
              <div><label>Number of clips</label><select value={options.num_clips} onChange={e => update("num_clips", Number(e.target.value))}>{[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n}>{n}</option>)}</select></div>
              <div><label>Clip length</label><select value={options.clip_duration} onChange={e => update("clip_duration", Number(e.target.value))}>{[15,30,45,60].map(n => <option key={n} value={n}>{n} seconds</option>)}</select></div>
              <div><label>Whisper model</label><select value={options.model} onChange={e => update("model", e.target.value)}><option value="tiny">Tiny · fastest</option><option value="base">Base · balanced</option><option value="small">Small · accurate</option><option value="medium">Medium · best local</option></select></div>
            </div>
            <div className="toggles">
              <label><input type="checkbox" checked={options.captions} onChange={e => update("captions", e.target.checked)} /><span>Auto captions</span></label>
              <label><input type="checkbox" checked={options.smart_crop} onChange={e => update("smart_crop", e.target.checked)} /><span>Smart 9:16 crop</span></label>
              <label><input type="checkbox" checked={options.generate_metadata} onChange={e => update("generate_metadata", e.target.checked)} /><span>Titles + hashtags</span></label>
            </div>
            {error && <div className="error"><X size={17} /> {error}</div>}
            <button className="generate" onClick={startProcessing} disabled={isBusy}><Play size={18} fill="currentColor" /> Generate best clips</button>
          </div>

          <aside className="feature-card">
            <div className="feature-title"><Gauge size={18} /> What the AI does</div>
            {[["01","Transcribe","Local Whisper analyzes speech and timing."],["02","Find hooks","Ranks moments using hooks, context and language signals."],["03","Format","Creates vertical 1080×1920 MP4 clips."],["04","Publish","Adds captions, thumbnails, titles and hashtags."]].map(([n,t,d]) => <div className="feature" key={n}><b>{n}</b><div><strong>{t}</strong><p>{d}</p></div></div>)}
            <div className="health">{health ? <><span className={health.ffmpeg && health.whisper && health.yt_dlp ? "ok" : "warn"}>●</span> Backend {health.ffmpeg && health.yt_dlp ? "ready" : "needs setup"}</> : <><span className="warn">●</span> Backend not connected</>}</div>
          </aside>
        </section>
      )}

      {isBusy && (
        <section className="processing-card">
          <div className="spinner"><Loader2 size={30} /></div>
          <div className="processing-copy"><div className="eyebrow">PROCESSING</div><h2>{job.message || "Analyzing your video…"}</h2><p>ClipForge is working locally. You can leave this tab open while the video is processed.</p><div className="progress-track"><span style={{ width: `${progress}%` }} /></div><div className="progress-meta"><span>{progress}%</span><span>Whisper → highlights → rendering</span></div></div>
        </section>
      )}

      {job?.status === "failed" && (
        <section className="failed-card"><X size={25} /><div><h2>Processing failed</h2><p>{job.error || job.message}</p><button onClick={reset}>Try again</button></div></section>
      )}

      {result && (
        <section className="results">
          <div className="results-head"><div><div className="eyebrow"><Sparkles size={15} /> PROCESS COMPLETE</div><h2>{result.number_of_clips} Shorts generated</h2><p>{result.language !== "unknown" ? `Transcript analyzed in ${result.language}.` : "Video analyzed with local AI."} · {result.source_resolution}</p></div><div className="result-actions"><a className="secondary" href={`${API}${result.download_all_url}`}><Download size={17} /> Download all</a><button className="primary" onClick={reset}>Process another</button></div></div>
          {result.warning && <div className="warning">{result.warning}</div>}
          <div className="clip-grid">{result.clips.map(clip => <article className="clip-card" key={clip.clip_number}><div className="thumb"><img src={clip.thumbnail_url ? `${API}${clip.thumbnail_url}` : ""} alt="" /><div className="score">{Math.round(clip.score)}/100</div><div className="clip-label">AI SHORT #{clip.clip_number}</div></div><div className="clip-body"><h3>{clip.title}</h3><div className="time"><span>{formatTime(clip.start)} – {formatTime(clip.end)}</span><span>{Math.round(clip.duration)}s</span></div><p>{clip.text || "AI-selected highlight"}</p><div className="card-actions"><a href={`${API}${clip.download_url}`} download><Download size={16} /> MP4</a><button onClick={() => copyMetadata(clip)}>Copy metadata</button></div></div></article>)}</div>
          {result.transcript && <details className="transcript"><summary><History size={17} /> View analyzed transcript</summary><p>{result.transcript}</p></details>}
        </section>
      )}

      {!result && history.length > 0 && !isBusy && <section className="history"><div className="section-title"><History size={18} /> Recent jobs</div>{history.slice(0,5).map(item => <div className="history-row" key={item.job_id}><Film size={17} /><span>{new Date(item.created).toLocaleString()}</span><b>{item.clips} clips</b><span>{item.source_duration}s</span></div>)}</section>}

      <footer>ClipForge AI · Local-first creator toolkit · Your videos stay on your machine</footer>
    </main>
  );
}

function formatTime(value) {
  const total = Math.max(0, Math.floor(Number(value) || 0));
  const m = Math.floor(total / 60); const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default App;
