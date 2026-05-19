import React from 'react'

export default function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Orb 1 - top left */}
      <div
        className="orb-1 absolute rounded-full opacity-20"
        style={{
          width: '500px',
          height: '500px',
          top: '-100px',
          left: '-150px',
          background: 'radial-gradient(circle, #7C3AED 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      {/* Orb 2 - top right */}
      <div
        className="orb-2 absolute rounded-full opacity-15"
        style={{
          width: '400px',
          height: '400px',
          top: '100px',
          right: '-100px',
          background: 'radial-gradient(circle, #2563EB 0%, transparent 70%)',
          filter: 'blur(50px)',
        }}
      />
      {/* Orb 3 - bottom center */}
      <div
        className="orb-3 absolute rounded-full opacity-10"
        style={{
          width: '600px',
          height: '600px',
          bottom: '-200px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'radial-gradient(circle, #7C3AED 0%, #2563EB 50%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      {/* Grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(124,58,237,0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(124,58,237,0.5) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />
    </div>
  )
}
