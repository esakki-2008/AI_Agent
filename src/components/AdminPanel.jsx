import { useState } from 'react'

const defaultProjects = [
  { title: 'NOVA HOUSE', type: 'Hospitality', status: 'Published' },
  { title: 'MONO FORM', type: 'Architecture', status: 'Published' },
  { title: 'ORBITAL', type: 'Technology', status: 'Draft' },
]

export default function AdminPanel({ onExit }) {
  const [loggedIn, setLoggedIn] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [projects, setProjects] = useState(() => {
    try { return JSON.parse(localStorage.getItem('atelier-projects')) || defaultProjects } catch { return defaultProjects }
  })
  const [notice, setNotice] = useState('')

  function login(event) { event.preventDefault(); if (email && password) setLoggedIn(true) }
  function addProject() {
    const next = { title: `NEW PROJECT ${projects.length + 1}`, type: 'New category', status: 'Draft' }
    const updated = [...projects, next]
    setProjects(updated); localStorage.setItem('atelier-projects', JSON.stringify(updated))
    setNotice('New project added locally'); setTimeout(() => setNotice(''), 1800)
  }

  if (!loggedIn) return <main className="admin-login"><button className="back-site" onClick={onExit}>← Back to website</button><div className="login-card"><span className="brand-mark">A</span><p className="section-index">ADMIN ACCESS</p><h1>Control<br /><em>everything.</em></h1><form onSubmit={login}><label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@atelier.studio" required /></label><label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required /></label><button className="login-btn">Enter dashboard ↗</button></form><small>Demo mode · Any valid email and password</small></div></main>

  return <main className="admin-shell"><aside className="admin-sidebar"><a className="brand" href="#admin"><span className="brand-mark">A</span><span>ATELIER<span className="brand-dot">.</span></span></a><p className="admin-label">CONTROL PANEL</p><nav><a className="admin-active" href="#admin">Overview</a><a href="#admin-projects">Projects</a><a href="#admin-services">Services</a><a href="#admin-settings">Settings</a></nav><button className="exit-admin" onClick={onExit}>↗ View website</button></aside><section className="admin-content"><header className="admin-top"><div><p className="section-index">ADMIN · 2026</p><h2>Good to see you.</h2></div><div className="admin-user"><span className="status-dot" /> Admin <button onClick={() => setLoggedIn(false)}>Log out</button></div></header><div className="admin-grid"><article className="admin-stat"><span>Published projects</span><strong>{projects.filter((p) => p.status === 'Published').length}</strong><i>↗</i></article><article className="admin-stat"><span>Total projects</span><strong>{projects.length}</strong><i>◌</i></article><article className="admin-stat"><span>Site status</span><strong className="online">LIVE</strong><i>●</i></article></div><div className="admin-table-head"><div><p className="section-index">CONTENT</p><h3>Projects</h3></div><button className="add-project" onClick={addProject}>+ Add project</button></div><div className="admin-table"><div className="table-row table-head"><span>PROJECT</span><span>CATEGORY</span><span>STATUS</span><span>ACTION</span></div>{projects.map((project, index) => <div className="table-row" key={`${project.title}-${index}`}><strong>{project.title}</strong><span>{project.type}</span><span className={project.status === 'Published' ? 'published' : 'draft'}>{project.status}</span><button>EDIT ↗</button></div>)}</div>{notice && <div className="admin-toast">✓ {notice}</div>}</section></main>
}
