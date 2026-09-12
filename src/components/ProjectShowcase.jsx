import { useState } from 'react'

const seed = [
  { id: 1, title: 'NOVA HOUSE', type: 'Hospitality', year: '2026', status: 'Published' },
  { id: 2, title: 'MONO FORM', type: 'Architecture', year: '2026', status: 'Published' },
  { id: 3, title: 'ORBITAL', type: 'Technology', year: '2025', status: 'Draft' },
  { id: 4, title: 'SORA', type: 'Lifestyle', year: '2025', status: 'Published' },
]
const visualClasses = ['project-nova', 'project-mono', 'project-orbital', 'project-sora']

export default function ProjectShowcase() {
  const [projects] = useState(() => { try { return JSON.parse(localStorage.getItem('atelier-projects')) || seed } catch { return seed } })
  const visible = projects.filter(p => p.status === 'Published')
  const [active, setActive] = useState(0)
  if (!visible.length) return <section className="projects-section"><p className="section-index">01 — SELECTED WORK</p><div className="empty-public">Projects are being prepared. Check back soon.</div></section>
  const selected = visible[Math.min(active, visible.length - 1)]
  return <section className="projects-section"><div className="projects-heading"><p className="section-index">01 — SELECTED WORK</p><div className="project-counter"><span>{String(Math.min(active + 1, visible.length)).padStart(2,'0')}</span> / {String(visible.length).padStart(2,'0')}</div></div><div className="projects-layout"><div className="project-list">{visible.map((project,index) => <button className={`project-row ${index === active ? 'is-active' : ''}`} key={project.id || project.title} onMouseEnter={() => setActive(index)} onFocus={() => setActive(index)} type="button"><span>{String(index+1).padStart(2,'0')}</span><strong>{project.title}</strong><small>{project.type}</small><i>↗</i></button>)}</div><div className="project-visual"><div className={`project-art ${visualClasses[(selected.id || active) % visualClasses.length]} is-visible`}><div className="art-shape shape-a"/><div className="art-shape shape-b"/><div className="art-label">{selected.title}</div><div className="art-year">{selected.year || '2026'}</div></div><div className="visual-caption">Move across a project <span>↗</span></div></div></div></section>
}
