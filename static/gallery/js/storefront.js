(() => {
	const openButtons = document.querySelectorAll('[data-open-panel]');
	const closeButtons = document.querySelectorAll('[data-close-panel]');

	openButtons.forEach((button) => {
		button.addEventListener('click', () => document.getElementById(button.dataset.openPanel)?.showModal());
	});
	closeButtons.forEach((button) => {
		button.addEventListener('click', () => button.closest('dialog')?.close());
	});
	document.querySelectorAll('dialog').forEach((panel) => {
		panel.addEventListener('click', (event) => {
			if (event.target === panel) panel.close();
		});
	});
	if (window.location.hash === '#cart-panel') document.getElementById('cart-panel')?.showModal();

	const searchInput = document.getElementById('instant-search');
	const searchResults = document.getElementById('search-results');
	let searchTimer;
	if (!window.htmx) searchInput?.addEventListener('input', () => {
		window.clearTimeout(searchTimer);
		const query = searchInput.value.trim();
		if (query.length < 2) {
			searchResults.innerHTML = '<p class="panel-hint">Type at least two letters to search.</p>';
			return;
		}
		searchResults.innerHTML = '<p class="panel-hint">Searching the collection…</p>';
		searchTimer = window.setTimeout(async () => {
			try {
				const response = await fetch(`/search/?q=${encodeURIComponent(query)}`, { headers: { Accept: 'application/json' } });
				const data = await response.json();
				searchResults.replaceChildren();
				if (!data.results.length) {
					searchResults.innerHTML = '<p class="panel-hint">No matching artwork found.</p>';
					return;
				}
				data.results.forEach((result) => {
					const link = document.createElement('a');
					link.className = 'search-result';
					link.href = result.url;
					const title = document.createElement('strong');
					title.textContent = result.title;
					const detail = document.createElement('span');
					detail.textContent = `${result.artist} · ${result.category}`;
					const price = document.createElement('small');
					price.textContent = result.price;
					link.append(title, detail, price);
					searchResults.append(link);
				});
			} catch {
				searchResults.innerHTML = '<p class="panel-hint">Search is unavailable right now.</p>';
			}
		}, 180);
	});

	const catalog = document.getElementById('catalog-grid');
	const filterForm = document.querySelector('.filter-controls');
	const emptyMessage = document.querySelector('[data-filter-empty]');
	const countLabel = document.querySelector('[data-art-count]');
	const applyFilters = () => {
		if (!catalog || !filterForm) return;
		const data = new FormData(filterForm);
		const minimum = Number(data.get('min_price')) || 0;
		const maximum = Number(data.get('max_price')) || Infinity;
		const stock = data.get('availability');
		const cards = [...catalog.querySelectorAll('.art-card')];
		let visibleCount = 0;
		cards.forEach((card) => {
			const price = Number(card.dataset.price) || 0;
			const visible = price >= minimum && price <= maximum && (!stock || card.dataset.stock === stock);
			card.hidden = !visible;
			if (visible) visibleCount += 1;
		});
		if (emptyMessage) emptyMessage.hidden = visibleCount > 0;
		if (countLabel) countLabel.textContent = `${visibleCount} ${visibleCount === 1 ? 'work' : 'works'}`;
		const sort = data.get('sort');
		if (sort) {
			cards.sort((first, second) => {
				const difference = (Number(first.dataset.price) || 0) - (Number(second.dataset.price) || 0);
				return (sort === 'price-high' ? -difference : difference) || first.dataset.title.localeCompare(second.dataset.title);
			}).forEach((card) => catalog.append(card));
		}
	};
	filterForm?.addEventListener('input', applyFilters);
	filterForm?.addEventListener('change', applyFilters);
	filterForm?.addEventListener('submit', (event) => {
		if (event.submitter?.classList.contains('filter-apply')) return;
		event.preventDefault();
		applyFilters();
	});

	const viewButtons = document.querySelectorAll('[data-view]');
	const setView = (view) => {
		if (!catalog) return;
		catalog.classList.toggle('is-list', view === 'list');
		viewButtons.forEach((button) => {
			const selected = button.dataset.view === view;
			button.classList.toggle('is-selected', selected);
			button.setAttribute('aria-pressed', String(selected));
		});
		try { window.localStorage.setItem('gallery-view', view); } catch {}
	};
	viewButtons.forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
	try { setView(window.localStorage.getItem('gallery-view') || 'grid'); } catch { setView('grid'); }

	const sizeSelect = document.querySelector('[data-price-size]');
	const priceDisplay = document.querySelector('[data-live-price]');
	const productForm = sizeSelect?.closest('.product-options');
	const updatePrice = () => {
		if (!sizeSelect || !priceDisplay || !productForm) return;
		const base = Number(productForm.dataset.basePrice);
		if (!Number.isFinite(base) || !base) {
			priceDisplay.textContent = 'Price on request';
			return;
		}
		const multiplier = Number(sizeSelect.selectedOptions[0].dataset.multiplier) || 1;
		priceDisplay.textContent = `PKR ${Math.round(base * multiplier).toLocaleString('en-PK')}`;
	};
	sizeSelect?.addEventListener('change', updatePrice);
	const preview = document.querySelector('[data-frame-preview]');
	document.querySelectorAll('[data-frame-option]').forEach((option) => {
		option.addEventListener('change', () => {
			if (!preview) return;
			preview.className = `detail-image frame-preview frame-preview--${option.value}`;
		});
	});
	updatePrice();

	if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
		document.querySelectorAll('[data-tilt]').forEach((image) => {
			image.addEventListener('pointermove', (event) => {
				const bounds = image.getBoundingClientRect();
				const x = (event.clientX - bounds.left) / bounds.width - 0.5;
				const y = (event.clientY - bounds.top) / bounds.height - 0.5;
				image.style.transform = `perspective(850px) rotateX(${-y * 5}deg) rotateY(${x * 5}deg) scale3d(1.015, 1.015, 1.015)`;
			});
			image.addEventListener('pointerleave', () => { image.style.transform = ''; });
		});
	}

	if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window) {
		const reveal = new IntersectionObserver((entries, observer) => {
			entries.forEach((entry) => {
				if (entry.isIntersecting) {
					entry.target.classList.add('is-revealed');
					observer.unobserve(entry.target);
				}
			});
		}, { threshold: 0.08 });
		document.querySelectorAll('.art-card, .featured, .visit-band').forEach((element) => reveal.observe(element));
	}
})();