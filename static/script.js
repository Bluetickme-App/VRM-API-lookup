// Vehicle Data Scraper - Frontend JavaScript

let currentVehicleData = null;
let currentRegistration = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    formatRegistrationInput();
});

function initializeEventListeners() {
    // VNC search button
    document.getElementById('vncSearchBtn').addEventListener('click', handleVncSearch);
    
    // Demo button
    document.getElementById('demoBtn').addEventListener('click', handleDemoData);
    
    // Export buttons
    document.getElementById('exportJsonBtn').addEventListener('click', () => exportData('json'));
    document.getElementById('exportCsvBtn').addEventListener('click', () => exportData('csv'));
    
    // Raw data toggle
    document.getElementById('toggleRawData').addEventListener('click', toggleRawData);
    
    // Registration input formatting
    document.getElementById('registration').addEventListener('input', handleRegistrationInput);
}

function formatRegistrationInput() {
    const regInput = document.getElementById('registration');
    
    regInput.addEventListener('input', function() {
        // Convert to uppercase and limit length
        this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        
        // Add visual feedback for valid format
        if (validateRegistration(this.value)) {
            this.classList.remove('is-invalid');
            this.classList.add('is-valid');
        } else if (this.value.length > 0) {
            this.classList.remove('is-valid');
            this.classList.add('is-invalid');
        } else {
            this.classList.remove('is-valid', 'is-invalid');
        }
    });
}

function validateRegistration(reg) {
    if (!reg || reg.length < 3) return false;
    
    // UK registration patterns
    const patterns = [
        /^[A-Z]{2}[0-9]{2}[A-Z]{3}$/,  // Current format: AB12CDE
        /^[A-Z][0-9]{1,3}[A-Z]{3}$/,   // Prefix format: A123BCD
        /^[A-Z]{3}[0-9]{1,3}[A-Z]$/,   // Suffix format: ABC123D
        /^[0-9]{1,4}[A-Z]{1,3}$/,      // Dateless format: 123AB
        /^[A-Z]{1,3}[0-9]{1,4}$/,      // Early format: AB1234
    ];
    
    return patterns.some(pattern => pattern.test(reg));
}

function handleRegistrationInput(event) {
    const value = event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    event.target.value = value;
}

async function handleSearch(event) {
    event.preventDefault();
    
    const registration = document.getElementById('registration').value.trim().toUpperCase();
    
    if (!registration) {
        showError('Please enter a vehicle registration number');
        return;
    }
    
    if (!validateRegistration(registration)) {
        showError('Please enter a valid UK vehicle registration number');
        return;
    }
    
    currentRegistration = registration;
    
    try {
        showLoading(true);
        hideError();
        hideResults();
        
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ registration: registration })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentVehicleData = result.data;
            displayResults(result.data, registration);
            showSuccess(`Vehicle data successfully retrieved for ${registration}`);
        } else {
            showError(result.error || 'Failed to retrieve vehicle data');
        }
        
    } catch (error) {
        console.error('Search error:', error);
        showError('Network error: Unable to retrieve vehicle data');
    } finally {
        showLoading(false);
    }
}

async function handleVncSearch() {
    const registration = document.getElementById('registration').value.trim().toUpperCase();
    
    if (!registration) {
        showError('Please enter a vehicle registration number');
        return;
    }
    
    if (!validateRegistration(registration)) {
        showError('Please enter a valid UK vehicle registration number');
        return;
    }
    
    try {
        showLoading(true);
        hideError();
        hideResults();
        
        const response = await fetch('/api/scrape-vnc', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ registration: registration })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentVehicleData = result.data;
            currentRegistration = registration;
            displayResults(result.data, registration);
            showSuccess(`Vehicle data successfully retrieved via VNC browser for ${registration}`);
        } else {
            showError(result.error || 'VNC browser search failed');
        }
        
    } catch (error) {
        console.error('VNC search error:', error);
        showError('Network error: Unable to perform VNC browser search');
    } finally {
        showLoading(false);
    }
}

async function handleDemoData() {
    const registration = document.getElementById('registration').value.trim().toUpperCase();
    
    if (!registration) {
        showError('Please enter a vehicle registration number');
        return;
    }
    
    if (!validateRegistration(registration)) {
        showError('Please enter a valid UK vehicle registration number');
        return;
    }
    
    try {
        showLoading(true);
        hideError();
        hideResults();
        
        const response = await fetch(`/api/demo-data/${registration}`);
        const result = await response.json();
        
        if (result.success) {
            currentVehicleData = result.data;
            displayResults(result.data, registration);
            showSuccess(`Demonstration data displayed for ${registration}. Note: ${result.note}`);
        } else {
            showError(result.error || 'Failed to load demonstration data');
        }
        
    } catch (error) {
        console.error('Demo data error:', error);
        showError('Network error: Unable to load demonstration data');
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const searchBtn = document.getElementById('searchBtn');
    
    if (show) {
        loadingIndicator.style.display = 'block';
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Searching...';
    } else {
        loadingIndicator.style.display = 'none';
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search me-2"></i>Search Vehicle';
    }
}

function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideError();
    }, 5000);
}

function hideError() {
    document.getElementById('errorAlert').classList.add('d-none');
}

function showSuccess(message) {
    // Create a temporary success alert
    const successAlert = document.createElement('div');
    successAlert.className = 'alert alert-success fade-in-up';
    successAlert.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
    
    const container = document.querySelector('.container');
    container.insertBefore(successAlert, container.firstChild);
    
    // Remove after 3 seconds
    setTimeout(() => {
        successAlert.remove();
    }, 3000);
}

function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
}

function displayResults(data, registration) {
    // Display vehicle summary
    displayVehicleSummary(data);
    
    // Display tax and MOT information
    displayTaxMotInfo(data.tax_mot || {});
    
    // Display vehicle details
    displayVehicleDetails(data.vehicle_details || {});
    
    // Display performance data
    displayPerformanceData(data);
    
    // Display mileage and safety
    displayMileageSafety(data);
    
    // Display raw data
    displayRawData(data);
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsSection').classList.add('fade-in-up');
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

function displayVehicleSummary(data) {
    const summaryContainer = document.getElementById('vehicleSummary');
    const basicInfo = data.basic_info || {};
    const vehicleDetails = data.vehicle_details || {};
    
    // Extract data from the correct fields based on what the scraper provides
    const make = basicInfo.make || 'Unknown';
    const model = basicInfo.model || vehicleDetails.model || 'Unknown';
    const year = basicInfo.year || vehicleDetails.year || 'Unknown';
    const color = basicInfo.color || vehicleDetails.color || 'Unknown';
    const fuel = basicInfo.fuel_type || vehicleDetails.fuel_type || 'Unknown';
    const description = basicInfo.description || '';
    
    const title = `${make} ${model}`.trim() || 'Vehicle Information';
    
    const transmission = vehicleDetails.transmission || 'Unknown';
    const engineSize = vehicleDetails.engine_size || 'Unknown';
    
    summaryContainer.innerHTML = `
        <div class="col-md-8">
            <h4 class="text-primary mb-3">${escapeHtml(title)}</h4>
            ${description ? `<p class="text-muted mb-3">${escapeHtml(description.substring(0, 200))}${description.length > 200 ? '...' : ''}</p>` : ''}
            <div class="row">
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Make</div>
                        <div class="vehicle-info-value">${escapeHtml(make)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Model</div>
                        <div class="vehicle-info-value">${escapeHtml(model)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Year</div>
                        <div class="vehicle-info-value">${escapeHtml(year)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Color</div>
                        <div class="vehicle-info-value">${escapeHtml(color)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Fuel Type</div>
                        <div class="vehicle-info-value">${escapeHtml(fuel)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Transmission</div>
                        <div class="vehicle-info-value">${escapeHtml(transmission)}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Engine</div>
                        <div class="vehicle-info-value">${escapeHtml(engineSize)}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-4 text-md-end">
            <div class="highlight-info">
                <strong>Registration:</strong><br>
                <span class="h5 text-primary">${escapeHtml(currentRegistration)}</span>
            </div>
        </div>
    `;
}

function displayTaxMotInfo(taxMotData) {
    const container = document.getElementById('taxMotInfo');
    
    const taxExpiry = taxMotData.tax_expiry || 'Unknown';
    const motExpiry = taxMotData.mot_expiry || 'Unknown';
    const taxDaysLeft = taxMotData.tax_days_left || '';
    const motDaysLeft = taxMotData.mot_days_left || '';
    
    container.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">
                        <i class="fas fa-calendar-alt me-2"></i>Tax Expiry
                    </div>
                    <div class="vehicle-info-value">${escapeHtml(taxExpiry)}</div>
                    ${taxDaysLeft ? `<small class="text-muted">${taxDaysLeft} days left</small>` : ''}
                </div>
            </div>
            <div class="col-md-6">
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">
                        <i class="fas fa-tools me-2"></i>MOT Expiry
                    </div>
                    <div class="vehicle-info-value">${escapeHtml(motExpiry)}</div>
                    ${motDaysLeft ? `<small class="text-muted">${motDaysLeft} days left</small>` : ''}
                </div>
            </div>
        </div>
    `;
}

function displayVehicleDetails(details) {
    const container = document.getElementById('vehicleDetails');
    
    // Key details to display
    const keyDetails = [
        'description',
        'transmission',
        'engine',
        'body_style',
        'euro_status',
        'registration_date',
        'type_approval'
    ];
    
    let html = '<table class="info-table table table-sm">';
    
    keyDetails.forEach(key => {
        if (details[key]) {
            const label = formatLabel(key);
            html += `
                <tr>
                    <td>${label}</td>
                    <td>${escapeHtml(details[key])}</td>
                </tr>
            `;
        }
    });
    
    html += '</table>';
    container.innerHTML = html;
}

function displayPerformanceData(data) {
    const container = document.getElementById('performanceData');
    const performance = data.performance || {};
    const fuelEconomy = data.fuel_economy || {};
    const additional = data.additional || {};
    
    let html = '<div class="row">';
    
    // Performance metrics
    if (Object.keys(performance).length > 0) {
        html += '<div class="col-md-6"><h6 class="text-muted mb-2">Performance</h6>';
        for (const [key, value] of Object.entries(performance)) {
            html += `
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">${formatLabel(key)}</div>
                    <div class="vehicle-info-value">${escapeHtml(value)}</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    // Fuel economy
    if (Object.keys(fuelEconomy).length > 0) {
        html += '<div class="col-md-6"><h6 class="text-muted mb-2">Fuel Economy</h6>';
        for (const [key, value] of Object.entries(fuelEconomy)) {
            html += `
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">${formatLabel(key)}</div>
                    <div class="vehicle-info-value">${escapeHtml(value)}</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    html += '</div>';
    
    // Additional info
    if (additional.co2_emissions || additional.tax_12_months) {
        html += '<hr><div class="row">';
        if (additional.co2_emissions) {
            html += `
                <div class="col-md-6">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">CO2 Emissions</div>
                        <div class="vehicle-info-value">${escapeHtml(additional.co2_emissions)}</div>
                    </div>
                </div>
            `;
        }
        if (additional.tax_12_months) {
            html += `
                <div class="col-md-6">
                    <div class="vehicle-info-item">
                        <div class="vehicle-info-label">Annual Tax</div>
                        <div class="vehicle-info-value">${escapeHtml(additional.tax_12_months)}</div>
                    </div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    container.innerHTML = html || '<p class="text-muted">No performance data available</p>';
}

function displayMileageSafety(data) {
    const container = document.getElementById('mileageSafety');
    const mileage = data.mileage || {};
    const safety = data.safety || {};
    
    let html = '<div class="row">';
    
    // Mileage information
    if (Object.keys(mileage).length > 0) {
        html += '<div class="col-md-6"><h6 class="text-muted mb-2">Mileage</h6>';
        for (const [key, value] of Object.entries(mileage)) {
            html += `
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">${formatLabel(key)}</div>
                    <div class="vehicle-info-value">${escapeHtml(value)}</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    // Safety ratings
    if (Object.keys(safety).length > 0) {
        html += '<div class="col-md-6"><h6 class="text-muted mb-2">Safety Ratings</h6>';
        for (const [key, value] of Object.entries(safety)) {
            html += `
                <div class="vehicle-info-item">
                    <div class="vehicle-info-label">${formatLabel(key)}</div>
                    <div class="vehicle-info-value">${escapeHtml(value)}</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    html += '</div>';
    
    container.innerHTML = html || '<p class="text-muted">No mileage or safety data available</p>';
}

function displayRawData(data) {
    const container = document.getElementById('rawDataContent');
    container.textContent = JSON.stringify(data, null, 2);
}

function toggleRawData() {
    const container = document.getElementById('rawDataContainer');
    const toggleBtn = document.getElementById('toggleRawData');
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> Hide';
    } else {
        container.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Show';
    }
}

async function exportData(format) {
    if (!currentVehicleData || !currentRegistration) {
        showError('No data available to export');
        return;
    }
    
    try {
        const response = await fetch(`/api/export/${format}/${currentRegistration}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vehicle_data_${currentRegistration}_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess(`Data exported as ${format.toUpperCase()}`);
        } else {
            const error = await response.json();
            showError(error.error || 'Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        showError('Export failed: Network error');
    }
}

function formatLabel(key) {
    return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function escapeHtml(text) {
    if (typeof text !== 'string') {
        return text;
    }
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
            case 'Enter':
                event.preventDefault();
                document.getElementById('searchForm').dispatchEvent(new Event('submit'));
                break;
            case 'j':
                event.preventDefault();
                exportData('json');
                break;
            case 'c':
                event.preventDefault();
                exportData('csv');
                break;
        }
    }
});
