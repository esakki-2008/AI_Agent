import { useEffect, useMemo, useState } from 'react'
import { Download, Film, Gauge, Globe2, Link2, LoaderCircle, Package, Play, Settings2, ShieldCheck, Sparkles, Upload, Youtube } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const defaults = { num_clips: 5, clip_duration: 30, captions: true, model: 'base', smart_crop: true, generate_metadata: true }

export default function App() {
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('youtube')
  const [options, setOptions] = useState(defaults)
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [jobId, setJobId] = useState(null)
  const [health, setHealth] = useState(null)
  const [drag, setDrag] = useState(false)

  const validYouTube = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)(\/|$)/i.test(url.trim())

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth(null))
  }, [])

  useEffect(() => {
    if (!jobId || status !== 'processing') return
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${API}/jobs/${jobId}`)
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || 'Could not read job status.')
        setProgress(data.progress ?? 0); setMessage(data.message || 'Working…')
        if (data.status === 'completed') { setResult(data.result); setProgress(100); setStatus('complete'); setJobId(null) }
        else if (data.status === 'failed') throw new Error(data.error || 'Processing failed.')
      } catch (e) { setError(e.message); setStatus('idle'); setJobId(null) }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobId, status])

  const totalWords = useMemo(() => result?.transcript?.trim().split(/\s+/).filter(Boolean).length || 0, [result])

  function chooseFile(next) { const picked = next?.[0]; if (picked) { setFile(picked); setError('') } }
  function setOption(key, value) { setOptions(prev => ({ ...prev, [key]: value })) }

  async function generate() {
    setError(''); setResult(null)
    if (mode === 'youtube' && !validYouTube) { setError('Enter a valid YouTube URL.'); return }
    if (mode === 'upload' && !file) { setError('Choose a video first.'); return }
    try {
      setStatus('processing'); setProgress(5); setMessage(mode === 'youtube' ? 'Starting secure YouTube download…' : 'Uploading video…')
      let response
      if (mode === 'youtube') {
        response = await fetch(`${API}/process-url`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: url.trim(), options }) })
      } else {
        const form = new FormData(); form.append('file', file)
        Object.entries(options).forEach(([key, value]) => form.append(key, String(value)))
        response = await fetch(`${API}/process`, { method: 'POST', body: form })
      }
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Generation failed.')
      setJobId(data.job_id)
    } catch (e) { setError(e.message); setStatus('idle'); setProgress(0) }
  }

  function reset() { setUrl(''); setFile(null); setResult(null); setStatus('idle'); setProgress(0); setMessage(''); setError(''); setJobId(null) }

  return <main>
    <nav>
      <div className="brand"><span className="brandmark"><Sparkles size={17}/></span>ClipForge<span>AI</span></div>
      <div className="nav-right"><div className="badge"><ShieldCheck size={14}/> Local AI · No API key</div><div className="health"><i className={health?.status === 'healthy' ? 'online' : ''}/>{health?.status === 'healthy' ? 'Engine ready' : 'Checking engine'}</div></div>
    </nav>

    <section className="hero">
      <p className="eyebrow">LONG-FORM → SHORT-FORM</p>
      <h1>Turn hours of video into <em>Shorts.</em></h1>
      <p className="sub">Paste a YouTube link or upload a video. ClipForge analyzes speech locally, scores hooks and context, finds the strongest moments, formats them vertically, adds captions and prepares publishing metadata.</p>

      {status === 'idle' && !result && <div className="panel">
        <div className="tabs"><button className={mode === 'youtube' ? 'active' : ''} onClick={() => setMode('youtube')}><Youtube size={17}/> YouTube URL</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><Upload size={17}/> Upload video</button></div>
        {mode === 'youtube' ? <div className="urlbox"><Link2 size={20}/><input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=…" onKeyDown={e => e.key === 'Enter' && generate()}/>{validYouTube && <span className="valid">✓</span>}</div> : <label className={`drop ${drag ? 'drag' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); chooseFile(e.dataTransfer.files) }}><Upload size={30}/><strong>{file ? file.name : 'Drop your video here or click to browse'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : 'MP4, MOV, MKV, AVI, WebM · Max 2 GB'}</span><input hidden type="file" accept="video/*" onChange={e => chooseFile(e.target.files)}/></label>}

        <div className="options-title"><Settings2 size={16}/> Advanced output settings</div>
        <div className="options">
          <label>Shorts<select value={options.num_clips} onChange={e => setOption('num_clips', Number(e.target.value))}>{[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
          <label>Length<select value={options.clip_duration} onChange={e => setOption('clip_duration', Number(e.target.value))}>{[15,20,30,45,60].map(n => <option key={n} value={n}>{n} sec</option>)}</select></label>
          <label>Whisper model<select value={options.model} onChange={e => setOption('model', e.target.value)}><option value="tiny">Tiny · fastest</option><option value="base">Base · balanced</option><option value="small">Small · better</option><option value="medium">Medium · best local</option></select></label>
        </div>
        <div className="toggles">
          <label><input type="checkbox" checked={options.captions} onChange={e => setOption('captions', e.target.checked)}/> Dynamic captions</label>
          <label><input type="checkbox" checked={options.smart_crop} onChange={e => setOption('smart_crop', e.target.checked)}/> Smart vertical crop</label>
          <label><input type="checkbox" checked={options.generate_metadata} onChange={e => setOption('generate_metadata', e.target.checked)}/> Titles + hashtags</label>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="primary" onClick={generate}><Sparkles size={18}/> Generate Best Shorts</button>
        <p className="fineprint">Best results come from videos with clear speech. Use videos you own or have permission to download and transform.</p>
      </div>}

      {status === 'processing' && <div className="processing"><div className="process-icon"><LoaderCircle className="spin" size={38}/></div><p className="eyebrow">AI WORKFLOW</p><h2>Creating your Shorts…</h2><p>{message || 'Downloading, transcribing, ranking and rendering.'}</p><div className="bar"><i style={{width: `${progress}%`}}/></div><div className="progress-row"><strong>{progress}%</strong><span>Local processing · No API key</span></div><div className="steps"><span className={progress >= 30 ? 'done' : ''}>Download</span><span className={progress >= 48 ? 'done' : ''}>Whisper</span><span className={progress >= 62 ? 'done' : ''}>Rank</span><span className={progress >= 70 ? 'done' : ''}>Render</span><span className={progress >= 100 ? 'done' : ''}>Export</span></div></div>}
    </section>

    {result && <section className="results">
      <div className="result-head"><div><p className="eyebrow">PROCESS COMPLETE</p><h2>{result.number_of_clips} Shorts generated</h2><p>{result.warning || 'AI ranked the strongest moments from your source video.'}</p></div><div className="result-actions"><a className="secondary" href={`${API}${result.download_all_url}`}><Package size={17}/> Download all</a><button className="secondary" onClick={reset}>Process another</button></div></div>
      <div className="stats"><div><Gauge/><b>{result.source_duration ? Math.round(result.source_duration / 60) + ' min' : '—'}</b><span>Source length</span></div><div><Film/><b>9:16</b><span>1080 × 1920</span></div><div><Globe2/><b>{result.language || 'auto'}</b><span>Detected language</span></div><div><Sparkles/><b>{totalWords}</b><span>Transcript words</span></div></div>
      <div className="grid">{result.clips.map(c => <article className="card" key={c.clip_number}>
        <div className="preview"><video controls preload="metadata" poster={c.thumbnail_url ? `${API}${c.thumbnail_url}` : undefined} src={`${API}${c.download_url}`}/><div className="score">🔥 {c.score}/100</div></div>
        <div className="card-body"><div className="card-top"><span>SHORT #{c.clip_number}</span><small>{formatTime(c.start)} → {formatTime(c.start + c.duration)}</small></div><h3>{c.title}</h3><p>{c.text || 'AI-selected highlight from the source video.'}</p>
          {c.metadata?.hashtags?.length > 0 && <div className="hashtags">{c.metadata.hashtags.slice(0,5).map(tag => <span key={tag}>{tag}</span>)}</div>}
          <div className="meta">Score {c.score}/100 · {Math.round(c.duration)} sec</div><div className="card-actions"><a className="download" href={`${API}${c.download_url}`} download><Download size={17}/> Download MP4</a>{c.thumbnail_url && <a className="thumb" href={`${API}${c.thumbnail_url}`} download>Thumbnail</a>}</div>
        </div>
      </article>)}</div>
      {result.transcript && <details className="transcript"><summary>View full transcript</summary><p>{result.transcript}</p></details>}
    </section>}

    <section className="features"><div><Sparkles/><b>AI highlight engine</b><span>Hooks, keywords, questions and context</span></div><div><Film/><b>Creator-ready format</b><span>9:16 · 1080 × 1920 · H.264/AAC</span></div><div><Play/><b>Captioned playback</b><span>Timed Whisper captions burned into video</span></div><div><Package/><b>Batch export</b><span>Download every Short in one ZIP</span></div></section>
    <footer>ClipForge AI · Local processing · No API key · v3.0</footer>
  </main>
}

function formatTime(seconds) { const total = Math.max(0, Math.floor(seconds)); const h = Math.floor(total / 3600); const m = Math.floor((total % 3600) / 60); const s = total % 60; return h ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}` }
