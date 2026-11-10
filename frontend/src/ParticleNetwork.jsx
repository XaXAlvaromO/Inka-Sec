import { useEffect, useRef } from 'react';

// Decorative canvas: it never receives focus or intercepts dashboard controls.
export default function ParticleNetwork({ maxParticles = 72 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const host = canvas.parentElement;
    const context = canvas.getContext('2d');
    if (!context) return;

    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const pointer = { x: -1000, y: -1000 };
    let width = 0;
    let height = 0;
    let particles = [];
    let frame = 0;

    function resize() {
      const bounds = host.getBoundingClientRect();
      width = bounds.width;
      height = bounds.height;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      const count = Math.min(maxParticles, Math.max(24, Math.round(width * height / 9000)));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - .5) * .38,
        vy: (Math.random() - .5) * .38,
        radius: 1 + Math.random() * 1.4,
      }));
      draw();
    }

    function draw() {
      context.clearRect(0, 0, width, height);
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const distance = Math.hypot(a.x - b.x, a.y - b.y);
          if (distance > 130) continue;
          context.strokeStyle = `rgba(115, 190, 255, ${.24 * (1 - distance / 130)})`;
          context.lineWidth = 1;
          context.beginPath();
          context.moveTo(a.x, a.y);
          context.lineTo(b.x, b.y);
          context.stroke();
        }
        context.fillStyle = i % 5 === 0 ? '#b48cff' : '#6abaff';
        context.beginPath();
        context.arc(a.x, a.y, a.radius, 0, Math.PI * 2);
        context.fill();
      }
    }

    function animate() {
      for (const point of particles) {
        const dx = point.x - pointer.x;
        const dy = point.y - pointer.y;
        const distance = Math.hypot(dx, dy);
        if (distance > 0 && distance < 115) {
          const push = (1 - distance / 115) * 1.25;
          point.x += dx / distance * push;
          point.y += dy / distance * push;
        }
        point.x += point.vx;
        point.y += point.vy;
        if (point.x < 0 || point.x > width) point.vx *= -1;
        if (point.y < 0 || point.y > height) point.vy *= -1;
      }
      draw();
      frame = window.requestAnimationFrame(animate);
    }

    function syncAnimation() {
      window.cancelAnimationFrame(frame);
      frame = 0;
      if (motion.matches || document.hidden) draw();
      else frame = window.requestAnimationFrame(animate);
    }

    function move(event) {
      const bounds = host.getBoundingClientRect();
      pointer.x = event.clientX - bounds.left;
      pointer.y = event.clientY - bounds.top;
    }
    function leave() { pointer.x = -1000; pointer.y = -1000; }

    const observer = new ResizeObserver(resize);
    observer.observe(host);
    host.addEventListener('pointermove', move);
    host.addEventListener('pointerleave', leave);
    motion.addEventListener('change', syncAnimation);
    document.addEventListener('visibilitychange', syncAnimation);
    resize();
    syncAnimation();
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      host.removeEventListener('pointermove', move);
      host.removeEventListener('pointerleave', leave);
      motion.removeEventListener('change', syncAnimation);
      document.removeEventListener('visibilitychange', syncAnimation);
    };
  }, [maxParticles]);

  return <canvas ref={canvasRef} className="particle-network" aria-hidden="true" />;
}
