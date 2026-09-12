import { useEffect, useState } from 'react'

export default function AnimatedCursor() {
  const [position, setPosition] = useState({ x: -100, y: -100 })
  const [active, setActive] = useState(false)

  useEffect(() => {
    const move = (event) => setPosition({ x: event.clientX, y: event.clientY })
    const enter = () => setActive(true)
    const leave = () => setActive(false)
    const targets = document.querySelectorAll('a, button')

    window.addEventListener('pointermove', move)
    targets.forEach((element) => {
      element.addEventListener('pointerenter', enter)
      element.addEventListener('pointerleave', leave)
    })

    return () => {
      window.removeEventListener('pointermove', move)
      targets.forEach((element) => {
        element.removeEventListener('pointerenter', enter)
        element.removeEventListener('pointerleave', leave)
      })
    }
  }, [])

  return (
    <div
      className={`cursor-orb ${active ? 'cursor-active' : ''}`}
      style={{ transform: `translate3d(${position.x}px, ${position.y}px, 0)` }}
      aria-hidden="true"
    />
  )
}
