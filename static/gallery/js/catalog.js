(() => {
	const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

	const updateWishlistState = (artworkId, added, count, kind = 'catalog') => {
		document.querySelectorAll(`[data-wishlist-toggle][data-wishlist-kind="${kind}"][data-artwork-id="${artworkId}"]`).forEach((button) => {
			button.setAttribute('aria-pressed', String(added));
			const title = button.dataset.artworkTitle || button.closest('.editorial-art-card')?.querySelector('h3')?.textContent.trim() || 'artwork';
			button.setAttribute('aria-label', `${added ? 'Remove' : 'Save'} ${title} ${added ? 'from' : 'to'} wishlist`);
		});
		document.querySelectorAll('[data-wishlist-count]').forEach((badge) => {
			badge.textContent = String(count);
			badge.hidden = count < 1;
		});
		if (!added && window.location.pathname === '/wishlist/') {
			document.querySelector(`[data-wishlist-toggle][data-wishlist-kind="${kind}"][data-artwork-id="${artworkId}"]`)?.closest('.catalog-card')?.remove();
		}
	};
	document.addEventListener('submit', async (event) => {
		const form = event.target.closest('[data-wishlist-form]');
		if (!form) return;
		if (window.htmx && form.hasAttribute('hx-post')) return;
		event.preventDefault();
		const button = form.querySelector('[data-wishlist-toggle]');
		try {
			const response = await fetch(form.action, { method: 'POST', headers: { 'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]')?.value || csrfToken, Accept: 'application/json' } });
			if (!response.ok) throw new Error('Wishlist request failed.');
			const data = await response.json();
			updateWishlistState(data.artwork_id, data.added, data.count, data.kind);
		} catch {
			form.submit();
		} finally {
			button?.classList.add('wishlist-heart-pulse');
			window.setTimeout(() => button?.classList.remove('wishlist-heart-pulse'), 350);
		}
	});
	document.body.addEventListener('wishlistUpdated', (event) => {
		const detail = event.detail || {};
		updateWishlistState(detail.artwork_id, detail.added, detail.count, detail.kind);
	});
	document.body.addEventListener('compareUpdated', (event) => {
		const detail = event.detail || {};
		const ids = detail.ids || [];
		document.querySelectorAll('[data-compare-toggle]').forEach((button) => {
			const selected = ids.includes(`${button.dataset.artworkType || 'catalog'}:${button.dataset.artworkId}`);
			button.setAttribute('aria-pressed', String(selected));
			button.setAttribute('aria-label', `${selected ? 'Remove' : 'Add'} ${button.dataset.artworkTitle} ${selected ? 'from' : 'to'} compare`);
		});
		document.querySelectorAll('[data-compare-count]').forEach((badge) => {
			badge.textContent = String(detail.count || 0);
			badge.hidden = !detail.count;
		});
		const feedback = document.querySelector('[data-compare-feedback]');
		if (feedback) {
			feedback.textContent = detail.full ? 'Compare up to three artworks at a time.' : `${detail.added ? 'Added to' : 'Updated'} your comparison list.`;
			feedback.hidden = false;
			window.setTimeout(() => { feedback.hidden = true; }, 2600);
		}
		if (window.location.pathname === '/compare/') window.location.reload();
	});

	const quickView = document.getElementById('quick-view-dialog');
	const quickViewContent = document.getElementById('quick-view-content');
	if (window.htmx) {
		document.body.addEventListener('htmx:afterSwap', (event) => {
			if (event.detail.target === quickViewContent && quickView && !quickView.open) quickView.showModal();
		});
	} else {
		document.addEventListener('click', async (event) => {
			const trigger = event.target.closest('[data-quick-view]');
			if (!trigger || !quickViewContent || !quickView) return;
			event.preventDefault();
			quickViewContent.innerHTML = '<p class="panel-hint">Loading artwork…</p>';
			quickView.showModal();
			try {
				const response = await fetch(trigger.dataset.quickViewUrl, { headers: { 'HX-Request': 'true' } });
				quickViewContent.innerHTML = await response.text();
			} catch { quickViewContent.innerHTML = '<p class="panel-hint">Artwork preview is unavailable.</p>'; }
		});
	}

	document.addEventListener('click', (event) => {
		const zoomTrigger = event.target.closest('[data-lightbox-open]');
		const lightbox = document.getElementById('artwork-lightbox');
		const lightboxImage = lightbox?.querySelector('[data-lightbox-image]');
		if (zoomTrigger && lightbox && lightboxImage) {
			lightboxImage.src = zoomTrigger.dataset.imageSrc;
			lightboxImage.alt = zoomTrigger.querySelector('img')?.alt || '';
			lightboxImage.classList.remove('is-zoomed');
			lightbox.showModal();
		}
		if (event.target.matches('[data-lightbox-image]')) event.target.classList.toggle('is-zoomed');
		const columnButton = event.target.closest('[data-grid-columns]');
		if (columnButton) {
			const columns = columnButton.dataset.gridColumns;
			const grid = document.getElementById('shop-grid');
			if (grid) grid.dataset.columns = columns;
			document.querySelectorAll('[data-grid-columns]').forEach((button) => button.setAttribute('aria-pressed', String(button === columnButton)));
			const hiddenInput = document.querySelector('[data-columns-value]');
			if (hiddenInput) hiddenInput.value = columns;
		}
	});
	document.addEventListener('change', (event) => {
		if (event.target.matches('[data-filter-sort]') && !window.htmx) document.getElementById('shop-filters')?.requestSubmit();
		if (event.target.matches('[data-price-range]')) {
			const output = document.querySelector(`[data-range-label="${event.target.dataset.priceRange}"]`);
			if (output) output.textContent = Number(event.target.value).toLocaleString('en-PK');
		}
	});

	const productForm = document.querySelector('[data-product-options]');
	const priceOutput = document.querySelector('[data-live-price]');
	const updateProductPrice = () => {
		if (!productForm || !priceOutput) return;
		let price = Number(productForm.dataset.basePrice) || 0;
		productForm.querySelectorAll('[data-custom-price]').forEach((control) => {
			if (control.type === 'radio' && !control.checked) return;
			if (control.tagName === 'SELECT') {
				price += Number(control.selectedOptions[0]?.dataset.modifier) || 0;
			} else {
				price += Number(control.dataset.modifier) || 0;
			}
		});
		priceOutput.textContent = `PKR ${Math.round(price).toLocaleString('en-PK')}`;
	};
	productForm?.addEventListener('change', (event) => {
		if (event.target.matches('[data-custom-price]')) updateProductPrice();
		if (event.target.matches('[data-frame-style]')) document.querySelector('.product-gallery')?.setAttribute('data-frame', event.target.dataset.frameStyle);
	});
	updateProductPrice();

	document.body.addEventListener('htmx:afterRequest', (event) => {
		if (event.detail.elt?.matches('[data-load-more]') && event.detail.successful) event.detail.elt.remove();
	});

	const roomCanvas = document.querySelector('[data-room-canvas]');
	const roomWallInput = document.querySelector('[data-room-wall]');
	const roomArtwork = document.querySelector('[data-room-artwork]');
	const roomScale = document.querySelector('[data-room-scale]');
	const roomDownload = document.querySelector('[data-room-download]');
	if (roomCanvas && roomWallInput && roomArtwork && roomScale && roomDownload) {
		const context = roomCanvas.getContext('2d');
		const wall = new Image();
		let wallReady = false;
		let artworkReady = false;
		let artworkX = roomCanvas.width * .5;
		let artworkY = roomCanvas.height * .52;
		let dragging = false;
		let dragOffsetX = 0;
		let dragOffsetY = 0;
		const drawCover = (image, canvas) => {
			const scale = Math.max(canvas.width / image.width, canvas.height / image.height);
			const width = image.width * scale;
			const height = image.height * scale;
			context.drawImage(image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
		};
		const drawRoom = () => {
			context.clearRect(0, 0, roomCanvas.width, roomCanvas.height);
			if (wallReady) drawCover(wall, roomCanvas);
			else {
				context.fillStyle = '#dcd8ce';
				context.fillRect(0, 0, roomCanvas.width, roomCanvas.height);
				context.fillStyle = '#2c3e35';
				context.font = '22px Inter, sans-serif';
				context.textAlign = 'center';
				context.fillText('Upload a wall photo to begin', roomCanvas.width / 2, roomCanvas.height / 2);
			}
			if (!artworkReady) return;
			const width = roomCanvas.width * Number(roomScale.value) / 100;
			const height = width * roomArtwork.naturalHeight / roomArtwork.naturalWidth;
			context.save();
			context.shadowColor = '#0005';
			context.shadowBlur = 18;
			context.drawImage(roomArtwork, artworkX - width / 2, artworkY - height / 2, width, height);
			context.restore();
		};
		roomArtwork.addEventListener('load', () => { artworkReady = true; drawRoom(); });
		if (roomArtwork.complete && roomArtwork.naturalWidth) { artworkReady = true; drawRoom(); }
		roomWallInput.addEventListener('change', () => {
			const file = roomWallInput.files?.[0];
			if (!file || !file.type.startsWith('image/')) return;
			wall.src = URL.createObjectURL(file);
			wall.onload = () => { wallReady = true; roomDownload.disabled = false; drawRoom(); };
		});
		roomScale.addEventListener('input', drawRoom);
		const pointOnCanvas = (event) => {
			const bounds = roomCanvas.getBoundingClientRect();
			return { x: (event.clientX - bounds.left) * roomCanvas.width / bounds.width, y: (event.clientY - bounds.top) * roomCanvas.height / bounds.height };
		};
		roomCanvas.addEventListener('pointerdown', (event) => {
			const point = pointOnCanvas(event);
			dragging = true;
			dragOffsetX = point.x - artworkX;
			dragOffsetY = point.y - artworkY;
			roomCanvas.setPointerCapture(event.pointerId);
		});
		roomCanvas.addEventListener('pointermove', (event) => {
			if (!dragging) return;
			const point = pointOnCanvas(event);
			artworkX = point.x - dragOffsetX;
			artworkY = point.y - dragOffsetY;
			drawRoom();
		});
		roomCanvas.addEventListener('pointerup', () => { dragging = false; });
		roomCanvas.addEventListener('pointercancel', () => { dragging = false; });
		roomDownload.addEventListener('click', () => {
			const link = document.createElement('a');
			link.href = roomCanvas.toDataURL('image/png');
			link.download = 'ahmaan-art-room-preview.png';
			document.body.append(link);
			link.click();
			link.remove();
		});
		drawRoom();
	}

	document.addEventListener('keydown', (event) => {
		if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '')) return;
		event.preventDefault();
		const searchDialog = document.getElementById('search-panel');
		const searchInput = document.getElementById('instant-search');
		if (searchDialog && !searchDialog.open) searchDialog.showModal();
		window.setTimeout(() => searchInput?.focus(), 0);
	});
})();
