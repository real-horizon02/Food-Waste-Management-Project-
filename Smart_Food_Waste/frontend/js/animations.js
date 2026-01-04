// animations.js - smooth scroll animations + particle background + reveal

(function () {
  // run on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    // start overlay -> hide after ready and small delay
    const overlay = document.getElementById('launch-overlay');
    setTimeout(() => {
      if (overlay) {
        overlay.style.transition = 'opacity 650ms cubic-bezier(.2,.9,.3,1), transform 650ms ease';
        overlay.style.opacity = '0';
        overlay.style.transform = 'scale(0.997)';
        setTimeout(()=> overlay.remove(), 780);
      }
    }, 650);

    initParticles();
    initRevealObserver();
    initNavButtons();
    startRenderLoop();
  });

  // ---------- particles ----------
  function initParticles() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w = canvas.width = innerWidth;
    let h = canvas.height = innerHeight;
    const particles = [];
    const pal = ['rgba(255,255,255,0.04)', 'rgba(255,240,200,0.03)', 'rgba(180,200,255,0.02)'];

    window.addEventListener('resize', () => { w = canvas.width = innerWidth; h = canvas.height = innerHeight; });

    function spawn() {
      const size = 12 + Math.random()*26;
      particles.push({
        x: Math.random()*w,
        y: h + Math.random()*160,
        vx: (Math.random()-0.5)*0.25,
        vy: - (0.2 + Math.random()*0.6),
        s: size,
        c: pal[(Math.random()*pal.length)|0],
        life: 220 + Math.random()*240
      });
    }

    for (let i=0;i<40;i++) spawn();

    function step() {
      ctx.clearRect(0,0,w,h);
      if (particles.length < 28 && Math.random() > 0.4) spawn();
      for (let i=particles.length-1;i>=0;i--) {
        const p = particles[i];
        p.x += p.vx; p.y += p.vy; p.life--;
        const alpha = Math.max(0, Math.min(1, p.life/260));
        ctx.fillStyle = p.c.replace(/\d+\)$/,'') + `${alpha})`;
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, p.s*0.6, p.s*0.32, 0.3, 0, Math.PI*2);
        ctx.fill();
        if (p.life <= 0 || p.y < -200) particles.splice(i,1);
      }
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ---------- reveal observer ----------
  function initRevealObserver() {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          en.target.classList.add('in-view');
        }
      });
    }, { threshold: 0.12 });

    document.querySelectorAll('.reveal, .section').forEach(el => obs.observe(el));
  }

  // ---------- nav buttons -> sections with FLIP-ish transitions ----------
  function initNavButtons() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        // Don't handle clicks if they originated from an input or form element
        if (e.target !== btn && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.closest('form'))) {
          return;
        }
        const t = e.currentTarget;
        
        // Check for logout action
        const action = t.getAttribute('data-action');
        if (action === 'logout') {
          if (typeof logout === 'function') {
            logout();
          }
          return;
        }
        
        const dest = t.getAttribute('data-target');
        if (!dest) return;
        document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
        t.classList.add('active');
        showSectionFlip(dest);
      });
    });
  }

  // FLIP-ish fast section swap
  function showSectionFlip(sectionId) {
    const oldEl = document.querySelector('.section.active');
    const newEl = document.getElementById(sectionId);
    if (!newEl || oldEl === newEl) return;

    // capture first
    const oldRect = oldEl.getBoundingClientRect();
    newEl.style.display = ''; // ensure measured
    const newRect = newEl.getBoundingClientRect();

    // create clone for animation
    const clone = oldEl.cloneNode(true);
    clone.style.position = 'fixed';
    clone.style.left = oldRect.left + 'px';
    clone.style.top = oldRect.top + 'px';
    clone.style.width = oldRect.width + 'px';
    clone.style.height = oldRect.height + 'px';
    clone.style.margin = '0';
    clone.style.zIndex = '9999';
    clone.style.transition = 'transform 520ms cubic-bezier(.2,.9,.3,1), opacity 420ms ease';
    document.body.appendChild(clone);

    // hide new element while animating
    newEl.style.opacity = '0';
    newEl.classList.add('active');

    // compute delta
    const dx = newRect.left - oldRect.left;
    const dy = newRect.top - oldRect.top;
    const sx = newRect.width / oldRect.width;
    const sy = newRect.height / oldRect.height;

    // animate clone to new position/scale
    requestAnimationFrame(() => {
      clone.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
      clone.style.opacity = '0';
    });

    // after animation, remove clone, finalize states
    setTimeout(() => {
      clone.remove();
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      newEl.classList.add('active');
      newEl.style.opacity = '';
      // ensure reveal
      newEl.querySelectorAll('.reveal').forEach(r => r.classList.add('in-view'));
    }, 540);
  }

  // ------------- small render loop for parallax movement -------------
  let lastY = 0;
  function startRenderLoop() {
    const bg = document.querySelector('.bg-svg');
    function loop() {
      const y = window.scrollY;
      const dy = y - lastY;
      lastY = y;
      if (bg) {
        bg.style.transform = `translateY(${Math.min(-10 + y * -0.03, 10)}px)`;
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

})();

// animations.js - Section transitions + reveal
document.addEventListener('DOMContentLoaded', () => {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => e.isIntersecting && e.target.classList.add('in-view'));
  }, { threshold: 0.15 });
  document.querySelectorAll('.section').forEach(s => observer.observe(s));

  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      const id = btn.dataset.target;
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
    });
  });
});

