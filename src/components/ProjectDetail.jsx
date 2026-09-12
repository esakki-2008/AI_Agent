import { useEffect } from 'react'

export default function ProjectDetail({ project, onClose }) {
  useEffect(() => { const onKey = e => e.key === 'Escape' && onClose(); document.body.style.overflow='hidden'; window.addEventListener('keydown', onKey); return () => { document.body.style.overflow=''; window.removeEventListener('keydown', onKey) } }, [onClose])
  return <div className="project-detail" role="dialog" aria-modal="true"><button className="detail-close" onClick={onClose}>Close <span>×</span></button><div className="detail-image" style={project.image ? {backgroundImage:`url(${project.image})`} : {}}><div className="detail-fallback"><span>{project.type}</span><strong>{project.title}</strong></div><span className="detail-year">{project.year}</span></div><div className="detail-copy"><p className="section-index">SELECTED PROJECT · {project.year}</p><h2>{project.title}</h2><p>{project.description || 'A carefully crafted digital experience designed around clarity, movement and memorable interaction.'}</p><div><span>{project.type}</span><span>Digital experience</span></div></div></div>
}
