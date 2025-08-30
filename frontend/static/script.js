// API Configuration
// Use relative base so Nginx can proxy /api to backend container
const API_BASE = '/api';

// Global variables
let devices = [];
let connections = [];
let currentDevice = null;
let transmissionAPI = null;
let realtimeMonitor = null;
let visualizations = null;
let editingConnection = null;

// DOM Elements
const views = {
    devicesList: document.getElementById('devices-list-view'),
    createDevice: document.getElementById('create-device-view'),
    deviceDetail: document.getElementById('device-detail-view'),
    connectionsList: document.getElementById('connections-list-view'),
    connectionForm: document.getElementById('connection-form-view'),
    connectionDetail: document.getElementById('connection-detail-view')
};

const elements = {
    devicesGrid: document.getElementById('devices-grid'),
    devicesLoading: document.getElementById('devices-loading'),
    createForm: document.getElementById('create-device-form'),
    deviceInfo: document.getElementById('device-info'),
    uploadArea: document.getElementById('upload-area'),
    csvFileInput: document.getElementById('csv-file-input'),
    previewSection: document.getElementById('preview-section'),
    csvPreviewTable: document.getElementById('csv-preview-table'),
    jsonPreview: document.getElementById('json-preview'),
    notifications: document.getElementById('notifications')
};

// API Functions
const API = {
    async createDevice(data) {
        const response = await fetch(`${API_BASE}/devices`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async getDevices() {
        const response = await fetch(`${API_BASE}/devices`);
        return response.json();
    },

    async getDevice(id) {
        const response = await fetch(`${API_BASE}/devices/${id}`);
        return response.json();
    },

    async uploadCSV(deviceId, file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/devices/${deviceId}/upload`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },

    async saveCSVData(deviceId, data) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csv_data: data })
        });
        return response.json();
    },

    // Connections API
    async getConnections() {
        const response = await fetch(`${API_BASE}/connections`);
        return response.json();
    },

    async createConnection(data) {
        const response = await fetch(`${API_BASE}/connections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async getConnection(id) {
        const response = await fetch(`${API_BASE}/connections/${id}`);
        return response.json();
    },

    async updateConnection(id, data) {
        const response = await fetch(`${API_BASE}/connections/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteConnection(id) {
        const response = await fetch(`${API_BASE}/connections/${id}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async testConnection(id) {
        const response = await fetch(`${API_BASE}/connections/${id}/test`, {
            method: 'POST'
        });
        return response.json();
    },

    async getConnectionHistory(id, limit = 10) {
        const response = await fetch(`${API_BASE}/connections/${id}/history?limit=${limit}`);
        return response.json();
    },

    async getConnectionTypes() {
        const response = await fetch(`${API_BASE}/connections/types`);
        return response.json();
    },

    async getAuthTypes() {
        const response = await fetch(`${API_BASE}/connections/auth-types`);
        return response.json();
    },

    async sendDeviceData(deviceId, connectionId) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/send/${connectionId}`, {
            method: 'POST'
        });
        return response.json();
    },

    // Manual transmit API
    async manualTransmit(deviceId, connectionId) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/transmit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connection_id: connectionId })
        });
        return response.json();
    },

    // Transmission history API
    async getTransmissionHistory(deviceId, limit = 20) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/transmission-history?limit=${limit}`);
        return response.json();
    },

    // Reset sensor position API
    async resetSensor(deviceId) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/reset-sensor`, { method: 'POST' });
        return response.json();
    }
};

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    elements.notifications.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Transmit modal functions (manual transmission)
async function showTransmitModal() {
    try {
        const connections = await API.getConnections();
        const activeConnections = connections.filter(conn => conn.is_active);
        const selector = document.getElementById('transmit-connections-selector');
        if (!selector) return;
        if (activeConnections.length === 0) {
            selector.innerHTML = '<div class="loading">No hay conexiones activas</div>';
        } else {
            selector.innerHTML = activeConnections.map(conn => `
                <div class="connection-option" onclick="selectTransmitConnection(${conn.id})">
                    <input type="radio" name="tx_connection" value="${conn.id}" id="tx-conn-${conn.id}">
                    <div class="connection-option-info">
                        <div class="connection-option-name">${conn.name}</div>
                        <div class="connection-option-details">${conn.type} - ${conn.host}${conn.port ? ':' + conn.port : ''}</div>
                    </div>
                </div>
            `).join('');
        }
        document.getElementById('transmit-modal').classList.add('active');
    } catch (error) {
        showNotification('Error cargando conexiones: ' + error.message, 'error');
    }
}

function selectTransmitConnection(connectionId) {
    document.querySelectorAll('#transmit-connections-selector .connection-option').forEach(opt => opt.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    document.getElementById(`tx-conn-${connectionId}`).checked = true;
}

function hideTransmitModal() {
    document.getElementById('transmit-modal').classList.remove('active');
}

async function confirmTransmit() {
    const selected = document.querySelector('input[name="tx_connection"]:checked');
    if (!selected) {
        showNotification('Selecciona una conexión', 'warning');
        return;
    }
    try {
        const res = await API.manualTransmit(currentDevice.id, selected.value);
        if (res.error) {
            showNotification(`❌ ${res.error}`, 'error');
        } else {
            showNotification('📤 Transmisión realizada', 'success');
            // Update sensor position and last transmission if provided
            if (typeof res.current_row_index === 'number') {
                const idxEl = document.getElementById('current-row-index');
                if (idxEl) idxEl.textContent = String(res.current_row_index);
                currentDevice.current_row_index = res.current_row_index;
            }
            if (res.last_transmission) {
                // Optionally refresh config/history to reflect timestamp
            }
            await loadTransmissionHistory(currentDevice.id);
        }
    } catch (e) {
        showNotification('Error al transmitir: ' + e.message, 'error');
    } finally {
        hideTransmitModal();
    }
}

// Transmission history
async function loadTransmissionHistory(deviceId) {
    try {
        const list = document.getElementById('transmission-history-list');
        if (!list) return;
        list.innerHTML = '<div class="loading">Cargando historial...</div>';
        const history = await API.getTransmissionHistory(deviceId);
        if (!history || history.length === 0) {
            list.innerHTML = '<div class="loading">Sin transmisiones</div>';
            return;
        }
        list.innerHTML = history.map(item => `
            <div class="history-item ${item.status && item.status.toLowerCase()}">
                <div class="history-info">
                    <div class="history-result ${item.status && item.status.toLowerCase()}">
                        ${item.status === 'SUCCESS' ? '✅ Éxito' : '❌ Falló'}
                    </div>
                    <div class="history-time">${new Date(item.timestamp || item.sent_at || item.created_at).toLocaleString()}</div>
                    ${item.error_message ? `<div class="history-error">${item.error_message}</div>` : ''}
                </div>
                ${item.response_time ? `<div class="history-response-time">${item.response_time}ms</div>` : ''}
            </div>
        `).join('');
    } catch (error) {
        const list = document.getElementById('transmission-history-list');
        if (list) list.innerHTML = '<div class="loading">Error cargando historial</div>';
    }
}

// Paused state persistence (per-device) in sessionStorage
function getPausedState(deviceId) {
    const key = `devsim:paused:${deviceId}`;
    return sessionStorage.getItem(key) === 'true';
}

function setPausedState(deviceId, paused) {
    const key = `devsim:paused:${deviceId}`;
    if (paused) {
        sessionStorage.setItem(key, 'true');
    } else {
        sessionStorage.removeItem(key);
    }
}

function updateTransmissionControls({ enabled, paused, deviceType }) {
    const transmitBtn = document.getElementById('btn-transmit-now');
    const pauseBtn = document.getElementById('btn-pause-transmission');
    const resumeBtn = document.getElementById('btn-resume-transmission');
    const stopBtn = document.getElementById('btn-stop-transmission');

    if (!transmitBtn || !pauseBtn || !resumeBtn || !stopBtn) return;

    // Allow manual "Transmitir ahora" when INACTIVE or PAUSED; disable when automatic is ACTIVE
    transmitBtn.disabled = !!(enabled && !paused);

    // Running (enabled = true)
    if (enabled) {
        pauseBtn.style.display = 'inline-block';
        resumeBtn.style.display = 'none';
        pauseBtn.disabled = false;
        stopBtn.disabled = false;
        return;
    }

    // Not running: paused vs stopped
    if (paused) {
        // Paused: can resume or stop, transmit now enabled
        transmitBtn.disabled = false;
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'inline-block';
        resumeBtn.disabled = false;
        stopBtn.disabled = false;
    } else {
        // Stopped: transmit now enabled, stop disabled, hide resume/pause
        transmitBtn.disabled = false;
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'none';
        stopBtn.disabled = true;
    }
}

function showView(viewName) {
    // Hide all views
    Object.values(views).forEach(view => {
        if (view) view.style.display = 'none';
    });
    
    // Show selected view
    if (views[viewName]) {
        views[viewName].style.display = 'block';
        currentView = viewName;
    } else {
        console.error(`View not found: ${viewName}`);
    }
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Device Functions
async function loadDevices() {
    try {
        elements.devicesLoading.style.display = 'block';
        const devices = await API.getDevices();
        renderDevices(devices);
    } catch (error) {
        showNotification('Error al cargar dispositivos: ' + error.message, 'error');
    } finally {
        elements.devicesLoading.style.display = 'none';
    }
}

function renderDevices(devices) {
    if (devices.length === 0) {
        elements.devicesGrid.innerHTML = '<div class="loading">No hay dispositivos creados</div>';
        return;
    }

    elements.devicesGrid.innerHTML = devices.map(device => `
        <div class="device-card">
            <h3>${device.name}</h3>
            <div class="device-reference">${device.reference}</div>
            <div class="device-description">${device.description || 'Sin descripción'}</div>
            <div class="device-status">
                <div class="status-indicator ${device.csv_data ? 'has-data' : 'no-data'}"></div>
                <span>${device.csv_data ? 'Con datos CSV' : 'Sin datos CSV'}</span>
            </div>
            <div class="device-actions">
                <button class="btn btn-primary btn-small" onclick="viewDevice(${device.id})">
                    Ver Detalle
                </button>
            </div>
        </div>
    `).join('');
}

async function createDevice(formData) {
    try {
        const device = await API.createDevice(formData);
        showNotification('Dispositivo creado correctamente', 'success');
        showView('devicesList');
        loadDevices();
        elements.createForm.reset();
    } catch (error) {
        showNotification('Error al crear dispositivo: ' + error.message, 'error');
    }
}

async function viewDevice(deviceId) {
    try {
        const device = await API.getDevice(deviceId);
        currentDevice = device;
        renderDeviceDetail(device);
        
        // Load transmission configuration and history
        await loadTransmissionConfig(deviceId);
        await loadTransmissionHistory(deviceId);
        
        showView('deviceDetail');
    } catch (error) {
        showNotification('Error al cargar dispositivo: ' + error.message, 'error');
    }
}

function renderDeviceDetail(device) {
    document.getElementById('device-detail-title').textContent = device.name;
    
    elements.deviceInfo.innerHTML = `
        <div class="info-row">
            <div class="info-label">Referencia:</div>
            <div class="info-value">${device.reference}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Nombre:</div>
            <div class="info-value">${device.name}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Descripción:</div>
            <div class="info-value">${device.description || 'Sin descripción'}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Creado:</div>
            <div class="info-value">${formatDate(device.created_at)}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Estado CSV:</div>
            <div class="info-value">${device.csv_data ? 'Datos cargados' : 'Sin datos'}</div>
        </div>
    `;

    // If device already has CSV data saved, render previews by default
    const sendBtn = document.getElementById('btn-send-data');
    if (device.csv_data) {
        csvPreviewData = device.csv_data;
        // Render CSV table and JSON preview
        elements.csvPreviewTable.innerHTML = renderCSVPreview(csvPreviewData);
        elements.jsonPreview.textContent = JSON.stringify(csvPreviewData.json_preview || [], null, 2);
        elements.previewSection.style.display = 'block';
        if (sendBtn) sendBtn.style.display = 'inline-block';
    } else {
        // Hide preview if no data
        elements.csvPreviewTable.innerHTML = '';
        elements.jsonPreview.textContent = '';
        elements.previewSection.style.display = 'none';
        if (sendBtn) sendBtn.style.display = 'none';
    }
}

// CSV Functions
async function handleFileUpload(file) {
    if (!file || !file.name.toLowerCase().endsWith('.csv')) {
        showNotification('Por favor selecciona un archivo CSV válido', 'error');
        return;
    }

    try {
        const result = await API.uploadCSV(currentDevice.id, file);
        
        if (result.error) {
            showNotification(result.error, 'error');
            return;
        }

        csvPreviewData = result.preview;
        // Populate CSV and JSON previews
        elements.csvPreviewTable.innerHTML = renderCSVPreview(csvPreviewData);
        elements.jsonPreview.textContent = JSON.stringify(csvPreviewData.json_preview || [], null, 2);
        elements.previewSection.style.display = 'block';
        // Enable send button when there is preview data
        const sendBtn = document.getElementById('btn-send-data');
        if (sendBtn) sendBtn.style.display = 'inline-block';
        showNotification('Archivo procesado correctamente', 'success');
        
    } catch (error) {
        showNotification('Error al procesar archivo: ' + error.message, 'error');
    }
}

function renderCSVPreview(previewData) {
    // Render CSV table
    const headers = previewData.headers;
    const rows = previewData.csv_preview;
    
    let tableHTML = '<thead><tr>';
    headers.forEach(header => {
        tableHTML += `<th>${header}</th>`;
    });
    tableHTML += '</tr></thead><tbody>';
    
    rows.forEach(row => {
        tableHTML += '<tr>';
        row.forEach(cell => {
            tableHTML += `<td>${cell || ''}</td>`;
        });
        tableHTML += '</tr>';
    });
    tableHTML += '</tbody>';
    
    return tableHTML;
}

async function saveCSVData() {
    if (!csvPreviewData) {
        showNotification('No hay datos para guardar', 'error');
        return;
    }

    try {
        const result = await API.saveCSVData(currentDevice.id, csvPreviewData);
        
        if (result.error) {
            showNotification(result.error, 'error');
            return;
        }

        showNotification('Datos guardados correctamente', 'success');
        elements.previewSection.style.display = 'none';
        csvPreviewData = null;
        
        // Reload device data and update current device
        const updatedDevice = await API.getDevice(currentDevice.id);
        currentDevice = updatedDevice;
        renderDeviceDetail(updatedDevice);
        
    } catch (error) {
        showNotification('Error al guardar datos: ' + error.message, 'error');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Navigation buttons
    document.getElementById('btn-new-device').addEventListener('click', () => {
        showView('createDevice');
    });

    document.getElementById('btn-back-to-list').addEventListener('click', () => {
        showView('devicesList');
    });

    document.getElementById('btn-back-from-detail').addEventListener('click', () => {
        showView('devicesList');
    });

    document.getElementById('btn-cancel-create').addEventListener('click', () => {
        elements.createForm.reset();
        showView('devicesList');
    });

    // Form submission
    elements.createForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {
            name: formData.get('name'),
            description: formData.get('description')
        };
        createDevice(data);
    });

    // File upload
    elements.uploadArea.addEventListener('click', () => {
        elements.csvFileInput.click();
    });

    elements.csvFileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    elements.uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    elements.uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    elements.uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // CSV actions
    document.getElementById('btn-save-csv').addEventListener('click', saveCSVData);

    document.getElementById('btn-cancel-upload').addEventListener('click', () => {
        elements.previewSection.style.display = 'none';
        csvPreviewData = null;
        elements.csvFileInput.value = '';
        const sendBtn = document.getElementById('btn-send-data');
        if (sendBtn) sendBtn.style.display = 'none';
    });

    // Navigation
    document.getElementById('nav-devices').addEventListener('click', () => {
        setActiveNav('devices');
        showView('devicesList');
        loadDevices();
    });

    document.getElementById('nav-connections').addEventListener('click', () => {
        setActiveNav('connections');
        showView('connectionsList');
        loadConnections();
    });

    // Connection event listeners
    document.getElementById('btn-new-connection').addEventListener('click', () => {
        editingConnection = null;
        document.getElementById('connection-form-title').textContent = 'Nueva Conexión';
        document.getElementById('connection-submit-text').textContent = 'Crear Conexión';
        document.getElementById('connection-form').reset();
        clearAuthFields();
        clearAdvancedFields();
        showView('connectionForm');
    });

    document.getElementById('btn-back-to-connections').addEventListener('click', () => {
        showView('connectionsList');
    });

    document.getElementById('btn-back-from-connection-detail').addEventListener('click', () => {
        showView('connectionsList');
    });

    document.getElementById('btn-cancel-connection').addEventListener('click', () => {
        document.getElementById('connection-form').reset();
        showView('connectionsList');
    });

    // Connection form handlers
    document.getElementById('connection-type').addEventListener('change', handleConnectionTypeChange);
    document.getElementById('auth-type').addEventListener('change', handleAuthTypeChange);

    document.getElementById('connection-form').addEventListener('submit', function(e) {
        e.preventDefault();
        handleConnectionSubmit();
    });

    document.getElementById('btn-test-connection').addEventListener('click', () => {
        testConnectionFromForm();
    });

    // Send data modal
    document.getElementById('btn-send-data').addEventListener('click', () => {
        showSendDataModal();
    });

    document.querySelector('.modal-close').addEventListener('click', () => {
        hideSendDataModal();
    });

    document.getElementById('btn-cancel-send').addEventListener('click', () => {
        hideSendDataModal();
    });

    document.getElementById('btn-confirm-send').addEventListener('click', () => {
        confirmSendData();
    });

    // Load initial data
    loadDevices();
});

// Navigation functions
function setActiveNav(section) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`nav-${section}`).classList.add('active');
}

// Connection functions
async function loadConnections() {
    const grid = document.getElementById('connections-grid');
    const loading = document.getElementById('connections-loading');
    
    if (!grid || !loading) {
        console.error('Elements not found: connections-grid or connections-loading');
        return;
    }
    
    try {
        loading.style.display = 'block';
        const connections = await API.getConnections();
        
        if (connections.length === 0) {
            grid.innerHTML = '<div class="loading">No hay conexiones configuradas</div>';
        } else {
            grid.innerHTML = connections.map(conn => createConnectionCard(conn)).join('');
        }
    } catch (error) {
        console.error('Error loading connections:', error);
        showNotification('Error cargando conexiones: ' + error.message, 'error');
        grid.innerHTML = '<div class="loading">Error cargando conexiones</div>';
    } finally {
        if (loading) {
            loading.style.display = 'none';
        }
    }
}

function createConnectionCard(connection) {
    const statusClass = connection.is_active ? 'active' : 'inactive';
    const typeClass = connection.type.toLowerCase();
    const typeIcon = connection.type === 'MQTT' ? '🔄' : '🌐';
    
    return `
        <div class="connection-card">
            <div class="connection-status ${statusClass}"></div>
            <div class="connection-header">
                <div>
                    <div class="connection-title">${connection.name}</div>
                    <div class="connection-type ${typeClass}">${typeIcon} ${connection.type}</div>
                </div>
            </div>
            <div class="connection-info">
                <div><strong>Host:</strong> ${connection.host}${connection.port ? ':' + connection.port : ''}</div>
                <div><strong>Endpoint:</strong> ${connection.endpoint || 'N/A'}</div>
                <div><strong>Auth:</strong> ${connection.auth_type}</div>
                ${connection.description ? `<div><strong>Descripción:</strong> ${connection.description}</div>` : ''}
            </div>
            <div class="connection-actions">
                <button class="btn btn-info btn-sm" onclick="viewConnection(${connection.id})">Ver</button>
                <button class="btn btn-warning btn-sm" onclick="editConnection(${connection.id})">Editar</button>
                <button class="btn btn-success btn-sm" onclick="testConnection(${connection.id})">Probar</button>
                <button class="btn btn-danger btn-sm" onclick="deleteConnection(${connection.id})">Eliminar</button>
            </div>
        </div>
    `;
}

async function viewConnection(id) {
    try {
        const connection = await API.getConnection(id);
        currentConnection = connection;
        
        document.getElementById('connection-detail-title').textContent = connection.name;
        
        const info = document.getElementById('connection-info');
        info.innerHTML = `
            <div class="device-info-grid">
                <div class="info-item">
                    <label>Nombre:</label>
                    <span>${connection.name}</span>
                </div>
                <div class="info-item">
                    <label>Tipo:</label>
                    <span>${connection.type === 'MQTT' ? '🔄 MQTT' : '🌐 HTTPS'}</span>
                </div>
                <div class="info-item">
                    <label>Host:</label>
                    <span>${connection.host}${connection.port ? ':' + connection.port : ''}</span>
                </div>
                <div class="info-item">
                    <label>Endpoint:</label>
                    <span>${connection.endpoint || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <label>Autenticación:</label>
                    <span>${connection.auth_type}</span>
                </div>
                <div class="info-item">
                    <label>Estado:</label>
                    <span class="${connection.is_active ? 'status-active' : 'status-inactive'}">
                        ${connection.is_active ? '✅ Activa' : '❌ Inactiva'}
                    </span>
                </div>
                ${connection.description ? `
                <div class="info-item full-width">
                    <label>Descripción:</label>
                    <span>${connection.description}</span>
                </div>
                ` : ''}
            </div>
        `;
        
        loadConnectionHistory(id);
        showView('connectionDetail');
        
    } catch (error) {
        showNotification('Error cargando conexión: ' + error.message, 'error');
    }
}

async function loadConnectionHistory(connectionId) {
    const historyList = document.getElementById('connection-history-list');
    
    try {
        const history = await API.getConnectionHistory(connectionId);
        
        if (history.length === 0) {
            historyList.innerHTML = '<div class="loading">No hay pruebas registradas</div>';
        } else {
            historyList.innerHTML = history.map(test => `
                <div class="history-item ${test.test_result.toLowerCase()}">
                    <div class="history-info">
                        <div class="history-result ${test.test_result.toLowerCase()}">
                            ${test.test_result === 'SUCCESS' ? '✅ Éxito' : '❌ Falló'}
                        </div>
                        <div class="history-time">${new Date(test.tested_at).toLocaleString()}</div>
                        ${test.error_message ? `<div class="history-error">${test.error_message}</div>` : ''}
                    </div>
                    <div class="history-response-time">
                        ${test.response_time}ms
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        historyList.innerHTML = '<div class="loading">Error cargando historial</div>';
    }
}

async function editConnection(id) {
    try {
        const connection = await API.getConnection(id);
        editingConnection = connection;
        
        document.getElementById('connection-form-title').textContent = 'Editar Conexión';
        document.getElementById('connection-submit-text').textContent = 'Actualizar Conexión';
        
        // Fill form with connection data
        document.getElementById('connection-name').value = connection.name;
        document.getElementById('connection-description').value = connection.description || '';
        document.getElementById('connection-type').value = connection.type;
        document.getElementById('connection-host').value = connection.host;
        document.getElementById('connection-port').value = connection.port || '';
        document.getElementById('connection-endpoint').value = connection.endpoint || '';
        document.getElementById('auth-type').value = connection.auth_type;
        
        // Trigger change events to show appropriate fields
        handleConnectionTypeChange();
        handleAuthTypeChange();
        
        // Fill auth config if available
        if (connection.auth_config) {
            fillAuthFields(connection.auth_config);
        }
        
        showView('connectionForm');
        
    } catch (error) {
        showNotification('Error cargando conexión: ' + error.message, 'error');
    }
}

function handleConnectionTypeChange() {
    const type = document.getElementById('connection-type').value;
    const portField = document.getElementById('connection-port');
    const advancedConfig = document.getElementById('advanced-config');
    
    if (type === 'MQTT') {
        portField.placeholder = '1883';
        document.getElementById('connection-endpoint').placeholder = 'devices/topic';
        showAdvancedFields('mqtt');
    } else if (type === 'HTTPS') {
        portField.placeholder = '443';
        document.getElementById('connection-endpoint').placeholder = '/api/data';
        showAdvancedFields('https');
    } else {
        advancedConfig.style.display = 'none';
    }
    
    // Enable test button if form has minimum required fields
    updateTestButtonState();
}

function handleAuthTypeChange() {
    const authType = document.getElementById('auth-type').value;
    showAuthFields(authType);
    updateTestButtonState();
}

function showAuthFields(authType) {
    const container = document.getElementById('auth-fields');
    container.innerHTML = '';
    
    if (authType === 'USER_PASS') {
        container.innerHTML = `
            <div class="auth-field">
                <label for="auth-username">Usuario *</label>
                <input type="text" id="auth-username" name="username" required>
            </div>
            <div class="auth-field">
                <label for="auth-password">Contraseña *</label>
                <input type="password" id="auth-password" name="password" required>
            </div>
        `;
    } else if (authType === 'TOKEN') {
        container.innerHTML = `
            <div class="auth-field">
                <label for="auth-token">Token *</label>
                <input type="text" id="auth-token" name="token" required>
            </div>
            <div class="auth-field">
                <label for="auth-token-type">Tipo de Token</label>
                <select id="auth-token-type" name="token_type">
                    <option value="Bearer">Bearer</option>
                    <option value="Token">Token</option>
                </select>
            </div>
        `;
    } else if (authType === 'API_KEY') {
        container.innerHTML = `
            <div class="auth-field">
                <label for="auth-key">API Key *</label>
                <input type="text" id="auth-key" name="key" required>
            </div>
            <div class="auth-field">
                <label for="auth-location">Ubicación</label>
                <select id="auth-location" name="location">
                    <option value="header">Header</option>
                    <option value="query">Query Parameter</option>
                </select>
            </div>
            <div class="auth-field">
                <label for="auth-param-name">Nombre del Parámetro</label>
                <input type="text" id="auth-param-name" name="parameter_name" value="X-API-Key">
            </div>
        `;
    }
}

function showAdvancedFields(type) {
    const container = document.getElementById('advanced-fields');
    const advancedConfig = document.getElementById('advanced-config');
    
    if (type === 'mqtt') {
        container.innerHTML = `
            <div class="form-row">
                <div class="form-group">
                    <label for="mqtt-client-id">Client ID</label>
                    <input type="text" id="mqtt-client-id" name="client_id" placeholder="devsim_client">
                </div>
                <div class="form-group">
                    <label for="mqtt-keep-alive">Keep Alive (seg)</label>
                    <input type="number" id="mqtt-keep-alive" name="keep_alive" value="60">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="mqtt-qos">QoS</label>
                    <select id="mqtt-qos" name="qos">
                        <option value="0">0 - At most once</option>
                        <option value="1" selected>1 - At least once</option>
                        <option value="2">2 - Exactly once</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="mqtt-ssl">
                        <input type="checkbox" id="mqtt-ssl" name="ssl"> Usar SSL/TLS
                    </label>
                </div>
            </div>
        `;
        advancedConfig.style.display = 'block';
    } else if (type === 'https') {
        container.innerHTML = `
            <div class="form-row">
                <div class="form-group">
                    <label for="https-method">Método HTTP</label>
                    <select id="https-method" name="method">
                        <option value="POST" selected>POST</option>
                        <option value="PUT">PUT</option>
                        <option value="PATCH">PATCH</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="https-timeout">Timeout (seg)</label>
                    <input type="number" id="https-timeout" name="timeout" value="30">
                </div>
            </div>
            <div class="form-group">
                <label for="https-verify-ssl">
                    <input type="checkbox" id="https-verify-ssl" name="verify_ssl" checked> Verificar SSL
                </label>
            </div>
        `;
        advancedConfig.style.display = 'block';
    }
}

function clearAuthFields() {
    document.getElementById('auth-fields').innerHTML = '';
}

function clearAdvancedFields() {
    document.getElementById('advanced-fields').innerHTML = '';
    document.getElementById('advanced-config').style.display = 'none';
}

function fillAuthFields(authConfig) {
    // Fill auth fields based on current auth type and config
    const authType = document.getElementById('auth-type').value;
    
    if (authType === 'USER_PASS' && authConfig.username) {
        document.getElementById('auth-username').value = authConfig.username;
        if (authConfig.password) {
            document.getElementById('auth-password').value = authConfig.password;
        }
    } else if (authType === 'TOKEN' && authConfig.token) {
        document.getElementById('auth-token').value = authConfig.token;
        if (authConfig.token_type) {
            document.getElementById('auth-token-type').value = authConfig.token_type;
        }
    } else if (authType === 'API_KEY' && authConfig.key) {
        document.getElementById('auth-key').value = authConfig.key;
        if (authConfig.location) {
            document.getElementById('auth-location').value = authConfig.location;
        }
        if (authConfig.parameter_name) {
            document.getElementById('auth-param-name').value = authConfig.parameter_name;
        }
    }
}

function updateTestButtonState() {
    const testBtn = document.getElementById('btn-test-connection');
    const name = document.getElementById('connection-name').value;
    const type = document.getElementById('connection-type').value;
    const host = document.getElementById('connection-host').value;
    const authType = document.getElementById('auth-type').value;
    
    testBtn.disabled = !(name && type && host && authType);
}

async function handleConnectionSubmit() {
    try {
        const formData = new FormData(document.getElementById('connection-form'));
        
        // Basic connection data
        const connectionData = {
            name: formData.get('name'),
            description: formData.get('description'),
            type: formData.get('type'),
            host: formData.get('host'),
            port: formData.get('port') ? parseInt(formData.get('port')) : null,
            endpoint: formData.get('endpoint'),
            auth_type: formData.get('auth_type')
        };
        
        // Auth config
        const authType = formData.get('auth_type');
        if (authType !== 'NONE') {
            connectionData.auth_config = {};
            
            if (authType === 'USER_PASS') {
                connectionData.auth_config.username = formData.get('username');
                connectionData.auth_config.password = formData.get('password');
            } else if (authType === 'TOKEN') {
                connectionData.auth_config.token = formData.get('token');
                connectionData.auth_config.token_type = formData.get('token_type') || 'Bearer';
            } else if (authType === 'API_KEY') {
                connectionData.auth_config.key = formData.get('key');
                connectionData.auth_config.location = formData.get('location') || 'header';
                connectionData.auth_config.parameter_name = formData.get('parameter_name') || 'X-API-Key';
            }
        }
        
        // Connection config (advanced settings)
        const connectionConfig = {};
        if (connectionData.type === 'MQTT') {
            connectionConfig.client_id = formData.get('client_id') || `devsim_${Date.now()}`;
            connectionConfig.keep_alive = parseInt(formData.get('keep_alive')) || 60;
            connectionConfig.qos = parseInt(formData.get('qos')) || 1;
            connectionConfig.ssl = formData.has('ssl');
        } else if (connectionData.type === 'HTTPS') {
            connectionConfig.method = formData.get('method') || 'POST';
            connectionConfig.timeout = parseInt(formData.get('timeout')) || 30;
            connectionConfig.verify_ssl = formData.has('verify_ssl');
        }
        
        connectionData.connection_config = connectionConfig;
        
        let result;
        if (editingConnection) {
            result = await API.updateConnection(editingConnection.id, connectionData);
            showNotification('Conexión actualizada correctamente', 'success');
        } else {
            result = await API.createConnection(connectionData);
            showNotification('Conexión creada correctamente', 'success');
        }
        
        showView('connectionsList');
        loadConnections();
        
    } catch (error) {
        showNotification('Error guardando conexión: ' + error.message, 'error');
    }
}

async function testConnectionFromForm() {
    // First save as draft, then test
    try {
        await handleConnectionSubmit();
        // After successful creation/update, test the connection
        // This is a simplified approach - in production you might want to test without saving
    } catch (error) {
        showNotification('Error al probar conexión: ' + error.message, 'error');
    }
}

async function testConnection(id) {
    try {
        showNotification('Probando conexión...', 'info');
        const result = await API.testConnection(id);
        
        if (result.success) {
            showNotification(`✅ Conexión exitosa (${result.response_time}ms)`, 'success');
        } else {
            showNotification(`❌ Error de conexión: ${result.message}`, 'error');
        }
        
        // Reload history if we're viewing the connection detail
        if (currentView === 'connectionDetail' && currentConnection && currentConnection.id === id) {
            loadConnectionHistory(id);
        }
        
    } catch (error) {
        showNotification('Error probando conexión: ' + error.message, 'error');
    }
}

async function deleteConnection(id) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta conexión?')) {
        return;
    }
    
    try {
        await API.deleteConnection(id);
        showNotification('Conexión eliminada correctamente', 'success');
        loadConnections();
    } catch (error) {
        showNotification('Error eliminando conexión: ' + error.message, 'error');
    }
}

// Send data modal functions
async function showSendDataModal() {
    if (!currentDevice || !currentDevice.csv_data) {
        showNotification('No hay datos CSV para enviar', 'warning');
        return;
    }
    
    try {
        const connections = await API.getConnections();
        const activeConnections = connections.filter(conn => conn.is_active);
        
        if (activeConnections.length === 0) {
            showNotification('No hay conexiones activas disponibles', 'warning');
            return;
        }
        
        const selector = document.getElementById('connections-selector');
        selector.innerHTML = activeConnections.map(conn => `
            <div class="connection-option" onclick="selectConnection(${conn.id})">
                <input type="radio" name="connection" value="${conn.id}" id="conn-${conn.id}">
                <div class="connection-option-info">
                    <div class="connection-option-name">${conn.name}</div>
                    <div class="connection-option-details">
                        ${conn.type} - ${conn.host}${conn.port ? ':' + conn.port : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        // Show data preview
        const preview = document.getElementById('send-data-preview');
        preview.textContent = JSON.stringify(currentDevice.csv_data, null, 2);
        
        document.getElementById('send-data-modal').classList.add('active');
        
    } catch (error) {
        showNotification('Error cargando conexiones: ' + error.message, 'error');
    }
}

function selectConnection(connectionId) {
    document.querySelectorAll('.connection-option').forEach(opt => opt.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    document.getElementById(`conn-${connectionId}`).checked = true;
}

function hideSendDataModal() {
    document.getElementById('send-data-modal').classList.remove('active');
}

async function confirmSendData() {
    const selectedConnection = document.querySelector('input[name="connection"]:checked');
    
    if (!selectedConnection) {
        showNotification('Selecciona una conexión', 'warning');
        return;
    }
    
    try {
        const result = await API.sendDeviceData(currentDevice.id, selectedConnection.value);
        
        if (result.success) {
            showNotification(`✅ ${result.message}`, 'success');
        } else {
            showNotification(`❌ ${result.message}`, 'error');
        }
        
        hideSendDataModal();
        
    } catch (error) {
        showNotification('Error enviando datos: ' + error.message, 'error');
    }
}

// Transmission Functions
async function loadTransmissionConfig(deviceId) {
    try {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/transmission-config`);
        const config = await response.json();
        
        document.getElementById('device-type').value = config.device_type;
        document.getElementById('transmission-frequency').value = config.transmission_frequency;
        document.getElementById('transmission-enabled').checked = config.transmission_enabled;
        
        // Show/hide sensor controls
        const sensorControls = document.getElementById('sensor-controls');
        if (config.device_type === 'Sensor') {
            sensorControls.style.display = 'block';
            document.getElementById('current-row-index').textContent = currentDevice.current_row_index || 0;
        } else {
            sensorControls.style.display = 'none';
        }

        // Update transmission status indicator
        updateTransmissionStatusIndicator(config);
        
        // Update transmission controls
        updateTransmissionControls({
            enabled: config.transmission_enabled || false,
            paused: config.transmission_paused || false,
            deviceType: config.device_type
        });

        // Load transmission history
        loadTransmissionHistory(deviceId);
        
        // Load connections for transmission selector (await to avoid race condition)
        await loadTransmissionConnections();
        
        // Set selected connection if device has one configured
        const selectedId = config.selected_connection_id;
        if (selectedId) {
            const connectionSelector = document.getElementById('transmission-connection');
            if (connectionSelector) {
                connectionSelector.value = String(selectedId);
            }
        }
        
    } catch (error) {
        showNotification('Error cargando configuración: ' + error.message, 'error');
    }
}

// ...
async function saveTransmissionConfig() {
    const deviceType = document.getElementById('device-type').value;
    const frequency = parseInt(document.getElementById('transmission-frequency').value);
    const enabled = document.getElementById('transmission-enabled').checked;
    const connectionId = document.getElementById('transmission-connection').value;
    
    try {
        const response = await fetch(`${API_BASE}/devices/${currentDevice.id}/transmission-config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_type: deviceType,
                transmission_frequency: frequency,
                transmission_enabled: enabled,
                connection_id: connectionId || null
            })
        });
        
        if (response.ok) {
            const updatedDevice = await response.json();
            currentDevice = updatedDevice;
            showNotification('✅ Configuración guardada correctamente', 'success');
            
            // Update sensor controls visibility
            const sensorControls = document.getElementById('sensor-controls');
            if (deviceType === 'Sensor') {
                sensorControls.style.display = 'block';
                document.getElementById('current-row-index').textContent = updatedDevice.current_row_index || 0;
            } else {
                sensorControls.style.display = 'none';
            }

            // Update transmission status indicator based on actual device state
            updateTransmissionStatusIndicator(updatedDevice);
            
            // Update controls without auto-starting transmission
            updateTransmissionControls({
                enabled: !!updatedDevice.transmission_enabled,
                paused: !!updatedDevice.transmission_paused,
                deviceType
            });

            // If enabled and a connection is selected, start automatic transmission now
            if (enabled && connectionId) {
                try {
                    await transmissionAPI.startTransmission(currentDevice.id, connectionId);
                    showNotification('🚀 Transmisión automática iniciada', 'success');
                    // Refresh config/state from backend to reflect ACTIVE/PAUSED and next run time
                    await loadTransmissionConfig(currentDevice.id);
                    await loadTransmissionHistory(currentDevice.id);
                } catch (e) {
                    showNotification('❌ Error iniciando transmisión automática: ' + e.message, 'error');
                }
            }
        } else {
            showNotification('❌ Error guardando configuración', 'error');
        }
        
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

// Update transmission status indicator
function updateTransmissionStatusIndicator(device) {
    const indicator = document.getElementById('transmission-state-indicator');
    const stateText = document.getElementById('transmission-state-text');
    
    if (!indicator || !stateText) return;
    
    // Remove all state classes
    indicator.className = 'transmission-indicator';
    
    if (device.transmission_enabled && !device.transmission_paused) {
        indicator.classList.add('state-active');
        stateText.textContent = 'Activo';
    } else if (device.transmission_enabled && device.transmission_paused) {
        indicator.classList.add('state-paused');
        stateText.textContent = 'Pausado';
    } else if (device.transmission_enabled) {
        indicator.classList.add('state-manual');
        stateText.textContent = 'Manual';
    } else {
        indicator.classList.add('state-inactive');
        stateText.textContent = 'Inactivo';
    }
}

// Load connections into transmission selector
async function loadTransmissionConnections() {
    try {
        const response = await fetch(`${API_BASE}/connections`);
        if (response.ok) {
            const connections = await response.json();
            const selector = document.getElementById('transmission-connection');
            
            // Clear existing options except the first one
            selector.innerHTML = '<option value="">Seleccionar conexión...</option>';
            
            connections.forEach(conn => {
                const option = document.createElement('option');
                option.value = conn.id;
                option.textContent = `${conn.name} (${conn.url})`;
                selector.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading connections:', error);
    }
}

// ...

async function pauseTransmissionUI() {
    try {
        const response = await transmissionAPI.pauseTransmission(currentDevice.id);
        showNotification('⏸️ Transmisión pausada', 'info');
        
        // Update device state
        currentDevice.transmission_paused = true;
        updateTransmissionStatusIndicator(currentDevice);
        updateTransmissionControls({ 
            enabled: currentDevice.transmission_enabled, 
            paused: true, 
            deviceType: currentDevice.device_type 
        });
    } catch (e) {
        showNotification('Error al pausar: ' + e.message, 'error');
    }
}

async function resumeTransmissionUI() {
    try {
        const response = await transmissionAPI.resumeTransmission(currentDevice.id);
        showNotification('▶️ Transmisión reanudada', 'success');
        
        // Update device state
        currentDevice.transmission_paused = false;
        updateTransmissionStatusIndicator(currentDevice);
        updateTransmissionControls({ 
            enabled: currentDevice.transmission_enabled, 
            paused: false, 
            deviceType: currentDevice.device_type 
        });
    } catch (e) {
        showNotification('Error al reanudar: ' + e.message, 'error');
    }
}

async function stopTransmissionUI() {
    try {
        const response = await transmissionAPI.stopTransmission(currentDevice.id);
        showNotification('⏹️ Transmisión detenida', 'info');
        
        // Update device state
        currentDevice.transmission_enabled = false;
        currentDevice.transmission_paused = false;
        document.getElementById('transmission-enabled').checked = false;
        
        updateTransmissionStatusIndicator(currentDevice);
        updateTransmissionControls({ 
            enabled: false, 
            paused: false, 
            deviceType: currentDevice.device_type 
        });
    } catch (e) {
        showNotification('Error al detener: ' + e.message, 'error');
    }
}

async function transmitNowUI() {
    const connectionId = document.getElementById('transmission-connection').value;
    
    if (!connectionId) {
        showNotification('❌ Debe seleccionar una conexión para transmitir', 'error');
        return;
    }
    
    try {
        // Manual transmission: do NOT start automatic scheduler or toggle the checkbox
        const response = await transmissionAPI.transmitNow(currentDevice.id, connectionId);
        if (response && response.success) {
            showNotification('📤 Transmisión manual realizada', 'success');
        } else if (response && response.error) {
            showNotification('❌ ' + response.error, 'error');
        } else {
            showNotification('📤 Solicitud de transmisión enviada', 'info');
        }

        // Refresh history and leave automatic state untouched
        await loadTransmissionHistory(currentDevice.id);
    } catch (e) {
        showNotification('Error al transmitir: ' + e.message, 'error');
    }
}

// Reset sensor position
async function resetSensorPosition() {
    if (!currentDevice) return;
    try {
        const res = await API.resetSensor(currentDevice.id);
        if (res.error) {
            showNotification(`❌ ${res.error}`, 'error');
            return;
        }
        const idx = typeof res.current_row_index === 'number' ? res.current_row_index : 0;
        const idxEl = document.getElementById('current-row-index');
        if (idxEl) idxEl.textContent = String(idx);
        currentDevice.current_row_index = idx;
        showNotification('🔄 Posición del sensor reiniciada', 'success');
    } catch (e) {
        showNotification('Error al reiniciar sensor: ' + e.message, 'error');
    }
}

// Enhanced transmission history with filters and export
let currentHistoryPage = 1;
let historyFilters = { status: '', connection: '' };

async function loadTransmissionHistory(deviceId, page = 1) {
    try {
        const list = document.getElementById('transmission-history-list');
        if (!list) return;
        
        list.innerHTML = '<div class="loading">Cargando historial...</div>';
        
        // Build query parameters
        const params = new URLSearchParams({
            limit: '10',
            page: page.toString()
        });
        
        if (historyFilters.status) params.append('status', historyFilters.status);
        if (historyFilters.connection) params.append('connection_id', historyFilters.connection);
        
        const response = await fetch(`${API_BASE}/devices/${deviceId}/transmission-history?${params}`);
        const data = await response.json();
        
        if (!data.history || data.history.length === 0) {
            list.innerHTML = '<div class="loading">Sin transmisiones</div>';
            document.getElementById('history-pagination').style.display = 'none';
            return;
        }
        
        list.innerHTML = data.history.map(item => `
            <div class="history-item ${item.status && item.status.toLowerCase()}">
                <div class="history-info">
                    <div class="history-result ${item.status && item.status.toLowerCase()}">
                        ${item.status === 'SUCCESS' ? '✅ Éxito' : '❌ Falló'}
                    </div>
                    <div class="history-time">${new Date(item.timestamp || item.sent_at || item.created_at).toLocaleString()}</div>
                    ${item.connection_name ? `<div class="history-connection">Conexión: ${item.connection_name}</div>` : ''}
                    ${item.error_message ? `<div class="history-error">${item.error_message}</div>` : ''}
                </div>
                ${item.response_time ? `<div class="history-response-time">${item.response_time}ms</div>` : ''}
            </div>
        `).join('');
        
        // Update pagination
        currentHistoryPage = page;
        const pagination = document.getElementById('history-pagination');
        const pageInfo = document.getElementById('history-page-info');
        
        if (data.total_pages > 1) {
            pagination.style.display = 'flex';
            pageInfo.textContent = `Página ${page} de ${data.total_pages}`;
            
            const prevBtn = pagination.querySelector('button:first-child');
            const nextBtn = pagination.querySelector('button:last-child');
            
            prevBtn.disabled = page <= 1;
            nextBtn.disabled = page >= data.total_pages;
        } else {
            pagination.style.display = 'none';
        }
        
    } catch (error) {
        const list = document.getElementById('transmission-history-list');
        if (list) list.innerHTML = '<div class="loading">Error cargando historial</div>';
    }
}

function loadHistoryPage(direction) {
    if (!currentDevice) return;
    
    let newPage = currentHistoryPage;
    if (direction === 'prev' && currentHistoryPage > 1) {
        newPage = currentHistoryPage - 1;
    } else if (direction === 'next') {
        newPage = currentHistoryPage + 1;
    }
    
    loadTransmissionHistory(currentDevice.id, newPage);
}

function refreshTransmissionHistory() {
    if (!currentDevice) return;
    loadTransmissionHistory(currentDevice.id, currentHistoryPage);
}

async function exportTransmissionHistory() {
    if (!currentDevice) {
        showNotification('No hay dispositivo seleccionado', 'warning');
        return;
    }
    
    try {
        const params = new URLSearchParams();
        if (historyFilters.status) params.append('status', historyFilters.status);
        if (historyFilters.connection) params.append('connection_id', historyFilters.connection);
        
        const response = await fetch(`${API_BASE}/devices/${currentDevice.id}/transmission-history/export?format=csv&${params}`);
        
        if (!response.ok) {
            throw new Error('Error al exportar historial');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transmission-history-${currentDevice.name}-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('✅ Historial exportado exitosamente', 'success');
        
    } catch (error) {
        showNotification('Error al exportar historial: ' + error.message, 'error');
    }
}

// Initialize history filters
function initializeHistoryFilters() {
    const statusFilter = document.getElementById('history-filter-status');
    const connectionFilter = document.getElementById('history-filter-connection');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            historyFilters.status = this.value;
            if (currentDevice) {
                loadTransmissionHistory(currentDevice.id, 1);
            }
        });
    }
    
    if (connectionFilter) {
        connectionFilter.addEventListener('change', function() {
            historyFilters.connection = this.value;
            if (currentDevice) {
                loadTransmissionHistory(currentDevice.id, 1);
            }
        });
        
        // Load connections for filter
        loadConnectionsForFilter();
    }
}

async function loadConnectionsForFilter() {
    try {
        const connections = await API.getConnections();
        const connectionFilter = document.getElementById('history-filter-connection');
        
        if (connectionFilter && connections) {
            connectionFilter.innerHTML = '<option value="">Todas las conexiones</option>' +
                connections.map(conn => `<option value="${conn.id}">${conn.name}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading connections for filter:', error);
    }
}


// ...

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    transmissionAPI = new TransmissionAPI();
    realtimeMonitor = new RealtimeTransmissionMonitor();
    
    loadDevices();
    loadConnections();
    
    // Initialize real-time monitoring
    // Realtime monitor auto-connects internally
});

// Event Listeners for Transmission Controls
document.addEventListener('DOMContentLoaded', function() {
    // Device type change handler
    document.getElementById('device-type').addEventListener('change', function() {
        const sensorControls = document.getElementById('sensor-controls');
        if (this.value === 'Sensor') {
            sensorControls.style.display = 'block';
        } else {
            sensorControls.style.display = 'none';
        }
    });
    
    // Transmission config buttons
    document.getElementById('btn-save-transmission-config').addEventListener('click', saveTransmissionConfig);
    document.getElementById('btn-transmit-now').addEventListener('click', transmitNowUI);
    document.getElementById('btn-reset-sensor').addEventListener('click', resetSensorPosition);
    // Transmission control buttons
    document.getElementById('btn-pause-transmission').addEventListener('click', pauseTransmissionUI);
    document.getElementById('btn-resume-transmission').addEventListener('click', resumeTransmissionUI);
    document.getElementById('btn-stop-transmission').addEventListener('click', stopTransmissionUI);
    document.getElementById('btn-cancel-transmit').addEventListener('click', hideTransmitModal);
    document.getElementById('btn-confirm-transmit').addEventListener('click', confirmTransmit);
    
    // Initialize history filters
    initializeHistoryFilters();
    
    // Modal close handlers
    document.querySelectorAll('#transmit-modal .modal-close').forEach(btn => {
        btn.addEventListener('click', hideTransmitModal);
    });
});

// Initialize visualization tabs
// (Device analytics/dashboard removed by design)

// Global functions for onclick handlers
window.viewDevice = viewDevice;
window.viewConnection = viewConnection;
window.editConnection = editConnection;
window.testConnection = testConnection;
window.deleteConnection = deleteConnection;
window.selectConnection = selectConnection;
window.selectTransmitConnection = selectTransmitConnection;
