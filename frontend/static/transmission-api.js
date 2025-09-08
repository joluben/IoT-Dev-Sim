/**
 * Advanced Transmission API Client with state management
 * Implements the enhanced API from implementation plan Task 7.5.1
 */

class TransmissionAPI {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
        this.requestQueue = new Map();
        this.retryAttempts = 3;
        this.retryDelay = 1000;
    }

    // Core transmission operations
    async updateDeviceType(deviceId, deviceType) {
        return this._makeRequest(`/devices/${deviceId}/type`, {
            method: 'PUT',
            body: JSON.stringify({ device_type: deviceType })
        });
    }

    async configureTransmission(deviceId, config) {
        return this._makeRequest(`/devices/${deviceId}/transmission-config`, {
            method: 'PUT',
            body: JSON.stringify(config)
        });
    }

    async startTransmission(deviceId, connectionId) {
        return this._makeRequest(`/devices/${deviceId}/start-transmission/${connectionId}`, {
            method: 'POST'
        });
    }

    async pauseTransmission(deviceId) {
        return this._makeRequest(`/devices/${deviceId}/pause`, {
            method: 'POST'
        });
    }

    async resumeTransmission(deviceId) {
        return this._makeRequest(`/devices/${deviceId}/resume`, {
            method: 'POST'
        });
    }

    async stopTransmission(deviceId) {
        return this._makeRequest(`/devices/${deviceId}/stop`, {
            method: 'POST'
        });
    }

    async transmitNow(deviceId, connectionId) {
        return this._makeRequest(`/devices/${deviceId}/transmit`, {
            method: 'POST',
            body: JSON.stringify({ connection_id: connectionId })
        });
    }

    // State management
    async getTransmissionState(deviceId) {
        return this._makeRequest(`/devices/${deviceId}/transmission-state`);
    }

    async getTransmissionHistory(deviceId, limit = 20) {
        return this._makeRequest(`/devices/${deviceId}/transmission-history?limit=${limit}`);
    }

    async getTransmissionStats(deviceId) {
        return this._makeRequest(`/devices/${deviceId}/transmission-stats`);
    }

    // Monitoring and dashboard
    async getActiveTransmissions() {
        return this._makeRequest('/transmissions/active');
    }

    async getGlobalStats() {
        return this._makeRequest('/transmissions/global-stats');
    }

    async getScheduledJobs() {
        return this._makeRequest('/scheduler/jobs');
    }

    // Export functionality
    async exportTransmissionHistory(deviceId, format = 'csv') {
        const response = await this._makeRequest(`/devices/${deviceId}/transmission-history/export?format=${format}`, {
            method: 'GET',
            responseType: 'blob'
        });
        return response;
    }

    // Private helper methods
    async _makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const requestId = `${options.method || 'GET'}_${endpoint}`;

        // Prevent duplicate requests
        if (this.requestQueue.has(requestId)) {
            return this.requestQueue.get(requestId);
        }

        const requestPromise = this._executeRequest(url, options);
        this.requestQueue.set(requestId, requestPromise);

        try {
            const result = await requestPromise;
            return result;
        } finally {
            this.requestQueue.delete(requestId);
        }
    }

    async _executeRequest(url, options) {
        const config = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
                    throw new Error(errorData.error || `HTTP ${response.status}`);
                }

                if (options.responseType === 'blob') {
                    return await response.blob();
                }

                return await response.json();
            } catch (error) {
                if (attempt === this.retryAttempts - 1) {
                    throw error;
                }
                
                // Exponential backoff
                await this._delay(this.retryDelay * Math.pow(2, attempt));
            }
        }
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

/**
 * Transmission Control UI Class
 * Manages button states and UI interactions based on transmission state
 */
class TransmissionControlUI {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.currentState = 'INACTIVE';
        this.api = new TransmissionAPI();
        
        this.buttons = {
            transmitNow: document.getElementById('btn-transmit-now'),
            pause: document.getElementById('btn-pause-transmission'),
            resume: document.getElementById('btn-resume-transmission'),
            stop: document.getElementById('btn-stop-transmission')
        };
        
        this.indicators = {
            state: document.getElementById('transmission-state-indicator'),
            text: document.getElementById('transmission-state-text'),
            progress: document.getElementById('transmission-progress')
        };
        
        this.initializeEventListeners();
        this.updateButtonStates();
        
        // Start periodic state updates
        this.startStatePolling();
    }
    
    async updateButtonStates() {
        try {
            const response = await this.api.getTransmissionState(this.deviceId);
            
            this.currentState = response.current_state;
            const actions = response.available_actions;
            
            // Update button visibility and state
            this._updateButton(this.buttons.transmitNow, actions.transmit_now);
            this._updateButton(this.buttons.pause, actions.pause);
            this._updateButton(this.buttons.resume, actions.resume);
            this._updateButton(this.buttons.stop, actions.stop);
            
            // Update state indicator
            this.updateStateIndicator(this.currentState, response);
            
        } catch (error) {
            // Error updating button states
            this.showError('Error updating transmission state');
        }
    }
    
    _updateButton(button, actionConfig) {
        if (!button) return;
        
        button.disabled = !actionConfig.enabled;
        button.style.display = actionConfig.visible ? 'inline-block' : 'none';
        
        // Store original text for loading states
        if (!button.hasAttribute('data-original-text')) {
            button.setAttribute('data-original-text', button.textContent);
        }
    }
    
    initializeEventListeners() {
        if (this.buttons.transmitNow) {
            this.buttons.transmitNow.addEventListener('click', () => this.handleTransmitNow());
        }
        if (this.buttons.pause) {
            this.buttons.pause.addEventListener('click', () => this.handlePause());
        }
        if (this.buttons.resume) {
            this.buttons.resume.addEventListener('click', () => this.handleResume());
        }
        if (this.buttons.stop) {
            this.buttons.stop.addEventListener('click', () => this.handleStop());
        }
    }
    
    async handleTransmitNow() {
        // Allow manual transmission in any state except when a manual one is in progress
        if (this.currentState === 'MANUAL') {
            this.showError('Ya hay una transmisión manual en curso');
            return;
        }
        
        const connectionId = this.getSelectedConnectionId();
        if (!connectionId) {
            this.showError('Please select a connection');
            return;
        }
        
        try {
            this.setButtonLoading(this.buttons.transmitNow, true);
            const result = await this.api.transmitNow(this.deviceId, connectionId);
            
            if (result.success) {
                this.showSuccess('Transmisión manual completada con éxito');
            } else {
                this.showError(result.error || 'La transmisión falló');
            }
        } catch (error) {
            this.showError('Error de conexión: ' + error.message);
        } finally {
            this.setButtonLoading(this.buttons.transmitNow, false);
            this.updateButtonStates();
        }
    }
    
    async handlePause() {
        try {
            await this.api.pauseTransmission(this.deviceId);
            this.showSuccess('Transmission paused');
            this.updateButtonStates();
        } catch (error) {
            this.showError('Error pausing transmission: ' + error.message);
        }
    }
    
    async handleResume() {
        try {
            await this.api.resumeTransmission(this.deviceId);
            this.showSuccess('Transmission resumed');
            this.updateButtonStates();
        } catch (error) {
            this.showError('Error resuming transmission: ' + error.message);
        }
    }
    
    async handleStop() {
        if (!confirm('Are you sure you want to stop transmission completely?')) {
            return;
        }
        
        try {
            await this.api.stopTransmission(this.deviceId);
            this.showSuccess('Transmission stopped');
            this.updateButtonStates();
        } catch (error) {
            this.showError('Error stopping transmission: ' + error.message);
        }
    }
    
    updateStateIndicator(state, stateData = {}) {
        if (!this.indicators.state || !this.indicators.text) return;
        
        const stateConfig = {
            'INACTIVE': { text: 'Inactive', class: 'state-inactive', color: '#6c757d' },
            'ACTIVE': { text: 'Transmitting', class: 'state-active', color: '#28a745' },
            'PAUSED': { text: 'Paused', class: 'state-paused', color: '#ffc107' },
            'MANUAL': { text: 'Manual Transmission', class: 'state-manual', color: '#17a2b8' }
        };
        
        const config = stateConfig[state] || stateConfig['INACTIVE'];
        
        this.indicators.state.className = `transmission-indicator ${config.class}`;
        this.indicators.state.style.backgroundColor = config.color;
        this.indicators.text.textContent = config.text;
        
        // Update progress for sensors
        if (this.indicators.progress && stateData.progress) {
            this.indicators.progress.style.display = 'block';
            this.indicators.progress.innerHTML = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${stateData.progress.percentage}%"></div>
                </div>
                <span class="progress-text">${stateData.progress.current} / ${stateData.progress.total}</span>
            `;
        } else if (this.indicators.progress) {
            this.indicators.progress.style.display = 'none';
        }
    }
    
    setButtonLoading(button, loading) {
        if (!button) return;
        
        if (loading) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = button.getAttribute('data-original-text') || button.textContent;
        }
    }
    
    startStatePolling() {
        // Poll every 5 seconds for state updates
        this.pollingInterval = setInterval(() => {
            this.updateButtonStates();
        }, 5000);
    }
    
    stopStatePolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Use existing notification system if available
        if (typeof showNotification === 'function') {
            showNotification(message, type);
            return;
        }
        
        // Fallback notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        const container = document.getElementById('notifications') || document.body;
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    getSelectedConnectionId() {
        const selector = document.getElementById('connection-selector') || 
                        document.querySelector('input[name="tx_connection"]:checked');
        return selector ? selector.value : null;
    }
    
    destroy() {
        this.stopStatePolling();
    }
}

// Export for use in other modules
window.TransmissionAPI = TransmissionAPI;
window.TransmissionControlUI = TransmissionControlUI;
