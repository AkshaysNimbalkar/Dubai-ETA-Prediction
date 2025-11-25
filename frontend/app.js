
// Dubai ETA Prediction System - Frontend Application

const API_BASE_URL = 'http://localhost:8000';

// State management
const state = {
    selectedPickup: null,
    selectedDropoff: null,
    zones: [],
    totalPredictions: 0,
    responseTimes: []
};

// Get Dubai time (UTC+4)
function getDubaiTime() {
    const now = new Date();
    // Dubai is UTC+4
    const dubaiOffset = 4 * 60; // 4 hours in minutes
    const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
    const dubaiTime = new Date(utcTime + (dubaiOffset * 60000));
    return dubaiTime;
}

// Format datetime for input field
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Initialize the application
async function init() {
    console.log('Initializing Dubai ETA System...');
    
    // Set datetime to current Dubai time (UTC+4)
    const dubaiTime = getDubaiTime();
    document.getElementById('requestTime').value = formatDateTimeLocal(dubaiTime);
    
    // Set min attribute to current Dubai time
    document.getElementById('requestTime').setAttribute('min', formatDateTimeLocal(dubaiTime));
    
    // Load zones
    await loadZones();
    
    // Create city grid
    createCityGrid();
    
    // Populate zone dropdowns
    populateZoneSelects();
    
    // Setup event listeners
    setupEventListeners();
    
    // Check system health
    await checkSystemHealth();
}

// Load zone information from API
async function loadZones() {
    try {
        const response = await fetch(`${API_BASE_URL}/zones`);
        const data = await response.json();
        state.zones = data.zones;
        console.log(`Loaded ${state.zones.length} zones`);
    } catch (error) {
        console.error('Failed to load zones:', error);
        // Use default zones if API fails
        state.zones = Array.from({length: 100}, (_, i) => ({
            id: i,
            row: Math.floor(i / 10),
            col: i % 10,
            type: getDefaultZoneType(i)
        }));
    }
}

// Get default zone type
function getDefaultZoneType(zoneId) {
    // Check airport first (higher priority)
    if ([98, 99, 88, 89].includes(zoneId)) return 'airport';
    if ([44, 45, 54, 55].includes(zoneId)) return 'business';
    if (zoneId % 10 >= 8) return 'coastal';
    return 'residential';
}

// Create interactive city grid
function createCityGrid() {
    const grid = document.getElementById('cityGrid');
    grid.innerHTML = '';
    
    state.zones.forEach(zone => {
        const cell = document.createElement('div');
        cell.className = `grid-cell ${zone.type}`;
        cell.textContent = zone.id;
        cell.dataset.zoneId = zone.id;
        cell.title = `Zone ${zone.id} - ${zone.type}`;
        
        cell.addEventListener('click', () => handleZoneClick(zone.id));
        
        grid.appendChild(cell);
    });
}

// Handle zone click on grid
function handleZoneClick(zoneId) {
    const cell = document.querySelector(`[data-zone-id="${zoneId}"]`);
    
    if (!state.selectedPickup) {
        // Select as pickup
        clearSelection('pickup');
        state.selectedPickup = zoneId;
        cell.classList.add('selected-pickup');
        document.getElementById('pickupZone').value = zoneId;
        updateDistanceDisplay();
    } else if (!state.selectedDropoff && zoneId !== state.selectedPickup) {
        // Select as dropoff
        clearSelection('dropoff');
        state.selectedDropoff = zoneId;
        cell.classList.add('selected-dropoff');
        document.getElementById('dropoffZone').value = zoneId;
        updateDistanceDisplay();
    } else {
        // Reset and select as new pickup
        clearSelection('pickup');
        clearSelection('dropoff');
        state.selectedPickup = zoneId;
        state.selectedDropoff = null;
        cell.classList.add('selected-pickup');
        document.getElementById('pickupZone').value = zoneId;
        document.getElementById('dropoffZone').value = '';
        updateDistanceDisplay();
    }
}

// Clear grid selection
function clearSelection(type) {
    if (type === 'pickup' && state.selectedPickup !== null) {
        const cell = document.querySelector(`[data-zone-id="${state.selectedPickup}"]`);
        if (cell) cell.classList.remove('selected-pickup');
        state.selectedPickup = null;
    }
    if (type === 'dropoff' && state.selectedDropoff !== null) {
        const cell = document.querySelector(`[data-zone-id="${state.selectedDropoff}"]`);
        if (cell) cell.classList.remove('selected-dropoff');
        state.selectedDropoff = null;
    }
}

// Populate zone select dropdowns
function populateZoneSelects() {
    const pickupSelect = document.getElementById('pickupZone');
    const dropoffSelect = document.getElementById('dropoffZone');
    
    // Group zones by type
    const zonesByType = {
        business: [],
        coastal: [],
        airport: [],
        residential: []
    };
    
    state.zones.forEach(zone => {
        zonesByType[zone.type].push(zone);
    });
    
    // Create options
    Object.entries(zonesByType).forEach(([type, zones]) => {
        if (zones.length > 0) {
            const optgroup1 = document.createElement('optgroup');
            optgroup1.label = type.charAt(0).toUpperCase() + type.slice(1);
            
            const optgroup2 = document.createElement('optgroup');
            optgroup2.label = type.charAt(0).toUpperCase() + type.slice(1);
            
            zones.forEach(zone => {
                const option1 = document.createElement('option');
                option1.value = zone.id;
                option1.textContent = `Zone ${zone.id}`;
                optgroup1.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = zone.id;
                option2.textContent = `Zone ${zone.id}`;
                optgroup2.appendChild(option2);
            });
            
            pickupSelect.appendChild(optgroup1);
            dropoffSelect.appendChild(optgroup2);
        }
    });
}

// Calculate Dubai distance between two zones
// Uses grid-based distance calculation (like counting city blocks in Dubai)
function calculateDubaiDistance(pickup, dropoff) {
    const gridSize = 10;
    // Convert zone number to grid coordinates (row, column)
    const p_row = Math.floor(pickup / gridSize);
    const p_col = pickup % gridSize;
    const d_row = Math.floor(dropoff / gridSize);
    const d_col = dropoff % gridSize;
    // Dubai distance: sum of horizontal + vertical grid units (like driving blocks)
    // You must drive horizontally THEN vertically (or vice versa) - no diagonal shortcuts!
    return Math.abs(p_row - d_row) + Math.abs(p_col - d_col);
}

// Update distance display with detailed calculation explanation
function updateDistanceDisplay() {
    const distanceDiv = document.getElementById('distanceDisplay');
    if (state.selectedPickup !== null && state.selectedDropoff !== null) {
        const distance = calculateDubaiDistance(state.selectedPickup, state.selectedDropoff);
        
        // Calculate coordinates for explanation
        const gridSize = 10;
        const p_row = Math.floor(state.selectedPickup / gridSize);
        const p_col = state.selectedPickup % gridSize;
        const d_row = Math.floor(state.selectedDropoff / gridSize);
        const d_col = state.selectedDropoff % gridSize;
        
        const rowDiff = Math.abs(p_row - d_row);
        const colDiff = Math.abs(p_col - d_col);
        
        distanceDiv.innerHTML = `
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #2196F3;">
                <strong style="font-size: 1.1em;">📍 Route Distance: ${distance} zones</strong>
                
                <div style="margin-top: 10px; padding: 10px; background: white; border-radius: 6px; font-size: 0.9em;">
                    <strong>📊 Calculation Breakdown:</strong><br>
                    <div style="margin-top: 8px; line-height: 1.6;">
                        <strong>Pickup Zone ${state.selectedPickup}:</strong> Row ${p_row}, Column ${p_col}<br>
                        <strong>Dropoff Zone ${state.selectedDropoff}:</strong> Row ${d_row}, Column ${d_col}<br>
                        <div style="margin-top: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
                            <strong>Distance Formula:</strong><br>
                            = |Row₁ - Row₂| + |Col₁ - Col₂|<br>
                            = |${p_row} - ${d_row}| + |${p_col} - ${d_col}|<br>
                            = ${rowDiff} + ${colDiff}<br>
                            = <strong style="color: #2196F3;">${distance} zones</strong>
                        </div>
                        <small style="color: #666; margin-top: 8px; display: block;">
                            💡 This is like counting city blocks: ${rowDiff > 0 ? rowDiff + ' block(s) ' + (d_row > p_row ? 'south' : 'north') : 'same row'}, 
                            ${colDiff > 0 ? colDiff + ' block(s) ' + (d_col > p_col ? 'east' : 'west') : 'same column'}
                        </small>
                    </div>
                </div>
            </div>
        `;
        distanceDiv.style.display = 'block';
    } else {
        distanceDiv.style.display = 'none';
    }
}

// Setup event listeners
function setupEventListeners() {
    // Predict button
    document.getElementById('predictBtn').addEventListener('click', handlePrediction);
    
    // Sync dropdown with grid selection
    document.getElementById('pickupZone').addEventListener('change', (e) => {
        const zoneId = parseInt(e.target.value);
        if (!isNaN(zoneId)) {
            clearSelection('pickup');
            state.selectedPickup = zoneId;
            const cell = document.querySelector(`[data-zone-id="${zoneId}"]`);
            if (cell) cell.classList.add('selected-pickup');
            updateDistanceDisplay();
        }
    });
    
    document.getElementById('dropoffZone').addEventListener('change', (e) => {
        const zoneId = parseInt(e.target.value);
        if (!isNaN(zoneId)) {
            clearSelection('dropoff');
            state.selectedDropoff = zoneId;
            const cell = document.querySelector(`[data-zone-id="${zoneId}"]`);
            if (cell) cell.classList.add('selected-dropoff');
            updateDistanceDisplay();
        }
    });
}

// Handle prediction request
async function handlePrediction() {
    const pickupZone = parseInt(document.getElementById('pickupZone').value);
    const dropoffZone = parseInt(document.getElementById('dropoffZone').value);
    const requestTime = document.getElementById('requestTime').value;
    
    // Validation
    if (isNaN(pickupZone) || isNaN(dropoffZone)) {
        showError('Please select both pickup and dropoff zones');
        return;
    }
    
    if (pickupZone === dropoffZone) {
        showError('Pickup and dropoff zones must be different');
        return;
    }
    
    if (!requestTime) {
        showError('Please select a request time');
        return;
    }
    
    // Clear previous results
    hideError();
    hideResult();
    
    // Show loading state
    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = 'Predicting...';
    
    try {
        const startTime = Date.now();
        
        const response = await fetch(`${API_BASE_URL}/predict_eta`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pickup_zone: pickupZone,
                dropoff_zone: dropoffZone,
                request_time: new Date(requestTime).toISOString()
            })
        });
        
        const responseTime = Date.now() - startTime;
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Prediction failed');
        }
        
        const result = await response.json();
        
        // Update statistics
        updateStatistics(responseTime);
        
        // Display results
        displayResult(result);
        
    } catch (error) {
        console.error('Prediction error:', error);
        showError(error.message || 'Failed to get prediction');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Get ETA Prediction';
    }
}

// Display prediction result
function displayResult(result) {
    const container = document.getElementById('resultContainer');
    
    // Update main ETA value
    document.getElementById('etaValue').textContent = result.estimated_duration_minutes.toFixed(1);
    
    // Update confidence interval
    const ci = result.confidence_interval;
    document.getElementById('confidenceInterval').textContent = 
        `${ci[0].toFixed(1)} - ${ci[1].toFixed(1)}`;
    
    // Update factors with detailed explanations
    const factorsList = document.getElementById('factorsList');
    factorsList.innerHTML = '';
    
    const factorExplanations = {
        'base_time': {
            icon: '📏',
            description: 'Distance-based travel time (3 min per zone)',
            getColor: () => '#2196F3'
        },
        'traffic_adjustment': {
            icon: '🚦',
            description: (val) => {
                if (val > 0) return 'Rush hour or Friday prayer slowdown';
                if (val === 0) return 'Normal traffic conditions';
                return 'Light traffic conditions';
            },
            getColor: (val) => val > 0 ? '#FF5722' : '#4CAF50'
        },
        'weather_impact': {
            icon: '🌤️',
            description: (val) => {
                if (val > 0) return 'Sandstorm or rain delays';
                return 'Clear weather conditions';
            },
            getColor: (val) => val > 0 ? '#FF9800' : '#4CAF50'
        },
        'zone_complexity': {
            icon: '🗺️',
            description: (val) => {
                if (val < -3) return 'Very efficient route (highway access)';
                if (val < 0) return 'Efficient route (direct roads)';
                if (val === 0) return 'Standard route complexity';
                if (val < 3) return 'Moderately complex route';
                return 'Complex route (congested zones)';
            },
            getColor: (val) => {
                if (val < 0) return '#4CAF50';
                if (val === 0) return '#9E9E9E';
                return '#FF9800';
            }
        }
    };
    
    Object.entries(result.factors).forEach(([key, value]) => {
        const li = document.createElement('li');
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const factorInfo = factorExplanations[key];
        
        let explanation = '';
        if (factorInfo) {
            const desc = typeof factorInfo.description === 'function' 
                ? factorInfo.description(value) 
                : factorInfo.description;
            const color = typeof factorInfo.getColor === 'function'
                ? factorInfo.getColor(value)
                : factorInfo.getColor();
            
            explanation = `<br><small style="color: ${color}; font-size: 0.85em;">${factorInfo.icon} ${desc}</small>`;
        }
        
        li.innerHTML = `
            <span>${label}:</span>
            <span><strong>${value.toFixed(1)} minutes</strong>${explanation}</span>
        `;
        factorsList.appendChild(li);
    });
    
    // Show container
    container.style.display = 'block';
}

// Hide result container
function hideResult() {
    document.getElementById('resultContainer').style.display = 'none';
}

// Show error message
function showError(message) {
    const container = document.getElementById('errorContainer');
    document.getElementById('errorMessage').textContent = message;
    container.style.display = 'block';
}

// Hide error container
function hideError() {
    document.getElementById('errorContainer').style.display = 'none';
}

// Update statistics
function updateStatistics(responseTime) {
    state.totalPredictions++;
    state.responseTimes.push(responseTime);
    
    // Keep only last 100 response times
    if (state.responseTimes.length > 100) {
        state.responseTimes.shift();
    }
    
    // Update UI
    document.getElementById('totalPredictions').textContent = state.totalPredictions;
    
    const avgResponseTime = state.responseTimes.reduce((a, b) => a + b, 0) / state.responseTimes.length;
    document.getElementById('avgResponseTime').textContent = `${Math.round(avgResponseTime)}ms`;
}

// Check system health
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy' && data.model_loaded) {
            document.getElementById('systemStatus').textContent = 'Ready';
            document.getElementById('systemStatus').style.color = '#4CAF50';
        } else {
            document.getElementById('systemStatus').textContent = 'Not Ready';
            document.getElementById('systemStatus').style.color = '#f44336';
            showError('Models not loaded. Please train models first.');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        document.getElementById('systemStatus').textContent = 'Offline';
        document.getElementById('systemStatus').style.color = '#f44336';
        showError('API server is not responding. Please start the server.');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

// Periodically check system health
setInterval(checkSystemHealth, 30000);