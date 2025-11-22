// Configuration
const API_URL = 'http://localhost:5000/api/power-status';
const UPDATE_INTERVAL = 2000; // 2 seconds

// DOM Elements
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const statusIndicator = document.getElementById('statusIndicator');
const powerSource = document.getElementById('powerSource');
const chargingStatus = document.getElementById('chargingStatus');
const batteryPercent = document.getElementById('batteryPercent');
const batteryGauge = document.getElementById('batteryGauge');
const timeRemaining = document.getElementById('timeRemaining');
const powerInput = document.getElementById('powerInput');
const powerConsumption = document.getElementById('powerConsumption');
const voltageDisplay = document.getElementById('voltageDisplay');
const currentDisplay = document.getElementById('currentDisplay');
const lastUpdate = document.getElementById('lastUpdate');

// State
let updateTimer = null;

/**
 * Format current time for display
 */
function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Update battery gauge animation
 */
function updateBatteryGauge(percent) {
    const circumference = 534; // 2 * PI * 85
    const offset = circumference - (percent / 100) * circumference;

    batteryGauge.style.strokeDashoffset = offset;

    // Change color based on battery level
    if (percent > 50) {
        batteryGauge.style.stroke = '#10b981'; // Green
    } else if (percent > 20) {
        batteryGauge.style.stroke = '#f59e0b'; // Orange
    } else {
        batteryGauge.style.stroke = '#ef4444'; // Red
    }
}

/**
 * Update power metrics display
 */
function updateMetric(element, value) {
    const valueElement = element.querySelector('.value');
    if (valueElement) {
        // Animate number change
        valueElement.style.transform = 'scale(1.1)';
        setTimeout(() => {
            valueElement.textContent = value;
            valueElement.style.transform = 'scale(1)';
        }, 150);
    }
}

/**
 * Update UI with power status data
 */
function updateUI(data) {
    if (data.error || !data.hasBattery) {
        showError(data.error || 'Battery information not available');
        return;
    }

    // Update status bar
    statusText.textContent = 'Connected';
    statusIndicator.classList.add('connected');

    // Update power source
    const sourceBadge = powerSource.querySelector('.source-badge');
    if (data.powerPlugged) {
        sourceBadge.textContent = '🔌 ' + data.powerSource;
        sourceBadge.className = 'source-badge ac';
    } else {
        sourceBadge.textContent = '🔋 ' + data.powerSource;
        sourceBadge.className = 'source-badge battery';
    }

    // Update charging status
    chargingStatus.textContent = data.status;

    // Update power state detail (NEW)
    const powerStateDetail = document.getElementById('powerStateDetail');
    if (powerStateDetail && data.powerStateText) {
        powerStateDetail.textContent = data.powerStateText;

        // Color coding based on state
        if (data.batteryBypassed) {
            powerStateDetail.style.borderColor = 'var(--accent-success)';
            powerStateDetail.style.color = 'var(--accent-success)';
            powerStateDetail.style.background = 'rgba(16, 185, 129, 0.1)';
        } else if (data.batteryCharging) {
            powerStateDetail.style.borderColor = 'var(--accent-primary)';
            powerStateDetail.style.color = 'var(--accent-primary)';
            powerStateDetail.style.background = 'rgba(0, 242, 255, 0.1)';
        } else if (data.batteryInUse) {
            powerStateDetail.style.borderColor = 'var(--accent-warning)';
            powerStateDetail.style.color = 'var(--accent-warning)';
            powerStateDetail.style.background = 'rgba(245, 158, 11, 0.1)';
        }
    }

    // Update power flow diagram (NEW)
    if (data.powerFlow) {
        const flowAcInput = document.getElementById('flowAcInput');
        const valueToBattery = document.getElementById('valueToBattery');
        const valueToSystem = document.getElementById('valueToSystem');
        const arrowToBattery = document.getElementById('arrowToBattery');
        const arrowToSystem = document.getElementById('arrowToSystem');
        const batteryFlowStatus = document.getElementById('batteryFlowStatus');

        if (flowAcInput) flowAcInput.textContent = `${data.powerFlow.acInput}W`;
        if (valueToBattery) valueToBattery.textContent = `${Math.abs(data.powerFlow.toBattery)}W`;
        if (valueToSystem) valueToSystem.textContent = `${data.powerFlow.toSystem}W`;

        // Update arrow states
        if (arrowToBattery) {
            arrowToBattery.classList.remove('active', 'charging', 'bypassed');
            if (data.batteryCharging && data.powerFlow.toBattery > 0) {
                arrowToBattery.classList.add('active', 'charging');
            } else if (data.batteryBypassed) {
                arrowToBattery.classList.add('bypassed');
            } else if (data.powerFlow.fromBattery > 0) {
                arrowToBattery.classList.add('active');
                // Reverse arrow for battery discharge
                const label = document.getElementById('labelToBattery');
                if (label) label.textContent = 'From Battery';
            } else {
                const label = document.getElementById('labelToBattery');
                if (label) label.textContent = 'To Battery';
            }
        }

        if (arrowToSystem) {
            arrowToSystem.classList.remove('active');
            if (data.powerPlugged || data.batteryInUse) {
                arrowToSystem.classList.add('active');
            }
        }

        // Update battery flow status
        if (batteryFlowStatus) {
            if (data.batteryBypassed) {
                batteryFlowStatus.textContent = '🔌 Bypassed';
                batteryFlowStatus.style.color = 'var(--accent-success)';
            } else if (data.batteryCharging) {
                batteryFlowStatus.textContent = '⚡ Charging';
                batteryFlowStatus.style.color = 'var(--accent-primary)';
            } else if (data.batteryInUse) {
                batteryFlowStatus.textContent = '🔋 In Use';
                batteryFlowStatus.style.color = 'var(--accent-warning)';
            } else {
                batteryFlowStatus.textContent = '⏸️ Idle';
                batteryFlowStatus.style.color = 'var(--text-muted)';
            }
        }
    }

    // Update battery percentage
    batteryPercent.textContent = `${Math.round(data.batteryPercent)}%`;
    updateBatteryGauge(data.batteryPercent);

    // Update time remaining
    if (data.timeRemaining) {
        timeRemaining.textContent = data.powerPlugged
            ? `🔌 Charging • ${data.timeRemaining} to full`
            : `⏱️ ${data.timeRemaining} remaining`;
    } else {
        timeRemaining.textContent = data.powerPlugged
            ? '🔌 Fully charged'
            : '⏱️ Calculating...';
    }

    // Update power input
    updateMetric(powerInput, Math.round(data.powerInputWatts));

    // Update power consumption
    updateMetric(powerConsumption, Math.round(data.powerConsumptionWatts));

    // Update voltage
    if (voltageDisplay && data.voltage !== undefined) {
        updateMetric(voltageDisplay, data.voltage.toFixed(1));
    }

    // Update current
    if (currentDisplay && data.current !== undefined) {
        updateMetric(currentDisplay, data.current.toFixed(2));
    }

    // Update last update time
    lastUpdate.textContent = formatTime();
}

/**
 * Show error message
 */
function showError(message) {
    statusText.textContent = 'Error: ' + message;
    statusIndicator.classList.remove('connected');

    batteryPercent.textContent = '--';
    powerSource.querySelector('.source-badge').textContent = 'Unknown';
    chargingStatus.textContent = 'Unable to detect';
    timeRemaining.textContent = 'N/A';
    updateMetric(powerInput, '--');
    updateMetric(powerConsumption, '--');
}

/**
 * Fetch power status from API
 */
async function fetchPowerStatus() {
    try {
        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        updateUI(data);

    } catch (error) {
        console.error('Failed to fetch power status:', error);
        showError(error.message);
    }
}

/**
 * Start automatic updates
 */
function startUpdates() {
    // Initial fetch
    fetchPowerStatus();

    // Schedule periodic updates
    updateTimer = setInterval(fetchPowerStatus, UPDATE_INTERVAL);
}

/**
 * Stop automatic updates
 */
function stopUpdates() {
    if (updateTimer) {
        clearInterval(updateTimer);
        updateTimer = null;
    }
}

/**
 * Initialize the application
 */
function init() {
    console.log('Laptop Power Monitor initialized');
    console.log(`Connecting to API: ${API_URL}`);
    console.log(`Update interval: ${UPDATE_INTERVAL}ms`);

    // Add SVG gradient for battery gauge
    const svg = document.querySelector('.gauge');
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
    gradient.setAttribute('id', 'gaugeGradient');
    gradient.setAttribute('x1', '0%');
    gradient.setAttribute('y1', '0%');
    gradient.setAttribute('x2', '100%');
    gradient.setAttribute('y2', '100%');

    const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop1.setAttribute('offset', '0%');
    stop1.setAttribute('style', 'stop-color:#00f2ff;stop-opacity:1');

    const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop2.setAttribute('offset', '100%');
    stop2.setAttribute('style', 'stop-color:#7c3aed;stop-opacity:1');

    gradient.appendChild(stop1);
    gradient.appendChild(stop2);
    defs.appendChild(gradient);
    svg.insertBefore(defs, svg.firstChild);

    // Start updates
    startUpdates();

    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopUpdates();
        } else {
            startUpdates();
        }
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', stopUpdates);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
