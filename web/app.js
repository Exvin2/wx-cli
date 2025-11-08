// wx - Ultra-Modern Weather Intelligence UI
// Built with vanilla JavaScript + all the best practices

const API_BASE = window.location.origin + '/api';

// State management
const state = {
    currentLocation: null,
    currentStory: null,
    theme: localStorage.getItem('wx-theme') || 'light',
    favorites: JSON.parse(localStorage.getItem('wx-favorites') || '[]'),
    recentSearches: JSON.parse(localStorage.getItem('wx-recent') || '[]'),
};

// DOM Elements
const elements = {
    locationInput: document.getElementById('locationInput'),
    searchBtn: document.getElementById('searchBtn'),
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    errorMessage: document.getElementById('errorMessage'),
    retryBtn: document.getElementById('retryBtn'),
    story: document.getElementById('story'),
    themeToggle: document.getElementById('themeToggle'),
    geoBtn: document.getElementById('geoBtn'),
    favoriteBtn: document.getElementById('favoriteBtn'),
    shareBtn: document.getElementById('shareBtn'),
    clearInput: document.getElementById('clearInput'),
    bgAnimated: document.getElementById('bgAnimated'),
};

// Initialize app
function init() {
    applyTheme(state.theme);
    setupEventListeners();
    loadFavorites();
    loadRecentSearches();
    setupKeyboardShortcuts();
    setupScrollReveal();

    // Load initial story if URL has location
    const urlParams = new URLSearchParams(window.location.search);
    const location = urlParams.get('location');
    if (location) {
        elements.locationInput.value = location;
        fetchWeatherStory();
    }
}

// Event listeners
function setupEventListeners() {
    elements.searchBtn.addEventListener('click', fetchWeatherStory);
    elements.locationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchWeatherStory();
    });
    elements.locationInput.addEventListener('input', handleInputChange);
    elements.themeToggle.addEventListener('click', toggleTheme);
    elements.geoBtn.addEventListener('click', useGeolocation);
    elements.retryBtn.addEventListener('click', fetchWeatherStory);
    elements.clearInput.addEventListener('click', clearInput);
    elements.favoriteBtn.addEventListener('click', () => toggleFavorite());
    elements.shareBtn.addEventListener('click', shareStory);
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+K or Cmd+K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            elements.locationInput.focus();
        }

        // Escape to clear
        if (e.key === 'Escape') {
            clearInput();
        }
    });
}

// Scroll reveal animation
function setupScrollReveal() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.scroll-reveal').forEach(el => observer.observe(el));
}

// Input handling
function handleInputChange(e) {
    const value = e.target.value;
    elements.clearInput.classList.toggle('hidden', !value);
}

function clearInput() {
    elements.locationInput.value = '';
    elements.clearInput.classList.add('hidden');
    elements.locationInput.focus();
}

// Theme management
function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    applyTheme(state.theme);
    localStorage.setItem('wx-theme', state.theme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
}

// Geolocation
async function useGeolocation() {
    if (!navigator.geolocation) {
        showError('Geolocation is not supported by your browser');
        return;
    }

    elements.geoBtn.innerHTML = '<span class="animate-spin">🌍</span>';

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;

            // Reverse geocode to get location name
            try {
                const response = await fetch(
                    `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`
                );
                const data = await response.json();
                const locationName = data.address.city || data.address.town || data.address.village || 'Current Location';

                elements.locationInput.value = locationName;
                fetchWeatherStory();
            } catch (err) {
                elements.locationInput.value = `${latitude.toFixed(2)},${longitude.toFixed(2)}`;
                fetchWeatherStory();
            } finally {
                elements.geoBtn.innerHTML = '<span class="text-xl">📍</span>';
            }
        },
        (error) => {
            showError('Could not get your location. Please check permissions.');
            elements.geoBtn.innerHTML = '<span class="text-xl">📍</span>';
        }
    );
}

// Fetch weather story
async function fetchWeatherStory() {
    const location = elements.locationInput.value.trim();
    if (!location) {
        elements.locationInput.focus();
        return;
    }

    // Update URL
    const url = new URL(window.location);
    url.searchParams.set('location', location);
    window.history.pushState({}, '', url);

    // Save to recent searches
    addToRecentSearches(location);

    // Show loading
    hideAllSections();
    elements.loading.classList.remove('hidden');

    try {
        const [storyResponse, alertsResponse] = await Promise.all([
            fetch(`${API_BASE}/story?location=${encodeURIComponent(location)}`),
            fetch(`${API_BASE}/alerts?location=${encodeURIComponent(location)}`)
        ]);

        if (!storyResponse.ok) {
            throw new Error(`API error: ${storyResponse.statusText}`);
        }

        const story = await storyResponse.json();
        const alertsData = await alertsResponse.json();

        state.currentLocation = location;
        state.currentStory = story;

        displayStory(story, alertsData);
        updateBackgroundForWeather(story);

    } catch (err) {
        showError(err.message);
    } finally {
        elements.loading.classList.add('hidden');
    }
}

// Display weather story
function displayStory(story, alertsData) {
    // Location header
    const locationEl = document.getElementById('storyLocation');
    locationEl.textContent = state.currentLocation;

    // Time
    const timeEl = document.getElementById('storyTime');
    timeEl.textContent = new Date().toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    // Story content
    document.getElementById('setup').textContent = story.setup;
    document.getElementById('current').textContent = story.current;
    document.getElementById('meteorology').textContent = story.meteorology;
    document.getElementById('bottomLine').textContent = story.bottom_line;

    // Timeline
    renderTimeline(story.evolution);

    // Decisions
    renderDecisions(story.decisions);

    // Alerts
    renderAlerts(alertsData);

    // Favorite button state
    updateFavoriteButton();

    // Show story
    hideAllSections();
    elements.story.classList.remove('hidden');

    // Trigger scroll reveal
    setTimeout(() => {
        setupScrollReveal();
    }, 100);
}

// Render timeline
function renderTimeline(evolution) {
    const timeline = document.getElementById('timeline');
    timeline.innerHTML = '';

    if (!evolution || !evolution.phases || evolution.phases.length === 0) {
        document.getElementById('timelineSection').classList.add('hidden');
        return;
    }

    document.getElementById('timelineSection').classList.remove('hidden');

    evolution.phases.forEach((phase, index) => {
        const isLast = index === evolution.phases.length - 1;

        const phaseEl = document.createElement('div');
        phaseEl.className = 'timeline-item';
        phaseEl.innerHTML = `
            <div class="timeline-dot"></div>
            <div class="glass rounded-lg p-4">
                <div class="flex justify-between items-start mb-3">
                    <div class="flex-1">
                        <p class="font-bold text-lg">${phase.start_time} – ${phase.end_time}</p>
                        <p class="text-secondary mt-2">${phase.description}</p>
                    </div>
                </div>
                ${phase.key_changes && phase.key_changes.length > 0 ? `
                    <div class="mt-3 space-y-1">
                        ${phase.key_changes.map(change => `
                            <div class="flex items-start gap-2">
                                <span class="text-blue-500 mt-1">•</span>
                                <span class="text-sm text-secondary">${change}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                <div class="mt-3">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-xs text-muted">Confidence</span>
                        <span class="text-xs font-medium">${Math.round(phase.confidence * 100)}%</span>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${phase.confidence * 100}%"></div>
                    </div>
                </div>
            </div>
        `;
        timeline.appendChild(phaseEl);
    });
}

// Render decisions
function renderDecisions(decisions) {
    const decisionsEl = document.getElementById('decisions');
    decisionsEl.innerHTML = '';

    if (!decisions || decisions.length === 0) {
        document.getElementById('decisionsSection').classList.add('hidden');
        return;
    }

    document.getElementById('decisionsSection').classList.remove('hidden');

    decisions.forEach(decision => {
        const decisionEl = document.createElement('div');
        decisionEl.className = 'glass rounded-xl p-5 card-interactive';
        decisionEl.innerHTML = `
            <div class="flex items-start gap-3 mb-3">
                <span class="text-2xl">${getActivityEmoji(decision.activity)}</span>
                <div class="flex-1">
                    <p class="font-bold text-lg">${decision.activity}</p>
                </div>
            </div>
            <div class="space-y-2">
                <p class="font-medium">→ ${decision.recommendation}</p>
                <p class="text-sm text-secondary">💭 ${decision.reasoning}</p>
                ${decision.timing ? `<p class="text-sm text-muted">⏰ ${decision.timing}</p>` : ''}
            </div>
            <div class="mt-4">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-xs text-muted">Confidence</span>
                    <span class="text-xs font-medium">${Math.round(decision.confidence * 100)}%</span>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${decision.confidence * 100}%"></div>
                </div>
            </div>
        `;
        decisionsEl.appendChild(decisionEl);
    });
}

// Render alerts
function renderAlerts(alertsData) {
    const alertsContainer = document.getElementById('alertsContainer');
    const alertsList = document.getElementById('alertsList');

    if (!alertsData || !alertsData.alerts || alertsData.count === 0) {
        alertsContainer.classList.add('hidden');
        return;
    }

    alertsList.innerHTML = '';
    alertsData.alerts.forEach(alert => {
        const alertEl = document.createElement('div');
        alertEl.className = 'glass rounded-lg p-4';
        alertEl.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <p class="font-bold text-lg">${alert.event}</p>
                <span class="px-3 py-1 rounded-full text-xs font-medium bg-red-500 text-white">
                    ${alert.severity}
                </span>
            </div>
            <p class="text-secondary mb-2">${alert.description}</p>
            ${alert.areas && alert.areas.length > 0 ? `
                <p class="text-sm text-muted">📍 ${alert.areas.join(', ')}</p>
            ` : ''}
        `;
        alertsList.appendChild(alertEl);
    });

    alertsContainer.classList.remove('hidden');
}

// Update background based on weather
function updateBackgroundForWeather(story) {
    const current = story.current.toLowerCase();
    let gradient;

    if (current.includes('rain') || current.includes('shower')) {
        gradient = 'var(--rainy-gradient)';
    } else if (current.includes('storm') || current.includes('thunder')) {
        gradient = 'var(--stormy-gradient)';
    } else if (current.includes('cloud')) {
        gradient = 'var(--cloudy-gradient)';
    } else if (current.includes('snow')) {
        gradient = 'var(--snowy-gradient)';
    } else if (current.includes('sun') || current.includes('clear')) {
        gradient = 'var(--sunny-gradient)';
    } else {
        gradient = 'var(--clear-gradient)';
    }

    elements.bgAnimated.style.background = gradient;
}

// Favorites management
function addToRecentSearches(location) {
    state.recentSearches = state.recentSearches.filter(l => l !== location);
    state.recentSearches.unshift(location);
    state.recentSearches = state.recentSearches.slice(0, 5);
    localStorage.setItem('wx-recent', JSON.stringify(state.recentSearches));
    loadRecentSearches();
}

function loadRecentSearches() {
    const recentsContainer = document.getElementById('recentsContainer');
    const recentsList = document.getElementById('recentsList');

    if (state.recentSearches.length === 0) {
        recentsContainer.classList.add('hidden');
        return;
    }

    recentsList.innerHTML = '';
    state.recentSearches.forEach(location => {
        const chip = createLocationChip(location, () => {
            elements.locationInput.value = location;
            fetchWeatherStory();
        });
        recentsList.appendChild(chip);
    });

    recentsContainer.classList.remove('hidden');
}

function loadFavorites() {
    const favoritesContainer = document.getElementById('favoritesContainer');
    const favoritesList = document.getElementById('favoritesList');

    if (state.favorites.length === 0) {
        favoritesContainer.classList.add('hidden');
        return;
    }

    favoritesList.innerHTML = '';
    state.favorites.forEach(location => {
        const chip = createLocationChip(location, () => {
            elements.locationInput.value = location;
            fetchWeatherStory();
        }, true);
        favoritesList.appendChild(chip);
    });

    favoritesContainer.classList.remove('hidden');
}

function createLocationChip(location, onClick, showRemove = false) {
    const chip = document.createElement('button');
    chip.className = 'px-4 py-2 glass rounded-lg text-sm hover:scale-105 transition flex items-center gap-2';
    chip.innerHTML = `
        <span>${location}</span>
        ${showRemove ? '<span class="text-xs opacity-50 hover:opacity-100">✕</span>' : ''}
    `;

    chip.addEventListener('click', (e) => {
        if (showRemove && e.target.tagName === 'SPAN' && e.target.textContent === '✕') {
            toggleFavorite(location);
        } else {
            onClick();
        }
    });

    return chip;
}

function toggleFavorite(location = state.currentLocation) {
    if (!location) return;

    const index = state.favorites.indexOf(location);
    if (index > -1) {
        state.favorites.splice(index, 1);
    } else {
        state.favorites.push(location);
    }

    localStorage.setItem('wx-favorites', JSON.stringify(state.favorites));
    loadFavorites();
    updateFavoriteButton();
}

function updateFavoriteButton() {
    if (!state.currentLocation) return;

    const isFavorite = state.favorites.includes(state.currentLocation);
    elements.favoriteBtn.textContent = isFavorite ? '★' : '☆';
    elements.favoriteBtn.classList.toggle('active', isFavorite);
}

// Share functionality
async function shareStory() {
    const url = window.location.href;
    const text = `Check out the weather story for ${state.currentLocation}!`;

    if (navigator.share) {
        try {
            await navigator.share({ title: 'wx Weather Story', text, url });
        } catch (err) {
            copyToClipboard(url);
        }
    } else {
        copyToClipboard(url);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = elements.shareBtn.textContent;
        elements.shareBtn.textContent = 'Link copied! ✓';
        setTimeout(() => {
            elements.shareBtn.textContent = originalText;
        }, 2000);
    });
}

// UI helpers
function hideAllSections() {
    elements.loading.classList.add('hidden');
    elements.error.classList.add('hidden');
    elements.story.classList.add('hidden');
}

function showError(message) {
    hideAllSections();
    elements.errorMessage.textContent = message;
    elements.error.classList.remove('hidden');
}

function getActivityEmoji(activity) {
    const lower = activity.toLowerCase();
    if (lower.includes('outdoor') || lower.includes('hik')) return '🌳';
    if (lower.includes('commut') || lower.includes('driv')) return '🚗';
    if (lower.includes('run') || lower.includes('jog')) return '🏃';
    if (lower.includes('flight') || lower.includes('fly') || lower.includes('aviation')) return '✈️';
    if (lower.includes('bike') || lower.includes('cycl')) return '🚴';
    if (lower.includes('walk')) return '🚶';
    if (lower.includes('sport')) return '⚽';
    if (lower.includes('photo')) return '📸';
    return '📍';
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
