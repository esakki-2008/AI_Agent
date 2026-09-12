import { useEffect, useMemo, useState } from 'react'

const seedProjects = [
  { id: 1, title: 'NOVA HOUSE', type: 'Hospitality', year: '2026', status: 'Published' },
  { id: 2, title: 'MONO FORM', type: 'Architecture', year: '2026', status: 'Published' },
  { id: 3, title: 'ORBITAL', type: 'Technology', year: '2025', status: 'Draft' },
  { id: 4, title: 'SORA', type: 'Lifestyle', year: '2025', status: 'Published' },
]
const seedServices = [
  { id: 1, title: 'Digital Strategy', text: 'Turn ambitious ideas into clear digital direction.', enabled: true },
  { id: 2, title: 'Brand Systems', text: 'Build a visual language people remember instantly.', enabled: true },
  { id: 3, title: 'Interactive Web', text: 'Create responsive experiences that react to people.', enabled: true },
]
const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) || fallback } catch { return fallback } }

export default function AdminPanel({ onExit }) {
  const [loggedIn, setLoggedIn] = useState(() => sessionStorage.getItem('atelier-admin') === '1')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [active, setActive] = useState('Overview')
  const [projects, setProjects] = useState(() => read('atelier-projects', seedProjects))
  const [services, setServices] = useState(() => read('atelier-services', seedServices))
  const [inquiries, setInquiries] = useState(() => read('atelier-inquiries', []))
  const [notice, setNotice] = useState('')
  useEffect(() => localStorage.setItem('atelier-projects', JSON.stringify(projects)), [projects])
  useEffect(() => localStorage.setItem('atelier-services', JSON.stringify(services)), [services])
  useEffect(() => localStorage.setItem('atelier-inquiries', JSON.stringify(inquiries)), [inquiries])
  const published = useMemo(() => projects.filter(p => p.status === 'Published').length, [projects])
  const toast = message => { setNotice(message); setTimeout(() => setNotice(''), 1800) }
  const login = e => { e.preventDefault(); sessionStorage.setItem('atelier-admin', '1'); setLoggedIn(true) }
  const logout = () => { sessionStorage.removeItem('atelier-admin'); setLoggedIn(false) }
  const addProject = () => { setProjects(items => [...items, { id: Date.now(), title: `NEW PROJECT ${items.length + 1}`, type: 'New category', year: '2026', status: 'Draft' }]); toast('Project created') }
  const toggleProject = i => { setProjects(items => items.map((p,n) => n === i ? { ...p, status: p.status === 'Published' ? 'Draft' : 'Published' } : p)); toast('Project status updated') }
  const deleteProject = i => { setProjects(items => items.filter((_,n) => n !== i)); toast('Project deleted') }
  const toggleService = i => { setServices(items => items.map((s,n) => n === i ? { ...s, enabled: !s.enabled } : s)); toast('Service visibility updated') }

  if (!loggedIn) return <main className="admin-login"><button className="back-site" onClick={onExit}>← Back to website</button><div className="login-card"><span className="brand-mark">A</span><p className="section-index">ADMIN ACCESS</p><h1>Control<br /><em>everything.</em></h1><form onSubmit={login}><label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@atelier.studio" required /></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required /></label><button className="login-btn">Enter dashboard ↗</button></form><small>Demo mode · Any valid email and password</small></div></main>

  return <main className="admin-shell"><aside className="admin-sidebar"><button className="admin-logo" onClick={onExit}>A<span>.</span></button><p className="admin-label">CONTROL PANEL</p><nav>{['Overview','Projects','Services','Inquiries','Settings'].map(item => <button key={item} className={active === item ? 'admin-active' : ''} onClick={() => setActive(item)}>{item}<span>↗</span></button>)}</nav><button className="exit-admin" onClick={onExit}>↗ View website</button></aside><section className="admin-content"><header className="admin-top"><div><p className="section-index">ADMIN · 2026</p><h2>{active === 'Overview' ? 'Good to see you.' : active}</h2></div><div className="admin-user"><span className="status-dot" /> Admin <button onClick={logout}>Log out</button></div></header>
    {active === 'Overview' || active === 'Projects' ? <><div className="admin-grid"><article className="admin-stat"><span>Published projects</span><strong>{published}</strong><i>↗</i></article><article className="admin-stat"><span>Total projects</span><strong>{projects.length}</strong><i>◌</i></article><article className="admin-stat"><span>Inquiries</span><strong>{inquiries.length}</strong><i>✦</i></article></div><div className="admin-table-head"><div><p className="section-index">CONTENT MANAGER</p><h3>{active === 'Projects' ? 'All projects' : 'Recent projects'}</h3></div><button className="add-project" onClick={addProject}>+ Add project</button></div><ProjectTable projects={projects} toggle={toggleProject} remove={deleteProject} /></> : null}
    {active === 'Services' && <div className="admin-list"><p className="section-index">SERVICE MANAGER</p>{services.map((s,i) => <div className="admin-service" key={s.id}><div><strong>{s.title}</strong><p>{s.text}</p></div><button className={s.enabled ? 'published' : 'draft'} onClick={() => toggleService(i)}>{s.enabled ? 'VISIBLE' : 'HIDDEN'}</button></div>)}</div>}
    {active === 'Inquiries' && <div className="admin-list"><p className="section-index">CONTACT</p><h3>Client inquiries</h3>{inquiries.length === 0 ? <div className="empty-state">No inquiries yet. Contact form submissions will appear here.</div> : inquiries.map((item,i) => <div className="inquiry" key={i}><strong>{item.name}</strong><span>{item.email}</span><p>{item.message}</p></div>)}</div>}
    {active === 'Settings' && <div className="admin-list"><p className="section-index">SITE SETTINGS</p><div className="settings-card"><h3>Demo configuration</h3><p>Authentication · Session based</p><p>Content storage · Browser localStorage</p><p>Public site · Dynamic project content</p><span>Backend-ready client demo.</span></div></div>}
    {notice && <div className="admin-toast">✓ {notice}</div>}</section></main>
}
function ProjectTable({ projects, toggle, remove }) { return <div className="admin-table"><div className="table-row table-head"><span>PROJECT</span><span>CATEGORY</span><span>STATUS</span><span>ACTION</span></div>{projects.map((p,i) => <div className="table-row" key={p.id}><strong>{p.title}</strong><span>{p.type}</span><button className={p.status === 'Published' ? 'published' : 'draft'} onClick={() => toggle(i)}>{p.status}</button><button className="delete-btn" onClick={() => remove(i)}>DELETE</button></div>)}</div> }
