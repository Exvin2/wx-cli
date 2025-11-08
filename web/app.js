// wx Web Client - Lightning Fast Weather Intelligence

const API_BASE = 'http://localhost:3000/api';

// DOM Elements
const locationInput = document.getElementById('locationInput');
const searchBtn = document.getElementById('searchBtn');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const story = document.getElementById('story');
const alerts = document.getElementById('alerts');
const alertsList = document.getElementById('alerts List');

// Story elements
const setup = document.getElementById('setup');
const current = document.getElementById('current');
const timeline = document.getElementById('timeline');
const meteorology = document.getElementById('meteorology');
const decisions = document.getElementById('decisions');
const bottomLine = document.getElementById('bottomLine');

// Event listeners
searchBtn.addEventListener('click', fetchWeatherStory);
locationInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') fetchWeatherStory();
});

// Fetch weather story
async function fetchWeatherStory() {
    const location = locationInput.value.trim();
    if (!location) return;

    // Show loading
    story.classList.add('hidden');
    error.classList.add('hidden');
    loading.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/story?location=${encodeURIComponent(location)}`);

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        displayStory(data);

        // Fetch alerts separately
        fetchAlerts(location);

    } catch (err) {
        showError(err.message);
    } finally {
        loading.classList.add('hidden');
    }
}

// Display weather story
function displayStory(data) {
    // Set text content
    setup.textContent = data.setup;
    current.textContent = data.current;
    meteorology.textContent = data.meteorology;
    bottomLine.textContent = data.bottom_line;

    // Render timeline
    timeline.innerHTML = '';
    if (data.evolution && data.evolution.phases) {
        data.evolution.phases.forEach((phase, index) => {
            const phaseEl = document.createElement('div');
            phaseEl.className = 'border-l-4 border-blue-500 pl-4 py-2';
            phaseEl.innerHTML = `
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <p class="font-semibold text-gray-900">${phase.start_time} – ${phase.end_time}</p>
                        <p class="text-gray-700 mt-1">${phase.description}</p>
                        ${phase.key_changes && phase.key_changes.length > 0 ? `
                            <ul class="mt-2 space-y-1">
                                ${phase.key_changes.map(change => `
                                    <li class="text-sm text-gray-600">• ${change}</li>
                                `).join('')}
                            </ul>
                        ` : ''}
                    </div>
                    <div class="ml-4">
                        <div class="text-sm text-gray-500">Confidence</div>
                        <div class="w-24 bg-gray-200 rounded-full h-2 mt-1">
                            <div class="bg-blue-600 h-2 rounded-full" style="width: ${phase.confidence * 100}%"></div>
                        </div>
                    </div>
                </div>
            `;
            timeline.appendChild(phaseEl);
        });
    }

    // Render decisions
    decisions.innerHTML = '';
    if (data.decisions && data.decisions.length > 0) {
        data.decisions.forEach(decision => {
            const decisionEl = document.createElement('div');
            decisionEl.className = 'bg-green-50 border border-green-200 rounded-lg p-4';
            decisionEl.innerHTML = `
                <p class="font-bold text-green-900 mb-2">${getActivityEmoji(decision.activity)} ${decision.activity}</p>
                <p class="text-gray-800 mb-2"><strong>→</strong> ${decision.recommendation}</p>
                <p class="text-sm text-gray-600"><strong>Why:</strong> ${decision.reasoning}</p>
                ${decision.timing ? `<p class="text-sm text-gray-600 mt-1"><strong>Best timing:</strong> ${decision.timing}</p>` : ''}
                <div class="mt-2">
                    <div class="text-xs text-gray-500">Confidence</div>
                    <div class="w-32 bg-gray-200 rounded-full h-2 mt-1">
                        <div class="bg-green-600 h-2 rounded-full" style="width: ${decision.confidence * 100}%"></div>
                    </div>
                </div>
            `;
            decisions.appendChild(decisionEl);
        });
    }

    // Show story
    story.classList.remove('hidden');
}

// Fetch and display alerts
async function fetchAlerts(location) {
    try {
        const response = await fetch(`${API_BASE}/alerts?location=${encodeURIComponent(location)}`);
        const data = await response.json();

        if (data.count > 0) {
            alertsList.innerHTML = '';
            data.alerts.forEach((alert, index) => {
                const alertEl = document.createElement('div');
                alertEl.className = 'bg-white rounded-lg p-4 mb-3';
                alertEl.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <span class="font-bold text-red-900">${alert.event}</span>
                        <span class="text-xs px-2 py-1 bg-red-200 rounded">${alert.severity}</span>
                    </div>
                    <p class="text-gray-700">${alert.description}</p>
                    ${alert.areas && alert.areas.length > 0 ? `
                        <p class="text-sm text-gray-600 mt-2">Areas: ${alert.areas.join(', ')}</p>
                    ` : ''}
                `;
                alertsList.appendChild(alertEl);
            });
            alerts.classList.remove('hidden');
        } else {
            alerts.classList.add('hidden');
        }
    } catch (err) {
        // Alerts are optional, don't show error
        alerts.classList.add('hidden');
    }
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    error.classList.remove('hidden');
    story.classList.add('hidden');
}

// Get activity emoji
function getActivityEmoji(activity) {
    const lower = activity.toLowerCase();
    if (lower.includes('outdoor') || lower.includes('hiking')) return '🌳';
    if (lower.includes('commut') || lower.includes('driv')) return '🚗';
    if (lower.includes('run') || lower.includes('jog')) return '🏃';
    if (lower.includes('flight') || lower.includes('fly')) return '✈️';
    if (lower.includes('bike') || lower.includes('cycl')) return '🚴';
    return '📍';
}

// Load initial story on page load
window.addEventListener('DOMContentLoaded', () => {
    fetchWeatherStory();
});
