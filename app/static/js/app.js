let currentGame = null;
let currentPrediction = null;
let charts = {};
let filterOptions = { 
    genres: ["Acción", "Aventura", "RPG", "Estrategia", "Simulación", "Indie", "Multijugador", "Deportes", "Carreras"], 
    prices: [], 
    ages: [0, 3, 7, 12, 16, 18],
    max_languages: 74
};

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icon = type === 'error' ? '✕' : 'ℹ';
    
    notification.innerHTML = `
        <span class="notification-icon">${icon}</span>
        <span class="notification-message">${message}</span>
    `;

    container.innerHTML = '';
    container.appendChild(notification);
    
    // Show
    setTimeout(() => container.classList.add('show'), 10);
    
    // Hide
    setTimeout(() => {
        container.classList.remove('show');
    }, 4000);
}

// ============================================================
// NAVIGATION
// ============================================================
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    const appContainer = document.querySelector('.app-container');
    if (appContainer) {
        appContainer.scrollIntoView({ behavior: 'smooth' });
    }
}

function setupNavigation() {
    document.getElementById('btn-back-home').addEventListener('click', () => {
        showView('view-home');
        checkAndRestoreBg();
    });
    document.getElementById('btn-back-game').addEventListener('click', () => {
        showView('view-game');
    });
    document.getElementById('btn-back-home-custom').addEventListener('click', () => {
        showView('view-home');
        checkAndRestoreBg();
    });
}

// ============================================================
// SEARCH & TRENDING STATE
// ============================================================
let currentPage = 1;
let currentQuery = '';
let isLoading = false;
let hasMore = true;
let currentSort = 'desc';
let currentGenre = 'all';
let currentPrices = 'all';
let lastFeaturedAppId = null;

// ============================================================
// SEARCH (same fetch() pattern as flower3.html)
// ============================================================
function setupSearch() {
    const input = document.getElementById('search-input');
    let debounceTimer = null;

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(debounceTimer);

        debounceTimer = setTimeout(() => {
            currentQuery = q;
            currentPage = 1;
            hasMore = true;
            fetchGames(true);
        }, 300);

        // Keep icon hidden while there's text
        const icon = input.closest('.search-wrapper').querySelector('.search-icon');
        if (q) icon.classList.add('icon-hidden');
        else icon.classList.add('icon-hidden'); // still focused, keep hidden
    });

    // Glow animation + icon toggle on focus / blur
    const wrapper = input.closest('.search-wrapper');
    const icon = wrapper.querySelector('.search-icon');
    input.addEventListener('focus', () => {
        wrapper.classList.remove('glow-out');
        wrapper.classList.add('glow-in');
        icon.classList.add('icon-hidden');
    });
    input.addEventListener('blur', () => {
        wrapper.classList.remove('glow-in');
        wrapper.classList.add('glow-out');
        if (!input.value.trim()) {
            icon.classList.remove('icon-hidden');
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && lastFeaturedAppId) {
            navigateToGame(lastFeaturedAppId);
            input.blur();
        }
    });

    setupInfiniteScroll();

    // Sort Toggle
        // Top sort button removed. Logic moved to sidebar click.

    // Initialize Filters
    initFilters(wrapper, input);

    // Setup hover background crossfade layers (global for reuse)
    const grid = document.getElementById('game-grid');
    window._hoverBg = {
        layers: [
            document.getElementById('hover-bg-a'),
            document.getElementById('hover-bg-b'),
        ],
        activeLayer: 0,
        currentSrc: null,
        hideTimer: null,
    };

    // Click delegation
    grid.addEventListener('click', (e) => {
        const card = e.target.closest('.game-card');
        if (card) {
            if (card.classList.contains('custom-game-card')) {
                navigateToCustomGame();
            } else {
                navigateToGame(parseInt(card.dataset.appid));
            }
        }
    });

    // Hover delegation
    grid.addEventListener('mouseover', (e) => {
        const card = e.target.closest('.game-card');
        if (!card) return;
        if (window._hoverBg.hideTimer) { clearTimeout(window._hoverBg.hideTimer); window._hoverBg.hideTimer = null; }
        const img = card.querySelector('.game-card-banner');
        if (img && img.src) showHoverBg(img.src);
    });

    grid.addEventListener('mouseout', (e) => {
        const related = e.relatedTarget;

        if (!related || !related.closest('.game-card')) {
            // Check if there is an active exact match that should persist
            let keepBg = false;
            if (grid.classList.contains('single-result')) {
                keepBg = true;
            } else if (currentQuery) {
                const queryLower = currentQuery.toLowerCase().trim();
                const exactCard = Array.from(grid.querySelectorAll('.game-card')).find(c => c.dataset.name.toLowerCase() === queryLower);
                if (exactCard) {
                    keepBg = true;
                    const img = exactCard.querySelector('.game-card-banner');
                    if (img && img.src) showHoverBg(img.src);
                }
            }

            if (!keepBg) {
                window._hoverBg.hideTimer = setTimeout(() => hideHoverBg(), 150);
            }
        }
    });
}

/**
 * Initialize Genre and Price filters
 */
async function initFilters(wrapper, input) {
    const genreDropdown = document.getElementById('genre-dropdown');
    const priceDropdown = document.getElementById('price-dropdown');

    // Helper to toggle dropdowns
    const toggleDropdown = (dropdown) => {
        const isVisible = dropdown.classList.contains('visible');
        document.querySelectorAll('.filter-dropdown').forEach(d => d.classList.remove('visible'));
        if (!isVisible) dropdown.classList.add('visible');
    };

    // Helper to trigger glow
    const triggerSearchGlow = () => {
        wrapper.classList.remove('glow-in', 'glow-out');
        void wrapper.offsetWidth;
        wrapper.classList.add('glow-in');
        
        if (window._glowTimeout) clearTimeout(window._glowTimeout);
        window._glowTimeout = setTimeout(() => {
            if (document.activeElement !== input) {
                wrapper.classList.remove('glow-in');
                wrapper.classList.add('glow-out');
            }
        }, 400);
    };

    // Top buttons removed.

    // Close on click outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.filter-dropdown').forEach(d => d.classList.remove('visible'));
    });

    // Sidebar Bindings
    const sideSort = document.getElementById('side-btn-sort');
    const sideGenre = document.getElementById('side-btn-genre');
    const sidePrice = document.getElementById('side-btn-price');

    if (sideSort) {
        sideSort.addEventListener('click', (e) => {
            e.stopPropagation();
            currentSort = (currentSort === 'desc') ? 'asc' : 'desc';
            updateSidebarSortIcon();
            currentPage = 1;
            hasMore = true;
            fetchGames(true);
            triggerSearchGlow();
            triggerSidebarAnimation(sideSort);
        });
    }

    if (sideGenre) {
        sideGenre.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(genreDropdown);
            triggerSidebarAnimation(sideGenre, 'anim-genre');
        });
    }

    if (sidePrice) {
        sidePrice.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(priceDropdown);
            triggerSidebarAnimation(sidePrice, 'anim-price');
        });
    }

    function triggerSidebarAnimation(item, animClass) {
        // Underline animation
        item.classList.remove('anim-active');
        void item.offsetWidth;
        item.classList.add('anim-active');
        setTimeout(() => item.classList.remove('anim-active'), 850);

        // Icon animation
        if (animClass) {
            const icon = item.querySelector('.sidebar-icon');
            if (!icon) return;
            icon.classList.remove(animClass);
            void icon.offsetWidth;
            icon.classList.add(animClass);
            setTimeout(() => icon.classList.remove(animClass), 700);
        }
    }

    // Fetch and populate options
    try {
        const res = await fetch('/api/filter-options');
        const options = await res.json();
        if (options.genres && options.genres.length > 0) filterOptions.genres = options.genres;
        if (options.ages && options.ages.length > 0) filterOptions.ages = options.ages;
        if (options.prices && options.prices.length > 0) filterOptions.prices = options.prices;
        if (options.max_languages) filterOptions.max_languages = options.max_languages;

        // Genres
        genreDropdown.innerHTML = `<div class="filter-option active" data-val="all">Todos los géneros</div>`;
        filterOptions.genres.forEach(g => {
            genreDropdown.innerHTML += `<div class="filter-option" data-val="${g}">${g}</div>`;
        });

        // Prices
        priceDropdown.innerHTML = '';
        options.prices.forEach(p => {
            const activeClass = (p.min === 0 && p.max === -1) ? 'active' : '';
            priceDropdown.innerHTML += `<div class="filter-option ${activeClass}" data-min="${p.min}" data-max="${p.max}">${p.label}</div>`;
        });

        // Event delegation for options
        [genreDropdown, priceDropdown].forEach(dropdown => {
            dropdown.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevents parent sidebar item from toggling the menu back
                const opt = e.target.closest('.filter-option');
                if (!opt) return;

                if (dropdown === genreDropdown) {
                    const val = opt.dataset.val;
                    let genresList = (currentGenre === 'all' || currentGenre === '') ? [] : currentGenre.split(',');

                    if (val === 'all') {
                        genresList = [];
                        dropdown.querySelectorAll('.filter-option').forEach(o => o.classList.remove('active'));
                        opt.classList.add('active');
                    } else {
                        // Toggle selection
                        if (genresList.includes(val)) {
                            genresList = genresList.filter(g => g !== val);
                            opt.classList.remove('active');
                        } else {
                            genresList.push(val);
                            opt.classList.add('active');
                        }
                        
                        dropdown.querySelector('.filter-option[data-val="all"]').classList.remove('active');
                        
                        if (genresList.length === 0) {
                            dropdown.querySelector('.filter-option[data-val="all"]').classList.add('active');
                        }
                    }

                    currentGenre = genresList.length === 0 ? 'all' : genresList.join(',');
                    sideGenre.title = currentGenre === 'all' ? 'Filtrar por género' : `Géneros: ${genresList.join(', ')}`;
                } else {
                    const min = opt.dataset.min;
                    const max = opt.dataset.max;
                    const val = `${min}_${max}`;

                    let pricesList = (currentPrices === 'all' || currentPrices === '') ? [] : currentPrices.split(',');

                    if (min == 0 && max == -1) {
                        pricesList = [];
                        dropdown.querySelectorAll('.filter-option').forEach(o => o.classList.remove('active'));
                        opt.classList.add('active');
                    } else {
                        if (pricesList.includes(val)) {
                            pricesList = pricesList.filter(p => p !== val);
                            opt.classList.remove('active');
                        } else {
                            pricesList.push(val);
                            opt.classList.add('active');
                        }

                        dropdown.querySelector('.filter-option[data-min="0"][data-max="-1"]').classList.remove('active');

                        if (pricesList.length === 0) {
                            dropdown.querySelector('.filter-option[data-min="0"][data-max="-1"]').classList.add('active');
                        }
                    }

                    currentPrices = pricesList.length === 0 ? 'all' : pricesList.join(',');
                    
                    if (pricesList.length === 0) {
                        sidePrice.title = 'Filtrar por precio';
                    } else {
                        const activeLabels = Array.from(dropdown.querySelectorAll('.filter-option.active')).map(o => o.textContent);
                        sidePrice.title = `Precio: ${activeLabels.join(', ')}`;
                    }
                }

                triggerSearchGlow();
                currentPage = 1;
                fetchGames(true);
            });
        });

    } catch (err) {
        console.error("Error loading filter options:", err);
    }
}

function checkAndRestoreBg() {
    const grid = document.getElementById('game-grid');
    let keepBg = false;
    if (grid.classList.contains('single-result')) {
        keepBg = true;
    } else if (currentQuery) {
        const queryLower = currentQuery.toLowerCase().trim();
        const exactCard = Array.from(grid.querySelectorAll('.game-card')).find(c => c.dataset.name.toLowerCase() === queryLower);
        if (exactCard) {
            keepBg = true;
            const img = exactCard.querySelector('.game-card-banner');
            if (img && img.src) showHoverBg(img.src);
        }
    }

    if (!keepBg) {
        window._hoverBg.hideTimer = setTimeout(() => hideHoverBg(), 150);
    }
}

function showHoverBg(src) {
    const hb = window._hoverBg;
    if (!hb || src === hb.currentSrc) return;
    hb.currentSrc = src;
    const oldLayer = hb.layers[hb.activeLayer];
    hb.activeLayer = 1 - hb.activeLayer;
    const newLayer = hb.layers[hb.activeLayer];
    newLayer.style.backgroundImage = `url('${src}')`;
    newLayer.classList.add('active');
    oldLayer.classList.remove('active');
}

function hideHoverBg() {
    // Si estamos en la vista de juego, no ocultamos el fondo
    const viewGame = document.getElementById('view-game');
    if (viewGame && viewGame.classList.contains('active')) return;

    const hb = window._hoverBg;
    if (!hb) return;
    hb.currentSrc = null;
    hb.layers[0].classList.remove('active');
    hb.layers[1].classList.remove('active');
}

function setupInfiniteScroll() {
    const sentinel = document.getElementById('scroll-sentinel');
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !isLoading && hasMore) {
            currentPage++;
            fetchGames(false);
        }
    }, { rootMargin: '100px' });

    observer.observe(sentinel);
}

// ============================================================
// FETCH & RENDER GAME GRID
// ============================================================
async function fetchGames(reset = false) {
    if (isLoading) return;
    isLoading = true;

    const sentinel = document.getElementById('scroll-sentinel');
    const grid = document.getElementById('game-grid');

    if (reset) {
        grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        if (sentinel) sentinel.style.display = 'none';
        // Removed window.scrollTo to prevent jumping to top while typing
    } else if (sentinel && hasMore) {
        sentinel.style.display = 'flex';
    }

    const url = `/api/search?q=${encodeURIComponent(currentQuery)}&page=${currentPage}&limit=40&sort=${currentSort}&genre=${encodeURIComponent(currentGenre)}&prices=${encodeURIComponent(currentPrices)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        hasMore = data.has_more;
        renderGameGrid(data.games, reset);
    } catch (e) {
        console.error(e);
        if (reset) grid.innerHTML = '<div class="search-no-results">Error al cargar resultados</div>';
    } finally {
        isLoading = false;
        if (sentinel) {
            sentinel.style.display = hasMore ? 'flex' : 'none';
        }
    }
}

function renderGameGrid(games, reset) {
    const grid = document.getElementById('game-grid');

    if (reset) {
        if (!games.length) {
            grid.innerHTML = '<div class="search-no-results">Sin resultados</div>';
            hideHoverBg();
            return;
        }
        grid.innerHTML = '';
    }

    if (!games.length && !reset) return;

    let customCardHtml = '';
    // Mostrar la tarjeta especial solo si es un reset y no hay filtros activos
    if (reset && !currentQuery && currentGenre === 'all' && currentPrices === 'all' && currentSort === 'desc') {
        customCardHtml = `
            <div class="game-card custom-game-card">
                <div class="custom-card-banner">
                    <span class="custom-card-icon">?</span>
                </div>
                <div class="game-card-name">Añadir tu propio juego</div>
            </div>
        `;
    }

    const html = games.map(g => `
        <div class="game-card" data-appid="${g.appid}" data-name="${g.name}">
            <img class="game-card-banner" src="${g.banner_url}" alt="${g.name}" loading="lazy">
            <div class="game-card-name">${g.name}</div>
        </div>
    `).join('');

    grid.insertAdjacentHTML('beforeend', customCardHtml + html);

    // If exactly one result after a search reset, show its background and enlarge
    if (reset && games.length === 1 && !hasMore && games[0].banner_url) {
        showHoverBg(games[0].banner_url);
        grid.classList.add('single-result');
        const card = grid.querySelector('.game-card');
        if (card) card.classList.add('game-card-featured');
        lastFeaturedAppId = games[0].appid;
    } else if (reset) {
        grid.classList.remove('single-result');
        // CAMBIO DEL CÓDIGO ORIGINAL: lastFeaturedAppId = null;
        let foundExactMatch = false;
        if (currentQuery) {
            const queryLower = currentQuery.toLowerCase().trim();
            const exactMatch = games.find(g => g.name.toLowerCase() === queryLower);
            if (exactMatch && exactMatch.banner_url) {
                showHoverBg(exactMatch.banner_url);
                foundExactMatch = true;
                lastFeaturedAppId = exactMatch.appid;
            }
        }

        if (!foundExactMatch) {
            hideHoverBg();
        }
    }
}

// ============================================================
// TRENDING GAMES
// ============================================================
function loadTrendingGames() {
    currentQuery = '';
    currentPage = 1;
    hasMore = true;
    currentSort = 'desc';
    currentGenre = 'all';
    currentMinPrice = 0;
    currentMaxPrice = -1;
    lastFeaturedAppId = null;
    fetchGames(true);
}

// ============================================================
// GAME DETAIL VIEW
// ============================================================
async function navigateToGame(appid) {
    showView('view-game');

    const container = document.getElementById('game-detail-content');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    // Fetch game info
    const res = await fetch(`/api/game/${appid}`);
    const game = await res.json();
    currentGame = game;

    showHoverBg(game.banner_url);

    const positive = game.positive_reviews || 0;
    const negative = game.negative_reviews || 0;
    const totalReviews = positive + negative;

    // 1. Parseo limpio del array de géneros
    let parsedGenres = [];
    try {
        let rawGenres = [];
        if (typeof game.genres === 'string') {
            rawGenres = game.genres.split(',');
        } else if (Array.isArray(game.genres)) {
            rawGenres = game.genres;
        }
        
        parsedGenres = rawGenres
            .map(g => g.replace(/[\[\]'"]/g, '').trim())
            .filter(Boolean);
    } catch (e) { }
    if (!parsedGenres.length) parsedGenres = ['Unknown'];

    const safeGenres = parsedGenres.map(g => `<span class="glow-chip">${g}</span>`).join('');

    // --- Dynamic NLP Themes ---
    let nlpThemes = [];
    
    // Sort from best to worst
    nlpThemes.sort((a, b) => b.score - a.score);

    const nlpThemesHTML = nlpThemes.map(theme => {
        let colorClass = '';
        let labelText = '';
        if (theme.score >= 80) {
            colorClass = 'excellent';
            labelText = 'apartado excelente';
        } else if (theme.score >= 60) {
            colorClass = 'positive';
            labelText = 'apartado bueno';
        } else if (theme.score >= 40) {
            colorClass = 'mixed';
            labelText = 'apartado malo';
        } else {
            colorClass = 'negative';
            labelText = 'apartado pésimo';
        }
        
        const offset = (125.6 * (1 - theme.score / 100)).toFixed(2);
        
        // Calcular color rgb entre rojo (0%), amarillo (60%) y verde (100%)
        let r, g;
        if (theme.score <= 60) {
            r = 255;
            g = Math.round(255 * (theme.score / 60));
        } else {
            g = 255;
            r = Math.round(255 * (1 - (theme.score - 60) / 40));
        }
        
        return `
            <div class="nlp-theme-row" style="--tint-color: rgba(${r}, ${g}, 0, 0.05); --tint-hover: rgba(${r}, ${g}, 0, 0.12);">
                <div class="nlp-theme-text">
                    <span class="nlp-theme-name">${theme.name}</span>
                    <span class="nlp-theme-keywords">${theme.keywords}</span>
                </div>
                <div class="nlp-gauge-wrapper">
                    <span class="gauge-label ${colorClass}">${labelText}</span>
                    <div class="nlp-mini-gauge ${colorClass}">
                        <svg viewBox="0 0 100 50" class="gauge-svg"><path class="gauge-bg" d="M 10 50 A 40 40 0 0 1 90 50" /><path class="gauge-fill" d="M 10 50 A 40 40 0 0 1 90 50" style="stroke-dashoffset: ${offset};" /></svg>
                        <span class="gauge-score">${theme.score}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // 2. Inyección del nuevo HTML en el contenedor
    container.innerHTML = `
        <a href="https://store.steampowered.com/app/${game.appid}" target="_blank" class="game-hero-link" title="Ver en Steam">
            <div class="game-hero-section vision-glass">
                <div class="hero-left">
                    <img class="hero-banner console-transition" src="${game.banner_url}" alt="${game.name}">
                </div>
                <div class="hero-right">
                    <h1 class="hero-name">${game.name}</h1>
                    <p class="hero-desc">${game.short_description || 'Explora esta increíble experiencia que te mantendrá al borde de tu asiento.'}</p>
                    <div class="hero-genres">
                        ${safeGenres}
                    </div>
                </div>
                <div class="steam-float-icon">
                    <img src="/static/img/steam_icon.png" alt="Steam">
                </div>
            </div>
        </a>

        <div class="game-meta-grid">
            <div class="vision-glass meta-card">
                <div class="meta-label">Desarrollador</div>
                <div class="meta-value">${game.developer || 'Unknown Studio'}</div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Fecha de Lanzamiento</div>
                <div class="meta-value">${game.release_date || 'N/A'}</div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Precio Actual</div>
                <div class="meta-value">
                    ${game.discount_percent > 0 ? `
                        <div class="price-discount-wrapper">
                            <span class="price-old">${game.price_overview}€</span>
                            <div class="price-new-row">
                                <span class="price-new">${game.discount}</span>
                                <div class="discount-badge">-${game.discount_percent}%</div>
                            </div>
                        </div>
                    ` : `
                        ${game.price_overview === 0 || game.price_overview === '0' ? 'Gratis' : (game.price_overview + '€' || 'Unknown')}
                    `}
                </div>
            </div>
            <div class="vision-glass meta-card">
                <div class="meta-label">Reseñas en lanzamiento</div>
                <div class="meta-value">${formatNumber(game.total_reviews_at_launch) || '0'}</div>
            </div>
        </div>

        <div class="predictions-grid">
            <div class="predictions-row-top">
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Predicción de Popularidad</h3>
                    <div class="pred-value" id="pred-popularity-value">Cargando...</div>
                </div>
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Estimación de Precio</h3>
                    <div class="pred-value" id="pred-price-value">Cargando...</div>
                    <div class="market-label" id="pred-price-conclusion">Calculando...</div>
                </div>
            </div>
        <div class="vision-glass nlp-card">
            <h3 class="pred-title">RESUMEN DE RESEÑAS</h3>
            <div class="nlp-themes-list" id="nlp-themes-container">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
    </div>
    `;

    // Cargar predicción real de precio
    loadRealPricePrediction(game.appid, parsedGenres, game.price_overview);
    // Cargar predicción real de popularidad
    loadRealPopularityPrediction(game.appid);
    // Cargar predicción de topics
    loadRealTopicsPrediction(game.appid)
}

function navigateToCustomGame() {
    showView('view-custom-game');

    const container = document.getElementById('custom-game-detail-content');
    
    // Generar géneros desde filterOptions (global) con fallback al sidebar
    // Listas fijas en inglés según variables del modelo
    const GENRES_LIST = ['Action', 'Adventure', 'Casual', 'Early Access', 'Free To Play', 'Indie', 'RPG', 'Simulation', 'Strategy'];
    const CATEGORIES_LIST = ['Co-op', 'Custom Volume Controls', 'Family Sharing', 'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP', 'Partial Controller Support', 'Playable without Timed Input', 'PvP', 'Remote Play Together', 'Shared/Split Screen', 'Single-player', 'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards'];
    
    const genreOptionsHtml = GENRES_LIST
                           .map(g => `<div class="custom-selector-option" data-val="${g}">${g}</div>`)
                           .join('');

    const categoryOptionsHtml = CATEGORIES_LIST
                           .map(c => `<div class="custom-selector-option cat-option" data-val="${c}">${c}</div>`)
                           .join('');

    container.innerHTML = `
        <form id="custom-game-form" class="vision-glass" style="padding: 10px;">
            <div class="game-hero-section" style="background: transparent; border: none; box-shadow: none; backdrop-filter: none; margin-bottom: 20px;">
                <div class="hero-left" id="cg-hero-upload" style="cursor: pointer;" title="Haz clic para subir un banner">
                    <div class="hero-banner console-transition custom-hero-placeholder" id="cg-image-preview-container">
                        <span class="custom-hero-icon">?</span>
                    </div>
                    <input type="file" id="cg-image" accept="image/*" style="display:none;">
                </div>
                <div class="hero-right">
                    <input type="text" id="cg-name" class="hero-name-input" placeholder="Nombre del Juego" autocomplete="off">
                    <input type="text" id="cg-dev" class="hero-desc-input" placeholder="Nombre del Desarrollador" autocomplete="off">
                </div>
            </div>

            <div class="custom-form-panel" style="background: transparent; border: none; box-shadow: none; backdrop-filter: none; padding-top: 0; padding-bottom: 20px;">
                <div class="form-group-row">
                    <div class="form-group">
                        <label>Fecha de Lanzamiento</label>
                        <input type="date" id="cg-date" required class="custom-select-style" placeholder="MM/DD/YYYY">
                    </div>
                    <div class="form-group">
                        <label>Géneros</label>
                        <div class="custom-selector-wrapper">
                            <div class="custom-selector-trigger" id="cg-genres-trigger">
                                <div class="selected-tags-container" id="cg-selected-tags">
                                    <span style="color: rgba(255,255,255,0.4); font-weight: 300;">Seleccionar géneros...</span>
                                </div>
                                <span class="sidebar-icon-arrow" style="font-size: 0.8rem; transform: rotate(90deg);">↓</span>
                            </div>
                            <div class="custom-selector-dropdown" id="cg-genres-dropdown">
                                ${genreOptionsHtml}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="form-group-row" style="margin-top: 10px;">
                    <div class="form-group">
                        <label>Nº de idiomas soportados</label>
                        <input type="number" id="cg-languages" min="1" max="${filterOptions.max_languages}" value="1" class="custom-select-style default-val">
                    </div>
                    <div class="form-group">
                        <label>Categorías</label>
                        <div class="custom-selector-wrapper">
                            <div class="custom-selector-trigger" id="cg-categories-trigger">
                                <div class="selected-tags-container" id="cg-selected-cats">
                                    <span style="color: rgba(255,255,255,0.4); font-weight: 300;">Seleccionar categorías...</span>
                                </div>
                                <span class="sidebar-icon-arrow" style="font-size: 0.8rem; transform: rotate(90deg);">↓</span>
                            </div>
                            <div class="custom-selector-dropdown" id="cg-categories-dropdown">
                                ${categoryOptionsHtml}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECCIÓN YOUTUBE -->
                <div class="yt-search-section">
                    <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 10px;">
                        <button type="button" id="btn-search-yt" class="btn-predict-custom" style="padding: 6px 12px; margin: 0; font-size: 0.75rem;">Buscar vídeos</button>
                    </div>
                    <p style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-bottom: 10px;">Buscamos vídeos antes de la fecha de publicación. Selecciona los que quieras usar para la predicción. Se necesita el título del vídeo y la fecha de publicación para realizar la búsqueda.</p>
                    <div id="cg-yt-results" class="yt-videos-grid">
                        <!-- Los vídeos se inyectarán aquí -->
                    </div>
                </div>

                <button type="submit" class="btn-predict-custom" style="margin-top: 30px;">Predecir Popularidad y Precio</button>
            </div>
        </form>

        <div id="cg-predictions-result" class="predictions-grid" style="display: none; margin-top: 2rem;">
            <div class="predictions-row-top">
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Predicción de Popularidad</h3>
                    <div class="pred-value" id="cg-pred-popularity-value">...</div>
                </div>
                <div class="vision-glass pred-card">
                    <h3 class="pred-title">Estimación de Precio</h3>
                    <div class="pred-value" id="cg-pred-price-value">...</div>
                </div>
            </div>
        </div>

        <div class="custom-game-review-container vision-glass" style="margin-top: 2rem;">
            <h3 class="pred-title">Analizador de Reseñas</h3>
            <p style="color: rgba(255, 255, 255, 0.4); font-size: 1rem; font-weight: 300; margin-bottom: 1.5rem;">Escribe una reseña en INGLÉS y el modelo predecirá si es positiva o negativa.</p>
            <textarea id="cg-review-text" rows="4" placeholder="Escribe tu reseña aquí..." class="custom-select-style" style="resize: vertical; font-size: 1rem; font-weight: 300;"></textarea>
            <button id="btn-predict-review" class="btn-predict-custom" style="margin-top: 1rem; margin-bottom: 1rem;">Analizar Sentimiento</button>
            <div id="cg-review-result" style="display: none; font-size: 1.2rem; font-weight: 500; text-align: center; padding: 1rem; border-radius: var(--radius-md);"></div>
        </div>
    `;

    // --- Lógica de selectores (Cierre al hacer click fuera) ---
    const closeAllCustomDropdowns = () => {
        document.querySelectorAll('.custom-selector-dropdown').forEach(d => d.classList.remove('show'));
        document.querySelectorAll('.custom-selector-trigger').forEach(t => t.classList.remove('active'));
    };

    document.addEventListener('click', closeAllCustomDropdowns);

    // --- Lógica del selector de GÉNEROS (Multi-select) ---
    const gTrigger = document.getElementById('cg-genres-trigger');
    const gDropdown = document.getElementById('cg-genres-dropdown');
    const gTagsContainer = document.getElementById('cg-selected-tags');
    let selectedGenres = [];

    gTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasActive = gTrigger.classList.contains('active');
        closeAllCustomDropdowns();
        if (!wasActive) {
            gDropdown.classList.add('show');
            gTrigger.classList.add('active');
        }
    });

    gDropdown.querySelectorAll('.custom-selector-option').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const val = item.dataset.val;
            if (selectedGenres.includes(val)) {
                selectedGenres = selectedGenres.filter(g => g !== val);
                item.classList.remove('selected');
            } else {
                selectedGenres.push(val);
                item.classList.add('selected');
            }
            updateGenreTags();
        });
    });

    function updateGenreTags() {
        if (selectedGenres.length === 0) {
            gTagsContainer.innerHTML = '<span style="color: rgba(255,255,255,0.4); font-weight: 300;">Seleccionar géneros...</span>';
        } else {
            gTagsContainer.innerHTML = selectedGenres.map(g => `<span class="custom-tag-pill">${g}</span>`).join('');
        }
    }

    // --- Lógica del selector de CATEGORÍAS (Multi-select) ---
    const cTrigger = document.getElementById('cg-categories-trigger');
    const cDropdown = document.getElementById('cg-categories-dropdown');
    const cTagsContainer = document.getElementById('cg-selected-cats');
    let selectedCategories = [];

    cTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasActive = cTrigger.classList.contains('active');
        closeAllCustomDropdowns();
        if (!wasActive) {
            cDropdown.classList.add('show');
            cTrigger.classList.add('active');
        }
    });

    cDropdown.querySelectorAll('.custom-selector-option').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const val = item.dataset.val;
            if (selectedCategories.includes(val)) {
                selectedCategories = selectedCategories.filter(c => c !== val);
                item.classList.remove('selected');
            } else {
                selectedCategories.push(val);
                item.classList.add('selected');
            }
            updateCategoryTags();
        });
    });

    function updateCategoryTags() {
        if (selectedCategories.length === 0) {
            cTagsContainer.innerHTML = '<span style="color: rgba(255,255,255,0.4); font-weight: 300;">Seleccionar categorías...</span>';
        } else {
            cTagsContainer.innerHTML = selectedCategories.map(c => `<span class="custom-tag-pill">${c}</span>`).join('');
        }
    }

    // --- Lógica de Búsqueda en YouTube ---
    const btnSearchYt = document.getElementById('btn-search-yt');
    const ytResultsContainer = document.getElementById('cg-yt-results');
    let selectedVideos = []; // Almacenará los objetos de vídeo seleccionados

    btnSearchYt.addEventListener('click', async () => {
        const gameName = document.getElementById('cg-name').value.trim();
        const devName = document.getElementById('cg-dev').value.trim();
        const releaseDate = document.getElementById('cg-date').value;

        if (!gameName || !devName || !releaseDate) {
            showNotification('Por favor, introduce el nombre, desarrollador y fecha para buscar en YouTube.', 'error');
            return;
        }

        btnSearchYt.textContent = 'Buscando...';
        btnSearchYt.disabled = true;
        ytResultsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;"><div class="spinner" style="margin: auto;"></div></div>';

        try {
            const response = await fetch('/api/youtube/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: gameName, release_date: releaseDate })
            });

            const videos = await response.json();
            ytResultsContainer.innerHTML = '';
            selectedVideos = [];

            if (videos.length === 0) {
                ytResultsContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.4);">No se encontraron vídeos relevantes.</p>';
            } else {
                videos.forEach(video => {
                    const card = document.createElement('div');
                    card.className = 'yt-video-card';
                    card.innerHTML = `
                        <div class="yt-thumb-wrapper">
                            <img src="${video.thumbnail}" class="yt-thumb">
                            <a href="https://www.youtube.com/watch?v=${video.id}" target="_blank" class="yt-play-btn" onclick="event.stopPropagation()">▶</a>
                        </div>
                        <div class="yt-checkbox"></div>
                        <div class="yt-info">
                            <div class="yt-title" title="${video.video_title}">${video.video_title}</div>
                        </div>
                    `;
                    card.addEventListener('click', () => {
                        const isSelected = card.classList.toggle('selected');
                        if (isSelected) {
                            selectedVideos.push(video);
                        } else {
                            selectedVideos = selectedVideos.filter(v => v.id !== video.id);
                        }
                    });
                    ytResultsContainer.appendChild(card);
                });
            }
        } catch (error) {
            console.error('Error YouTube search:', error);
            ytResultsContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #ef4444;">Error al conectar con YouTube.</p>';
        } finally {
            btnSearchYt.textContent = 'Buscar vídeos';
            btnSearchYt.disabled = false;
        }
    });

    // --- Lógica de subida de imagen ---
    const heroUpload = document.getElementById('cg-hero-upload');
    const imageInput = document.getElementById('cg-image');
    const previewContainer = document.getElementById('cg-image-preview-container');
    let base64Image = null;

    heroUpload.addEventListener('click', () => {
        imageInput.click();
    });

    imageInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                base64Image = e.target.result;
                previewContainer.innerHTML = `<img src="${base64Image}" style="width: 100%; height: 100%; object-fit: cover; border-radius: inherit;">`;
                previewContainer.classList.remove('custom-hero-placeholder');
            }
            reader.readAsDataURL(file);
        }
    });

    // --- Lógica de fecha (Flatpickr) ---
    const dateInput = document.getElementById('cg-date');
    if (typeof flatpickr !== 'undefined') {
        flatpickr(dateInput, {
            dateFormat: "Y-m-d",
            altInput: true,
            altFormat: "F j, Y",
            placeholder: "MM/DD/YYYY",
            disableMobile: "true",
            onChange: (selectedDates, dateStr, instance) => {
                dateInput.classList.remove('default-val');
                // Al usar altInput, Flatpickr crea un input hermano que es el que se ve
                const altInput = instance.altInput;
                if (altInput) altInput.style.color = '#fff';
            }
        });
    }

    // --- Lógica de idiomas (Clamping) ---
    const langInput = document.getElementById('cg-languages');
    langInput.addEventListener('input', () => {
        langInput.classList.remove('default-val');
        const max = parseInt(langInput.max) || 74;
        if (langInput.value > max) langInput.value = max;
        if (langInput.value < 1 && langInput.value !== '') langInput.value = 1;
    });

    // --- Submit del formulario ---
    const form = document.getElementById('custom-game-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = form.querySelector('button[type="submit"]');
        
        // Validación manual de campos
        const nameVal = document.getElementById('cg-name').value.trim();
        const devVal = document.getElementById('cg-dev').value.trim();

        if (!nameVal) {
            showNotification('Por favor, introduce el nombre del juego.', 'error');
            return;
        }
        if (!devVal) {
            showNotification('Por favor, introduce el nombre del desarrollador.', 'error');
            return;
        }
        if (selectedGenres.length === 0) {
            showNotification('Por favor, selecciona al menos un género.', 'error');
            return;
        }
        if (selectedCategories.length === 0) {
            showNotification('Por favor, selecciona al menos una categoría.', 'error');
            return;
        }

        if (!base64Image) {
            showNotification('Por favor, sube una imagen de portada para el juego.', 'error');
            return;
        }

        btn.textContent = 'Calculando...';
        btn.disabled = true;

        const payload = {
            name: nameVal,
            developer: devVal,
            release_date: document.getElementById('cg-date').value,
            genres: selectedGenres,
            categories: selectedCategories,
            languages_count: parseInt(document.getElementById('cg-languages').value) || 1,
            image: base64Image,
            youtube_videos: selectedVideos // Enviamos los vídeos seleccionados
        };

        const resultDiv = document.getElementById('cg-predictions-result');
        resultDiv.style.display = 'block';
        document.getElementById('cg-pred-popularity-value').innerHTML = '<div class="spinner" style="width:20px;height:20px;margin:auto;"></div>';
        document.getElementById('cg-pred-price-value').innerHTML = '<div class="spinner" style="width:20px;height:20px;margin:auto;"></div>';

        try {
            const res = await fetch('/api/predict/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            document.getElementById('cg-pred-popularity-value').textContent = formatNumber(data.popularity) + ' Reseñas';
            document.getElementById('cg-pred-price-value').textContent = data.price;
            
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            console.error(err);
            document.getElementById('cg-pred-popularity-value').textContent = 'Error';
            document.getElementById('cg-pred-price-value').textContent = 'Error';
        } finally {
            btn.textContent = 'Predecir Popularidad y Precio';
            btn.disabled = false;
        }
    });

    const btnReview = document.getElementById('btn-predict-review');
    btnReview.addEventListener('click', async () => {
        const text = document.getElementById('cg-review-text').value.trim();
        if (!text) {
            showNotification('Por favor, escribe una reseña para analizar.', 'error');
            return;
        }

        btnReview.textContent = 'Analizando...';
        btnReview.disabled = true;

        const resultDiv = document.getElementById('cg-review-result');
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<div class="spinner" style="width:20px;height:20px;margin:auto;"></div>';
        resultDiv.className = '';

        try {
            const res = await fetch('/api/predict/reviews', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ review: text })
            });
            const data = await res.json();
            
            if (data.details.prediction) {
                    resultDiv.innerHTML = 'Reseña Positiva';
                resultDiv.style.backgroundColor = 'rgba(46, 204, 113, 0.1)';
                resultDiv.style.color = '#2ecc71';
                resultDiv.style.border = '1px solid rgba(46, 204, 113, 0.3)';
            } else {
                resultDiv.innerHTML = 'Reseña Negativa';
                resultDiv.style.backgroundColor = 'rgba(231, 76, 60, 0.1)';
                resultDiv.style.color = '#e74c3c';
                resultDiv.style.border = '1px solid rgba(231, 76, 60, 0.3)';
            }
        } catch (err) {
            console.error(err);
            resultDiv.innerHTML = 'Error al analizar la reseña';
            resultDiv.style.color = 'white';
        } finally {
            btnReview.textContent = 'Analizar Sentimiento';
            btnReview.disabled = false;
        }
    });
}

async function loadRealPricePrediction(appid, genres, currentPrice) {
    const priceValue = document.getElementById('pred-price-value');
    const conclusion = document.getElementById('pred-price-conclusion');
    if (!priceValue) return;

    const isFreeToPlay = genres.some(g => g.toLowerCase().includes('free to play'));
    if (isFreeToPlay) {
        priceValue.textContent = 'Gratis';
        if (conclusion) conclusion.textContent = 'Precio justo';
        return;
    }
    
    try {
        const res = await fetch(`/api/predict/precio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appid }),
        });
        const data = await res.json();
        const predicted = data.details.prediction;
        priceValue.textContent = predicted;

        if (conclusion) {
            const PRICE_ORDER = [
                'Entre 0.01€ y 4.99€', 
                'Entre 5.00€ y 9.99€', 
                'Entre 10.00€ y 14.99€', 
                'Entre 15.00€ y 19.99€', 
                'Entre 20.00€ y 29.99€', 
                'Entre 30.00€ y 39.99€', 
                'Más de 40€'
            ];
            const predictedIndex = PRICE_ORDER.indexOf(predicted);
            
            let realIndex = -1;
            const price = parseFloat(currentPrice);
            if (!isNaN(price)) {
                if      (price <= 4.99)  realIndex = 0;
                else if (price <= 9.99)  realIndex = 1;
                else if (price <= 14.99) realIndex = 2;
                else if (price <= 19.99) realIndex = 3;
                else if (price <= 29.99) realIndex = 4;
                else if (price <= 39.99) realIndex = 5;
                else                     realIndex = 6;
            }
            
            if (predictedIndex !== -1 && realIndex !== -1) {
                const diff = realIndex - predictedIndex;
                const labels = {
                     3: 'No tiene sentido comprar este juego a este precio',
                     2: 'Precio desorbitado',
                     1: 'Precio elevado',
                     0: 'Precio justo',
                    '-1': 'Precio asequible',
                    '-2': 'Precio bajo',
                    '-3': 'Este juego es una ganga',
                };
                conclusion.textContent = labels[Math.max(-3, Math.min(3, diff))] ?? '';
            } else {
                conclusion.style.display = 'none';
            }
        }
    } catch (e) {
        priceValue.textContent = 'Error';
        if (conclusion) conclusion.style.display = 'none';
    }
}

async function loadRealPopularityPrediction(appid) {
    const popValue = document.getElementById('pred-popularity-value');
    if (!popValue) return;
    
    try {
        const res = await fetch(`/api/predict/popularidad`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appid }),
        });
        const data = await res.json();
        popValue.textContent = formatNumber(data.details.prediction) + ' Reseñas';
    } catch (e) {
        popValue.textContent = 'Error';
    }
}

async function loadRealTopicsPrediction(appid) {
    const container = document.getElementById('nlp-themes-container');
    if (!container) return;

    const TOPIC_DISPLAY = {
        "Updates & Bugs":     { name: "Updates & Bugs",     keywords: "Parches, Errores, Actualizaciones" },
        "Action & Combat":    { name: "Action & Combat",    keywords: "Acción, Peleas, Mecánicas" },
        "Music & Atmosphere": { name: "Music & Atmosphere", keywords: "Música, Sonido, Ambiente" },
        "Story & Design":     { name: "Story & Design",     keywords: "Narrativa, Personajes, Diseño" },
        "Casual & Humor":     { name: "Casual & Humor",     keywords: "Casual, Divertido, Ligero" },
        "General Opinion":    { name: "General Opinion",    keywords: "General, Recomendación, Valoración" },
    };

    try {
        const res = await fetch('/api/predict/reviews/topics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appid }),
        });
        const data = await res.json();

        const themes = Object.entries(data.details.prediction).map(([key, ratio]) => {
            const score = Math.round(ratio * 100);
            const display = TOPIC_DISPLAY[key] ?? { name: key, keywords: '' };
            return { name: display.name, keywords: display.keywords, score };
        });

        themes.sort((a, b) => b.score - a.score);

        container.innerHTML = themes.map(theme => {
            let colorClass, labelText;
            if      (theme.score >= 80) { colorClass = 'excellent'; labelText = 'apartado excelente'; }
            else if (theme.score >= 60) { colorClass = 'positive';  labelText = 'apartado bueno'; }
            else if (theme.score >= 40) { colorClass = 'mixed';     labelText = 'apartado malo'; }
            else                        { colorClass = 'negative';  labelText = 'apartado pésimo'; }

            const offset = (125.6 * (1 - theme.score / 100)).toFixed(2);

            let r, g;
            if (theme.score <= 60) { r = 255; g = Math.round(255 * (theme.score / 60)); }
            else                   { g = 255; r = Math.round(255 * (1 - (theme.score - 60) / 40)); }

            return `
                <div class="nlp-theme-row" style="--tint-color: rgba(${r},${g},0,0.05); --tint-hover: rgba(${r},${g},0,0.12);">
                    <div class="nlp-theme-text">
                        <span class="nlp-theme-name">${theme.name}</span>
                        <span class="nlp-theme-keywords">${theme.keywords}</span>
                    </div>
                    <div class="nlp-gauge-wrapper">
                        <span class="gauge-label ${colorClass}">${labelText}</span>
                        <div class="nlp-mini-gauge ${colorClass}">
                            <svg viewBox="0 0 100 50" class="gauge-svg">
                                <path class="gauge-bg" d="M 10 50 A 40 40 0 0 1 90 50"/>
                                <path class="gauge-fill" d="M 10 50 A 40 40 0 0 1 90 50" style="stroke-dashoffset: ${offset};"/>
                            </svg>
                            <span class="gauge-score">${theme.score}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) {
        container.innerHTML = '<p style="color:rgba(255,255,255,0.4); text-align:center;">No se pudieron cargar los temas.</p>';
    }
}

async function requestPrediction(type, appid) {
    const resultsArea = document.getElementById('prediction-results-area');
    resultsArea.style.display = 'block';
    resultsArea.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    resultsArea.scrollIntoView({ behavior: 'smooth' });

    // Regla para juegos Free to Play
    if (type === 'precio' && currentGame) {
        let genres = [];
        if (typeof currentGame.genres === 'string') {
            genres = currentGame.genres.split(',').map(g => g.trim().toLowerCase());
        } else if (Array.isArray(currentGame.genres)) {
            genres = currentGame.genres.map(g => g.trim().toLowerCase());
        }
        
        if (genres.some(g => g.includes('free to play'))) {
            const prediction = { value: 'Gratis', confidence: 1.0, details: {} };
            currentPrediction = prediction;
            showPredictionView(type, prediction);
            return;
        }
    }

    const res = await fetch(`/api/predict/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appid: appid }),
    });
    const prediction = await res.json();
    currentPrediction = prediction;

    showPredictionView(type, prediction);
}

function showPredictionView(type, prediction) {
    document.getElementById('prediction-detail-content').innerHTML = `
        <div class="loading"><div class="spinner"></div></div>
    `;
    showView('view-prediction');
    renderPredictionDetail(type, prediction);
}

async function loadPrediction(type, appid) {
    const card = document.getElementById(`card-${type}`);

    // Si es predicción de precio y el juego es Free to Play
    if (type === 'precio' && currentGame) {
        let genres = [];
        if (typeof currentGame.genres === 'string') {
            genres = currentGame.genres.split(',').map(g => g.trim().toLowerCase());
        } else if (Array.isArray(currentGame.genres)) {
            genres = currentGame.genres.map(g => g.trim().toLowerCase());
        }
        
        if (genres.some(g => g.includes('free to play'))) {
            renderPredictionCard(card, type, { value: 'Gratis', confidence: 1.0 });
            return;
        }
    }

    const res = await fetch(`/api/predict/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appid: appid }),
    });
    const prediction = await res.json();

    renderPredictionCard(card, type, prediction);
}

function renderPredictionCard(card, type, prediction) {
    const config = {
        popularidad: {
            title: 'Popularidad',
            formatValue: (v) => formatNumber(v),
            label: 'Jugadores estimados',
            color: '#22d3ee',
        },
        precio: {
            title: 'Precio',
            formatValue: (v) => typeof v === 'number' ? v.toFixed(2) + '\u20ac' : v,
            label: 'Precio predicho',
            color: '#fbbf24',
        },
        reviews: {
            title: 'Rese\u00f1as',
            formatValue: (v) => (v * 100).toFixed(1) + '%',
            label: 'Ratio positivo predicho',
            color: '#34d399',
        },
    };

    const c = config[type];
    const chartId = `chart-${type}-mini`;

    card.innerHTML = `
        <div class="prediction-card-header">
            <span class="prediction-card-title">${c.title}</span>
        </div>
        <div class="prediction-card-value">${c.formatValue(prediction.value)}</div>
        <div class="prediction-card-label">${c.label}</div>
        <div class="prediction-card-confidence">
            <div class="confidence-bar-container">
                <div class="confidence-bar" style="width: ${prediction.confidence * 100}%"></div>
            </div>
            <span class="confidence-text">${(prediction.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="prediction-card-chart">
            <canvas id="${chartId}"></canvas>
        </div>
        <div class="prediction-card-footer">
            <span class="prediction-card-model">${prediction.model_used}</span>
            <span class="view-detail-btn">Ver detalle</span>
        </div>
    `;

    renderMiniChart(chartId, prediction.details.history, c.color);

    card.addEventListener('click', () => {
        navigateToPredictionDetail(type, prediction);
    });
}

// ============================================================
// PREDICTION DETAIL VIEW
// ============================================================
function navigateToPredictionDetail(type, prediction) {
    showView('view-prediction');
    currentPrediction = { type, data: prediction };

    const container = document.getElementById('prediction-detail-content');
    const config = {
        popularidad: {
            title: 'Popularidad', formatValue: (v) => formatNumber(v),
            unit: 'Jugadores estimados', colorClass: 'popularidad',
        },
        precio: {
            title: 'Precio', formatValue: (v) => typeof v === 'number' ? v.toFixed(2) + '€' : v,
            unit: 'Precio predicho', colorClass: 'precio',
        },
        reviews: {
            title: 'Reseñas', formatValue: (v) => (v * 100).toFixed(1) + '%',
            unit: 'Ratio de reseñas positivas', colorClass: 'reviews',
        },
    };
    const c = config[type];

    let extraPanels = '';

    if (type === 'popularidad' && prediction.details.feature_importance) {
        const features = prediction.details.feature_importance;
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Importancia de caracteristicas</h3>
                <div class="feature-list">
                    ${Object.entries(features).map(([name, val]) => `
                        <div class="feature-item">
                            <span class="feature-name">${formatFeatureName(name)}</span>
                            <div class="feature-bar-container">
                                <div class="feature-bar" style="width: ${val * 100}%"></div>
                            </div>
                            <span class="feature-value">${(val * 100).toFixed(0)}%</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    if (type === 'precio' && prediction.details.price_range) {
        const range = prediction.details.price_range;
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Rango de precios</h3>
                <div class="price-range">
                    <div>
                        <div class="price-range-value" style="color:var(--accent-red)">${range.min}€</div>
                        <div class="price-range-label">Mínimo</div>
                    </div>
                    <div class="price-range-bar"><div class="price-range-fill"></div></div>
                    <div>
                        <div class="price-range-value" style="color:var(--accent-green)">${range.max}€</div>
                        <div class="price-range-label">Máximo</div>
                    </div>
                </div>
            </div>
        `;
    }

    if (type === 'reviews' && prediction.details.sentiment_distribution) {
        const sentiments = prediction.details.sentiment_distribution;
        const sentimentColors = {
            very_positive: '#22c55e',
            positive: '#34d399',
            mixed: '#fbbf24',
            negative: '#f87171',
            very_negative: '#ef4444',
        };
        const sentimentLabels = {
            very_positive: 'Muy positivo',
            positive: 'Positivo',
            mixed: 'Mixto',
            negative: 'Negativo',
            very_negative: 'Muy negativo',
        };
        extraPanels += `
            <div class="detail-panel">
                <h3 class="detail-panel-title">Distribucion de sentimiento</h3>
                <div class="sentiment-list">
                    ${Object.entries(sentiments).map(([key, val]) => `
                        <div class="sentiment-item">
                            <div class="sentiment-dot" style="background:${sentimentColors[key]}"></div>
                            <span class="sentiment-name">${sentimentLabels[key]}</span>
                            <span class="sentiment-value">${(val * 100).toFixed(1)}%</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="prediction-detail-header">
            <img class="prediction-detail-game-img" src="${currentGame.banner_url}" alt="${currentGame.name}">
            <div class="prediction-detail-main">
                <div class="prediction-detail-type ${c.colorClass}">${c.title}</div>
                <div class="prediction-detail-value">${c.formatValue(prediction.value)}</div>
                <div class="prediction-detail-unit">${c.unit} — ${currentGame.name}</div>
                <div class="prediction-detail-confidence">
                    <span class="prediction-detail-confidence-label">Confianza del modelo:</span>
                    <span class="prediction-detail-confidence-value" style="color:var(--accent-${type === 'popularidad' ? 'cyan' : type === 'precio' ? 'gold' : 'green'})">${(prediction.confidence * 100).toFixed(1)}%</span>
                    <span class="prediction-detail-confidence-label">·</span>
                    <span class="prediction-detail-confidence-label">Modelo: ${prediction.model_used}</span>
                </div>
            </div>
        </div>

        <div class="detail-panels">
            <div class="detail-panel">
                <h3 class="detail-panel-title">Evolucion historica</h3>
                <div class="detail-chart-container">
                    <canvas id="chart-detail-history"></canvas>
                </div>
            </div>
            ${extraPanels}
        </div>
    `;

    const colors = { popularidad: '#22d3ee', precio: '#fbbf24', reviews: '#34d399' };
    renderDetailChart('chart-detail-history', prediction.details.history, colors[type]);
}

// ============================================================
// CHARTS (Chart.js)
// ============================================================
function renderMiniChart(canvasId, history, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (charts[canvasId]) charts[canvasId].destroy();

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 100);
    gradient.addColorStop(0, color + '33');
    gradient.addColorStop(1, 'transparent');

    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(h => h.month),
            datasets: [{
                data: history.map(h => h.value),
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { display: false },
            },
        },
    });
}

function renderDetailChart(canvasId, history, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (charts[canvasId]) charts[canvasId].destroy();

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, color + '40');
    gradient.addColorStop(1, 'transparent');

    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(h => h.month),
            datasets: [{
                label: 'Valor',
                data: history.map(h => h.value),
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 2.5,
                pointRadius: 4,
                pointBackgroundColor: color,
                pointHoverRadius: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15,23,42,0.9)',
                    borderColor: color,
                    borderWidth: 1,
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                },
            },
        },
    });
}

// ============================================================
// HELPERS
// ============================================================
function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function formatFeatureName(name) {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// ============================================================
// BACKGROUND ANIMATION — Floating figures
// ============================================================
function initBackground() {
    const container = document.getElementById('bg-figures');
    if (!container) return;

    const CONFIG = {
        IMG_SRC: '/static/img/figura.png',
        NUM_COLUMNS: 14,
        COL_WIDTH: 400,
        OVERLAP_OFFSET: -14,
        OVERLAP_END: 200,
        SCALE_MIN: 1.0,
        SCALE_MAX: 1.5,
        OPACITY_MIN: 0.22,
        OPACITY_MAX: 0.3,
        DUR_MIN: 40,
        DUR_MAX: 70,
        SWAY_MAX_PX: 50,
        SWAY_DUR_MIN: 8,
        SWAY_DUR_MAX: 15,
        BLUR_PX: 2,
    };

    const range = CONFIG.OVERLAP_END - CONFIG.OVERLAP_OFFSET;

    for (let i = 0; i < CONFIG.NUM_COLUMNS; i++) {
        const col = document.createElement('div');
        col.className = 'bg-chain-col';
        col.style.width = `${CONFIG.COL_WIDTH}px`;

        const goesUp = (i % 2 === 0);
        col.classList.add(goesUp ? 'up' : 'down');

        const leftPct = CONFIG.OVERLAP_OFFSET + (i / (CONFIG.NUM_COLUMNS - 1)) * range;
        col.style.left = `${leftPct}%`;

        const scale = CONFIG.SCALE_MIN + Math.random() * (CONFIG.SCALE_MAX - CONFIG.SCALE_MIN);
        col.style.transform = `scale(${scale})`;
        col.style.opacity = (CONFIG.OPACITY_MIN + Math.random() * (CONFIG.OPACITY_MAX - CONFIG.OPACITY_MIN)).toString();

        const sway = document.createElement('div');
        sway.className = 'bg-chain-sway';
        const swayAmount = Math.random() * CONFIG.SWAY_MAX_PX;
        const swayDur = CONFIG.SWAY_DUR_MIN + Math.random() * (CONFIG.SWAY_DUR_MAX - CONFIG.SWAY_DUR_MIN);
        sway.style.setProperty('--sway-amount', swayAmount);
        sway.style.setProperty('--sway-dur', `${swayDur}s`);
        sway.style.animationDelay = `-${Math.random() * swayDur}s`;

        const track = document.createElement('div');
        track.className = 'bg-chain-track';

        const durY = CONFIG.DUR_MIN + Math.random() * (CONFIG.DUR_MAX - CONFIG.DUR_MIN);
        track.style.animationDuration = `${durY}s`;

        const delayY = -(Math.random() * durY);
        track.style.animationDelay = `${delayY}s`;

        for (let j = 0; j < 3; j++) {
            const img = document.createElement('img');
            img.src = CONFIG.IMG_SRC;
            img.className = 'bg-chain-img';
            img.alt = '';
            img.draggable = false;
            track.appendChild(img);
        }

        sway.appendChild(track);
        col.appendChild(sway);
        container.appendChild(col);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadTrendingGames();
    setupSearch();
    setupNavigation();
    initBackground();
    initNoise();
    setupSidebarVisibility();
});

function setupSidebarVisibility() {
    const sidebar = document.querySelector('.sidebar-filters');
    const target = document.querySelector('.search-container');
    
    if (!sidebar || !target) return;

    const updateVisibility = () => {
        const rect = target.getBoundingClientRect();
        // Show 400px after the search container starts entering the viewport
        if (rect.top < (window.innerHeight * 0.9 - 400)) {
            sidebar.classList.remove('hidden');
        } else {
            sidebar.classList.add('hidden');
        }
    };

    window.addEventListener('scroll', updateVisibility);
    updateVisibility();
}

let sidebarSortRotation = 0;
function updateSidebarSortIcon() {
    const arrow = document.querySelector('.sidebar-icon-arrow');
    if (!arrow) return;
    sidebarSortRotation += 180;
    arrow.style.transform = `rotate(${sidebarSortRotation}deg)`;
}

// ============================================================
// NOISE GRAIN
// ============================================================
function initNoise() {
    const el = document.getElementById('bg-noise');
    if (!el) return;

    const SIZE = 150;
    const c = document.createElement('canvas');
    c.width = SIZE;
    c.height = SIZE;

    const ctx = c.getContext('2d');
    const img = ctx.createImageData(SIZE, SIZE);
    const data = img.data;

    for (let i = 0; i < data.length; i += 4) {
        const v = Math.floor(Math.random() * 256);
        data[i] = v;
        data[i + 1] = v;
        data[i + 2] = v;
        data[i + 3] = 255;
    }

    ctx.putImageData(img, 0, 0);
    el.style.backgroundImage = `url('${c.toDataURL()}')`;
}

/* ============================================================
   LÓGICA JS PARA EL VÍDEO HERO SCROLLYTELLING (VANILLA JS)
   ============================================================ */

const canvas = document.getElementById('hero-canvas');
const ctx = canvas.getContext('2d');
const echoCanvas = document.getElementById('hero-echo-canvas');
const echoCtx = echoCanvas.getContext('2d');

const frameCount = 192;
const currentFrame = index => `/static/img/frames/header${String(86399 + index).padStart(8, '0')}.jpg`;

const images = [];
const heroSequence = { frame: 0 };

const initCanvas = () => {
    if (canvas.width !== images[0].width) {
        canvas.width = images[0].width;
        canvas.height = images[0].height;
    }
    ctx.drawImage(images[0], 0, 0);
};

for (let i = 1; i <= frameCount; i++) {
    const img = new Image();

    if (i === 1) {
        img.onload = initCanvas;
    }

    img.src = currentFrame(i);
    images.push(img);

    if (i === 1 && img.complete) {
        initCanvas();
    }
}

const updateCanvas = () => {
    const scrollTop = document.documentElement.scrollTop;
    const heroScrollContainer = document.getElementById('hero-scroll-container');
    const maxScroll = heroScrollContainer.scrollHeight - window.innerHeight;
    const scrollFraction = scrollTop / maxScroll;
    const frameIndex = Math.min(frameCount - 1, Math.floor(scrollFraction * frameCount));
    if (images[frameIndex]) {
        requestAnimationFrame(() => {
            ctx.drawImage(images[frameIndex], 0, 0);
            const img = images[frameIndex];
            const ew = echoCanvas.clientWidth, eh = echoCanvas.clientHeight;
            if (echoCanvas.width !== ew) echoCanvas.width = ew;
            if (echoCanvas.height !== eh) echoCanvas.height = eh;
            const es = Math.max(ew / img.naturalWidth, eh / img.naturalHeight);
            echoCtx.drawImage(img, (ew - img.naturalWidth * es) / 2, eh - img.naturalHeight * es, img.naturalWidth * es, img.naturalHeight * es);
        });
    }
};

window.addEventListener('scroll', updateCanvas);

let topIdleTimer = null;
let scrollIndicatorVisible = false;
let showScrollY = 0;

const refreshScrollIndicator = () => {
    if (topIdleTimer) clearTimeout(topIdleTimer);
    
    const indicator = document.getElementById('scroll-indicator');
    if (!indicator) return;

    // If we are at the top, start the 1s idle timer
    if (window.scrollY < 10) {
        if (!isAutoScrolling && !scrollIndicatorVisible) {
            topIdleTimer = setTimeout(() => {
                if (window.scrollY < 10 && !isAutoScrolling) {
                    indicator.classList.add('visible');
                    scrollIndicatorVisible = true;
                }
            }, 1000);
        }
    } else {
        // If we are far from the top, hide it if we move away from the point it was shown
        if (scrollIndicatorVisible && Math.abs(window.scrollY - showScrollY) > 20) {
            indicator.classList.remove('visible');
            scrollIndicatorVisible = false;
        }
    }
};

window.addEventListener('scroll', refreshScrollIndicator);
window.addEventListener('wheel', refreshScrollIndicator);
window.addEventListener('touchstart', refreshScrollIndicator);
window.addEventListener('mousedown', refreshScrollIndicator);
window.addEventListener('keydown', refreshScrollIndicator);

let isAutoScrolling = true;
const pixelsPerFrame = 20;
const cinematicAutoPlay = () => {
    if (!isAutoScrolling) return;

    const heroScrollContainer = document.getElementById('hero-scroll-container');
    const maxScroll = heroScrollContainer.scrollHeight - window.innerHeight;

    if (maxScroll <= 0) {
        // Layout not ready yet, retry
        requestAnimationFrame(cinematicAutoPlay);
        return;
    }

    window.scrollBy(0, pixelsPerFrame);

    if (window.scrollY >= maxScroll) {
        isAutoScrolling = false;
        showScrollIndicator();
        return;
    }

    requestAnimationFrame(cinematicAutoPlay);
};

function showScrollIndicator() {
    const indicator = document.getElementById('scroll-indicator');
    if (indicator) {
        indicator.classList.add('visible');
        scrollIndicatorVisible = true;
        showScrollY = window.scrollY;
    }
}

window.addEventListener('load', () => {
    // Reset scroll position on reload to avoid stuck state
    window.scrollTo(0, 0);
    // Wait a tick for layout to settle, then start
    setTimeout(() => {
        refreshScrollIndicator();
        if (images[0] && images[0].complete) {
            requestAnimationFrame(cinematicAutoPlay);
        } else {
            images[0].addEventListener('load', () => {
                requestAnimationFrame(cinematicAutoPlay);
            });
        }
    }, 100);
});

const stopAutoScroll = () => {
    if (isAutoScrolling) {
        isAutoScrolling = false;
        // Check if we show it immediately or wait for idle
        if (window.scrollY < 10) {
            refreshScrollIndicator(); 
        } else {
            showScrollIndicator();
        }
    }
};

window.addEventListener('wheel', stopAutoScroll);
window.addEventListener('touchstart', stopAutoScroll);
window.addEventListener('mousedown', stopAutoScroll);
window.addEventListener('keydown', stopAutoScroll);