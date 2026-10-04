document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-review-carousel]').forEach((carousel) => {
    const track = carousel.querySelector('[data-review-track]');
    if (!track) return;

    const scrollByCard = (direction) => {
      const card = track.querySelector('.collector-review-card');
      if (!card) return;
      const gap = Number.parseFloat(getComputedStyle(track).columnGap) || 0;
      track.scrollBy({ left: direction * (card.getBoundingClientRect().width + gap), behavior: 'smooth' });
    };

    carousel.querySelector('[data-review-prev]')?.addEventListener('click', () => scrollByCard(-1));
    carousel.querySelector('[data-review-next]')?.addEventListener('click', () => scrollByCard(1));
  });

  document.querySelectorAll('[data-discovery-carousel]').forEach((carousel) => {
    const track = carousel.querySelector('[data-discovery-track]');
    if (!track) return;

    const scrollByCard = (direction) => {
      const card = track.querySelector('.discovery-scroll-card');
      if (!card) return;
      const gap = Number.parseFloat(getComputedStyle(track).columnGap) || 0;
      track.scrollBy({ left: direction * (card.getBoundingClientRect().width + gap), behavior: 'smooth' });
    };

    carousel.querySelector('[data-discovery-prev]')?.addEventListener('click', () => scrollByCard(-1));
    carousel.querySelector('[data-discovery-next]')?.addEventListener('click', () => scrollByCard(1));
  });
});
