const progress = document.querySelector('.scroll-progress');
const setProgress = () => {
  if (!progress) return;
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const value = max <= 0 ? 0 : (window.scrollY / max) * 100;
  progress.style.width = `${value}%`;
};
setProgress();
window.addEventListener('scroll', setProgress, { passive: true });

const revealItems = document.querySelectorAll('[data-reveal]');
if ('IntersectionObserver' in window) {
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealItems.forEach((item, index) => {
    item.style.transitionDelay = `${Math.min(index * 55, 330)}ms`;
    revealObserver.observe(item);
  });
} else {
  revealItems.forEach((item) => item.classList.add('is-visible'));
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('.contact-button');
  if (!button) return;
  const panel = button.closest('.seller-panel');
  const phoneBox = panel?.querySelector('.phone-box');
  if (!phoneBox) return;
  phoneBox.textContent = button.dataset.phone;
  phoneBox.classList.remove('hidden');
  button.textContent = 'Телефон көрсетілді';
});

document.querySelectorAll('.payment-form input[name="card_number"]').forEach((input) => {
  input.addEventListener('input', () => {
    const digits = input.value.replace(/\D/g, '').slice(0, 16);
    input.value = digits.replace(/(.{4})/g, '$1 ').trim();
  });
});

document.querySelectorAll('.copy-link').forEach((button) => {
  button.addEventListener('click', async () => {
    const text = button.dataset.copy;
    try {
      await navigator.clipboard.writeText(text);
      button.classList.add('copied');
      const original = button.textContent;
      button.textContent = 'Көшірілді ✓';
      setTimeout(() => {
        button.textContent = original;
        button.classList.remove('copied');
      }, 1600);
    } catch (_) {
      window.prompt('Kaspi сілтемесі:', text);
    }
  });
});

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reduceMotion) {
  document.querySelectorAll('.tilt-card').forEach((card) => {
    card.addEventListener('mousemove', (event) => {
      if (window.matchMedia('(max-width: 900px)').matches) return;
      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const rotateY = ((x / rect.width) - 0.5) * 9;
      const rotateX = ((0.5 - y / rect.height)) * 9;
      card.style.transform = `perspective(980px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-5px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  document.querySelectorAll('.magnetic').forEach((button) => {
    button.addEventListener('mousemove', (event) => {
      if (window.matchMedia('(max-width: 900px)').matches) return;
      const rect = button.getBoundingClientRect();
      const x = (event.clientX - rect.left - rect.width / 2) * 0.16;
      const y = (event.clientY - rect.top - rect.height / 2) * 0.16;
      button.style.transform = `translate(${x}px, ${y}px)`;
    });
    button.addEventListener('mouseleave', () => {
      button.style.transform = '';
    });
  });
}
