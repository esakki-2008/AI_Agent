import { useState } from 'react'

const projects = [
  { id: '01', title: 'NOVA HOUSE', type: 'Hospitality', year: '2026', className: 'project-nova' },
  { id: '02', title: 'MONO FORM', type: 'Architecture', year: '2026', className: 'project-mono' },
  { id: '03', title: 'ORBITAL', type: 'Technology', year: '2025', className: 'project-orbital' },
  { id: '04', title: 'SORA', type: 'Lifestyle', year: '2025', className: 'project-sora' },
]

export default function ProjectShowcase() {
  const [active, setActive] = useState('01')

  return (
    <section className="projects-section">
      <div className="projects-heading">
        <p className="section-index">01 — SELECTED WORK</p>
        <div className="project-counter"><span>{active}</span> / 04</div>
      </div>

      <div className="projects-layout">
        <div className="project-list">
          {projects.map((project) => (
            <button className={`project-row ${active === project.id ? 'is-active' : ''}`} key={project.id} onMouseEnter={() => setActive(project.id)} onFocus={() => setActive(project.id)} type="button">
              <span>{project.id}</span>
              <strong>{project.title}</strong>
              <small>{project.type}</small>
              <i>↗</i>
            </button>
          ))}
        </div>

        <div className="project-visual" aria-label="Selected project preview">
          {projects.map((project) => (
            <div key={project.id} className={`project-art ${project.className} ${active === project.id ? 'is-visible' : ''}`}>
              <div className="art-shape shape-a" />
              <div className="art-shape shape-b" />
              <div className="art-label">{project.title}</div>
              <div className="art-year">{project.year}</div>
            </div>
          ))}
          <div className="visual-caption">Move across a project <span>↗</span></div>
        </div>
      </div>
    </section>
  )
}
