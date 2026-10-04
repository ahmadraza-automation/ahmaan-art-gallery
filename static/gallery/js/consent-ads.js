(() => {
  const storageKey = 'ahmaan-cookie-consent-v1';
  const banner = document.querySelector('[data-cookie-banner]');
  const savedChoice = window.localStorage.getItem(storageKey);

  const enableAds = () => {
    const slots = [...document.querySelectorAll('[data-adsense-slot]')];
    if (!slots.length || document.querySelector('[data-adsense-script]')) return;

    const client = slots[0].dataset.adClient;
    if (!client || slots.some((slot) => slot.dataset.adClient !== client)) return;

    const script = document.createElement('script');
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.dataset.adsenseScript = 'true';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(client)}`;
    script.onload = () => {
      slots.forEach((slot) => {
        const ad = document.createElement('ins');
        ad.className = 'adsbygoogle';
        ad.style.display = 'block';
        ad.dataset.adClient = client;
        ad.dataset.adSlot = slot.dataset.adSlot;
        ad.dataset.adFormat = 'auto';
        ad.dataset.fullWidthResponsive = 'true';
        slot.replaceChildren(ad);
        slot.hidden = false;
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      });
    };
    document.head.append(script);
  };

  const choose = (choice) => {
    const previousChoice = window.localStorage.getItem(storageKey);
    window.localStorage.setItem(storageKey, choice);
    if (banner) {
      banner.hidden = true;
      document.body.classList.remove('cookie-consent-visible');
    }
    if (previousChoice === 'accepted' && choice !== 'accepted') {
      window.location.reload();
      return;
    }
    if (choice === 'accepted') enableAds();
  };

  if (banner && !savedChoice) {
    banner.hidden = false;
    document.body.classList.add('cookie-consent-visible');
  }
  if (savedChoice === 'accepted') enableAds();
  document.querySelectorAll('[data-cookie-choice]').forEach((button) => {
    button.addEventListener('click', () => choose(button.dataset.cookieChoice));
  });
  document.querySelectorAll('[data-cookie-settings]').forEach((button) => {
    button.addEventListener('click', () => {
      if (banner) banner.hidden = false;
      document.body.classList.add('cookie-consent-visible');
    });
  });
})();
