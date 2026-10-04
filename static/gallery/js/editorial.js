(() => {
	const root = document.documentElement;
	const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	const themeButton = document.querySelector('[data-theme-toggle]');
	const setTheme = (theme) => {
		root.dataset.theme = theme;
		if (themeButton) {
			const nextLabel = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
			themeButton.setAttribute('aria-label', nextLabel);
			themeButton.title = nextLabel;
		}
	};
	try { setTheme(window.localStorage.getItem('ahmaan-theme') || 'light'); } catch { setTheme('light'); }
	themeButton?.addEventListener('click', () => {
		const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
		setTheme(nextTheme);
		try { window.localStorage.setItem('ahmaan-theme', nextTheme); } catch {}
	});

	const announcements = [...document.querySelectorAll('[data-announcement]')];
	if (announcements.length > 1) {
		let currentAnnouncement = 0;
		window.setInterval(() => {
			announcements[currentAnnouncement].hidden = true;
			currentAnnouncement = (currentAnnouncement + 1) % announcements.length;
			announcements[currentAnnouncement].hidden = false;
		}, 4800);
	}

	const mobileToggle = document.querySelector('[data-mobile-menu-toggle]');
	mobileToggle?.addEventListener('click', () => {
		const isOpen = document.body.classList.toggle('mobile-nav-open');
		mobileToggle.setAttribute('aria-expanded', String(isOpen));
		mobileToggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
	});
	document.querySelectorAll('#main-navigation a').forEach((link) => link.addEventListener('click', () => {
		document.body.classList.remove('mobile-nav-open');
		mobileToggle?.setAttribute('aria-expanded', 'false');
	}));

	const wishlistButtons = [...document.querySelectorAll('[data-wishlist-toggle]')].filter((button) => !button.closest('[data-wishlist-form]'));
	const wishlistCount = document.querySelector('[data-wishlist-count]');
	let wishlist = [];
	try { wishlist = JSON.parse(window.localStorage.getItem('ahmaan-wishlist') || '[]'); } catch { wishlist = []; }
	const updateWishlist = () => {
		wishlistButtons.forEach((button) => {
			const selected = wishlist.includes(button.dataset.artworkId);
			button.setAttribute('aria-pressed', String(selected));
			button.setAttribute('aria-label', `${selected ? 'Remove' : 'Save'} ${button.closest('.editorial-art-card')?.querySelector('h3')?.textContent.trim() || 'artwork'} ${selected ? 'from' : 'to'} wishlist`);
		});
		if (wishlistCount && wishlistButtons.length) {
			wishlistCount.textContent = String(wishlist.length);
			wishlistCount.hidden = wishlist.length === 0;
		}
	};
	wishlistButtons.forEach((button) => button.addEventListener('click', () => {
		const id = button.dataset.artworkId;
		wishlist = wishlist.includes(id) ? wishlist.filter((item) => item !== id) : [...wishlist, id];
		try { window.localStorage.setItem('ahmaan-wishlist', JSON.stringify(wishlist)); } catch {}
		updateWishlist();
	}));
	updateWishlist();

	document.querySelectorAll('[data-quick-add]').forEach((button) => button.addEventListener('click', () => {
		const panel = document.getElementById('cart-panel');
		const feedback = document.getElementById('cart-action-feedback');
		if (feedback) feedback.textContent = `Selected artwork preview: ${button.dataset.title}.`;
		if (panel && !panel.open) panel.showModal();
	}));

	const heroSlides = [...document.querySelectorAll('[data-hero-slide]')];
	const heroDots = [...document.querySelectorAll('[data-hero-dot]')];
	const heroControls = document.querySelector('[data-hero-controls]');
	const heroCount = document.querySelector('[data-hero-count]');
	if (heroSlides.length < 2 && heroControls) heroControls.hidden = true;
	if (heroSlides.length > 1) {
		let activeHero = 0;
		let heroTimer;
		const showHero = (index) => {
			activeHero = (index + heroSlides.length) % heroSlides.length;
			heroSlides.forEach((slide, slideIndex) => {
				const active = slideIndex === activeHero;
				slide.hidden = !active;
				slide.classList.toggle('is-active', active);
				const video = slide.querySelector('video');
				if (video) active ? video.play().catch(() => {}) : video.pause();
			});
			heroDots.forEach((dot, dotIndex) => dot.setAttribute('aria-current', String(dotIndex === activeHero)));
			if (heroCount) {
				heroCount.querySelector('[data-hero-current]').textContent = String(activeHero + 1).padStart(2, '0');
				heroCount.querySelector('[data-hero-total]').textContent = String(heroSlides.length).padStart(2, '0');
				heroCount.setAttribute('aria-label', `Slide ${activeHero + 1} of ${heroSlides.length}`);
			}
		};
		showHero(0);
		const startHeroTimer = () => {
			window.clearInterval(heroTimer);
			if (!reducedMotion) heroTimer = window.setInterval(() => showHero(activeHero + 1), 6500);
		};
		document.querySelector('[data-hero-prev]')?.addEventListener('click', () => { showHero(activeHero - 1); startHeroTimer(); });
		document.querySelector('[data-hero-next]')?.addEventListener('click', () => { showHero(activeHero + 1); startHeroTimer(); });
		heroDots.forEach((dot) => dot.addEventListener('click', () => { showHero(Number(dot.dataset.heroDot)); startHeroTimer(); }));
		startHeroTimer();
	}

	const testimonialSlides = [...document.querySelectorAll('[data-testimonial-slide]')];
	if (testimonialSlides.length > 1) {
		let activeTestimonial = 0;
		const count = document.querySelector('[data-testimonial-count]');
		const showTestimonial = (index) => {
			activeTestimonial = (index + testimonialSlides.length) % testimonialSlides.length;
			testimonialSlides.forEach((slide, slideIndex) => { slide.hidden = slideIndex !== activeTestimonial; });
			if (count) count.textContent = `${String(activeTestimonial + 1).padStart(2, '0')} / ${String(testimonialSlides.length).padStart(2, '0')}`;
		};
		document.querySelector('[data-testimonial-prev]')?.addEventListener('click', () => showTestimonial(activeTestimonial - 1));
		document.querySelector('[data-testimonial-next]')?.addEventListener('click', () => showTestimonial(activeTestimonial + 1));
	}

	const activeFilters = { space: '', color: '' };
	const filterButtons = [...document.querySelectorAll('[data-home-filter]')];
	const applyHomeFilters = () => {
		document.querySelectorAll('.editorial-art-card').forEach((card) => {
			const hasSpace = !activeFilters.space || card.dataset.spaceTags.split(',').includes(activeFilters.space);
			const hasColor = !activeFilters.color || card.dataset.colorTags.split(',').includes(activeFilters.color);
			card.hidden = !hasSpace || !hasColor;
		});
		filterButtons.forEach((button) => {
			const selected = button.dataset.homeFilter !== 'clear' && activeFilters[button.dataset.homeFilter] === button.dataset.filterValue;
			if (button.dataset.homeFilter === 'clear') button.setAttribute('aria-pressed', String(!activeFilters.space && !activeFilters.color));
			else button.setAttribute('aria-pressed', String(selected));
		});
	};
	filterButtons.forEach((button) => button.addEventListener('click', () => {
		const kind = button.dataset.homeFilter;
		if (kind === 'clear') {
			activeFilters.space = '';
			activeFilters.color = '';
		} else {
			activeFilters[kind] = activeFilters[kind] === button.dataset.filterValue ? '' : button.dataset.filterValue;
		}
		applyHomeFilters();
		if (kind !== 'clear') document.getElementById('featured-works')?.scrollIntoView({ behavior: reducedMotion ? 'instant' : 'smooth', block: 'start' });
	}));

	const images = [...document.querySelectorAll('.editorial-art-visual, .journal-image')];
	images.forEach((container) => {
		const image = container.querySelector('img');
		if (!image) { container.classList.add('is-loaded'); return; }
		if (image.complete) container.classList.add('is-loaded');
		else image.addEventListener('load', () => container.classList.add('is-loaded'), { once: true });
	});

	if (!reducedMotion && 'IntersectionObserver' in window) {
		document.body.classList.add('js-reveal-ready');
		const revealObserver = new IntersectionObserver((entries, observer) => {
			entries.forEach((entry) => {
				if (entry.isIntersecting) {
					entry.target.classList.add('is-revealed');
					observer.unobserve(entry.target);
				}
			});
		}, { threshold: 0.08 });
		document.querySelectorAll('[data-reveal]').forEach((element) => revealObserver.observe(element));
	}

	const welcomeDialog = document.querySelector('[data-welcome-offer]');
	if (welcomeDialog) {
		const welcomeKey = 'ahmaan-welcome-dismissed';
		const dismissWelcome = () => { try { window.localStorage.setItem(welcomeKey, '1'); } catch {} };
		welcomeDialog.querySelectorAll('[data-close-panel]').forEach((button) => button.addEventListener('click', dismissWelcome));
		welcomeDialog.addEventListener('click', (event) => { if (event.target === welcomeDialog) dismissWelcome(); });
		welcomeDialog.querySelector('form')?.addEventListener('submit', dismissWelcome);
		let dismissed = false;
		try { dismissed = window.localStorage.getItem(welcomeKey) === '1'; } catch { dismissed = true; }
		if (!dismissed) window.setTimeout(() => { if (!welcomeDialog.open) welcomeDialog.showModal(); }, 1800);
	}

	if ('startViewTransition' in document && !reducedMotion) {
		document.documentElement.style.viewTransitionName = 'gallery-page';
	}
})();
