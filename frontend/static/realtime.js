/**
 * Real-time transmission monitoring with WebSocket/polling fallback
 */

class RealtimeTransmissionMonitor {
    constructor() {
        this.websocket = null;
        this.pollingInterval = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.subscribers = new Map();
        
        this.init();
    }
    
    init() {
        // Try WebSocket first, fallback to polling
        this.connectWebSocket();
    }
    
    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/transmissions`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.stopPolling();
                this.notifySubscribers('connection', { status: 'connected', type: 'websocket' });
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleRealtimeUpdate(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.websocket = null;
                this.handleDisconnection();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.handleDisconnection();
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.fallbackToPolling();
        }
    }
    
    handleDisconnection() {
        this.isConnected = false;
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.log('Max reconnection attempts reached, falling back to polling');
            this.fallbackToPolling();
        }
    }
    
    fallbackToPolling() {
        console.log('Using polling for real-time updates');
        this.startPolling();
        this.notifySubscribers('connection', { status: 'connected', type: 'polling' });
    }
    
    startPolling() {
        if (this.pollingInterval) return;
        
        this.pollingInterval = setInterval(async () => {
            try {
                await this.pollForUpdates();
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 5000); // Poll every 5 seconds
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    async pollForUpdates() {
        try {
            // Poll for active transmissions
            const response = await fetch('/api/transmissions/updates');
            if (response.ok) {
                const updates = await response.json();
                updates.forEach(update => this.handleRealtimeUpdate(update));
            }
        } catch (error) {
            console.error('Error polling for updates:', error);
        }
    }
    
    handleRealtimeUpdate(data) {
        const { type, payload } = data;
        
        switch (type) {
            case 'connection':
                this.notifySubscribers('connection', payload);
                break;
            case 'transmission_started':
                this.notifySubscribers('transmission_started', payload);
                break;
            case 'transmission_completed':
                this.notifySubscribers('transmission_completed', payload);
                break;
            case 'transmission_failed':
                this.notifySubscribers('transmission_failed', payload);
                break;
            case 'transmission_paused':
                this.notifySubscribers('transmission_paused', payload);
                break;
            case 'transmission_resumed':
                this.notifySubscribers('transmission_resumed', payload);
                break;
            case 'device_status_changed':
                this.notifySubscribers('device_status_changed', payload);
                break;
            case 'connection_status_changed':
                this.notifySubscribers('connection_status_changed', payload);
                break;
            default:
                console.log('Unknown update type:', type);
        }
    }
    
    subscribe(event, callback) {
        if (!this.subscribers.has(event)) {
            this.subscribers.set(event, new Set());
        }
        this.subscribers.get(event).add(callback);
        
        return () => {
            const callbacks = this.subscribers.get(event);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }
    
    notifySubscribers(event, data) {
        const callbacks = this.subscribers.get(event);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Error in subscriber callback:', error);
                }
            });
        }
    }
    
    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    destroy() {
        this.stopPolling();
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.subscribers.clear();
    }
}

/**
 * Real-time UI updates manager
 */
class RealtimeUIManager {
    constructor() {
        this.monitor = new RealtimeTransmissionMonitor();
        this.setupSubscriptions();
    }
    
    setupSubscriptions() {
        // Connection status updates
        this.monitor.subscribe('connection', (data) => {
            this.updateConnectionStatus(data);
        });
        
        // Transmission events
        this.monitor.subscribe('transmission_started', (data) => {
            this.handleTransmissionStarted(data);
        });
        
        this.monitor.subscribe('transmission_completed', (data) => {
            this.handleTransmissionCompleted(data);
        });
        
        this.monitor.subscribe('transmission_failed', (data) => {
            this.handleTransmissionFailed(data);
        });
        
        this.monitor.subscribe('transmission_paused', (data) => {
            this.handleTransmissionPaused(data);
        });
        
        this.monitor.subscribe('transmission_resumed', (data) => {
            this.handleTransmissionResumed(data);
        });
        
        // Device status changes
        this.monitor.subscribe('device_status_changed', (data) => {
            this.handleDeviceStatusChanged(data);
        });
        
        // Connection status changes
        this.monitor.subscribe('connection_status_changed', (data) => {
            this.handleConnectionStatusChanged(data);
        });
    }
    
    updateConnectionStatus(data) {
        const statusElement = document.getElementById('realtime-status');
        if (statusElement) {
            const icon = data.type === 'websocket' ? '🔗' : '🔄';
            statusElement.innerHTML = `${icon} ${data.type === 'websocket' ? 'Tiempo Real' : 'Polling'}`;
            statusElement.className = `realtime-status ${data.status}`;
        }
    }
    
    handleTransmissionStarted(data) {
        if (typeof showNotification === 'function') {
            showNotification(`📤 Transmisión iniciada: ${data.device_name}`, 'info');
        }
        
        // Update device status if viewing the device
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            this.updateDeviceTransmissionState('ACTIVE');
        }
        
        // Update dashboard if visible
        this.updateDashboardStats();
    }
    
    handleTransmissionCompleted(data) {
        if (typeof showNotification === 'function') {
            showNotification(`✅ Transmisión exitosa: ${data.device_name}`, 'success');
        }
        
        // Update transmission history
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            if (typeof refreshTransmissionHistory === 'function') {
                refreshTransmissionHistory();
            }
        }
        
        // Update sensor position if applicable
        if (data.current_row_index !== undefined) {
            const rowElement = document.getElementById('current-row-index');
            if (rowElement) {
                rowElement.textContent = data.current_row_index;
            }
        }
        
        this.updateDashboardStats();
    }
    
    handleTransmissionFailed(data) {
        if (typeof showNotification === 'function') {
            showNotification(`❌ Transmisión fallida: ${data.device_name} - ${data.error}`, 'error');
        }
        
        // Update transmission history
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            if (typeof refreshTransmissionHistory === 'function') {
                refreshTransmissionHistory();
            }
        }
        
        this.updateDashboardStats();
    }
    
    handleTransmissionPaused(data) {
        if (typeof showNotification === 'function') {
            showNotification(`⏸️ Transmisión pausada: ${data.device_name}`, 'warning');
        }
        
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            this.updateDeviceTransmissionState('PAUSED');
        }
    }
    
    handleTransmissionResumed(data) {
        if (typeof showNotification === 'function') {
            showNotification(`▶️ Transmisión reanudada: ${data.device_name}`, 'success');
        }
        
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            this.updateDeviceTransmissionState('ACTIVE');
        }
    }
    
    handleDeviceStatusChanged(data) {
        // Update device list if visible
        const deviceElement = document.querySelector(`[data-device-id="${data.device_id}"]`);
        if (deviceElement) {
            // Update device status indicators
            const statusElement = deviceElement.querySelector('.device-status');
            if (statusElement) {
                statusElement.textContent = data.transmission_enabled ? '🟢 Activo' : '🔴 Inactivo';
            }
        }
        
        // Update current device view if applicable
        if (window.currentDevice && window.currentDevice.id === data.device_id) {
            window.currentDevice.transmission_enabled = data.transmission_enabled;
            if (typeof updateTransmissionControls === 'function') {
                updateTransmissionControls({
                    enabled: data.transmission_enabled,
                    paused: false,
                    deviceType: window.currentDevice.device_type
                });
            }
        }
    }
    
    handleConnectionStatusChanged(data) {
        if (typeof showNotification === 'function') {
            const status = data.is_active ? 'conectada' : 'desconectada';
            const icon = data.is_active ? '🟢' : '🔴';
            showNotification(`${icon} Conexión ${data.connection_name} ${status}`, data.is_active ? 'success' : 'warning');
        }
        
        // Update connection list if visible
        const connectionElement = document.querySelector(`[data-connection-id="${data.connection_id}"]`);
        if (connectionElement) {
            const statusElement = connectionElement.querySelector('.connection-status');
            if (statusElement) {
                statusElement.textContent = data.is_active ? 'Activa' : 'Inactiva';
                statusElement.className = `connection-status ${data.is_active ? 'active' : 'inactive'}`;
            }
        }
    }
    
    updateDeviceTransmissionState(state) {
        const indicator = document.getElementById('transmission-state-indicator');
        const text = document.getElementById('transmission-state-text');
        
        if (indicator && text) {
            indicator.className = `transmission-indicator state-${state.toLowerCase()}`;
            
            const stateTexts = {
                'ACTIVE': 'Transmitiendo',
                'PAUSED': 'Pausado',
                'INACTIVE': 'Inactivo'
            };
            
            text.textContent = stateTexts[state] || 'Desconocido';
        }
    }
    
    updateDashboardStats() {
        // Trigger dashboard refresh if dashboard is visible
        if (window.dashboard && typeof window.dashboard.loadGlobalStats === 'function') {
            window.dashboard.loadGlobalStats();
            window.dashboard.loadActiveTransmissions();
        }
    }
    
    destroy() {
        if (this.monitor) {
            this.monitor.destroy();
        }
    }
}

// Initialize real-time monitoring
let realtimeManager = null;

document.addEventListener('DOMContentLoaded', function() {
    realtimeManager = new RealtimeUIManager();
});

window.addEventListener('beforeunload', function() {
    if (realtimeManager) {
        realtimeManager.destroy();
    }
});

// Export for use in other modules
window.RealtimeTransmissionMonitor = RealtimeTransmissionMonitor;
window.RealtimeUIManager = RealtimeUIManager;
