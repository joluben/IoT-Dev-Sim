// API Configuration
// Use relative base so Nginx can proxy /api to backend container
// For development testing, use direct backend URL
const API_BASE = window.location.hostname === 'localhost' && window.location.port === '8080' 
    ? 'http://127.0.0.1:5000/api' 
    : '/api';

// Global variables
let devices = [];
let connections = [];
let currentDevice = null;
let currentConnection = null;
let currentProject = null;
let transmissionAPI = null;
let realtimeMonitor = null;
let visualizations = null;
let editingConnection = null;
let lastTransmissionHistory = [];
let lastProjectTransmissionHistory = [];
let websocket = null;

// DOM Elements
const views = {
    devicesList: document.getElementById('devices-list-view'),
    createDevice: document.getElementById('create-device-view'),
    deviceDetail: document.getElementById('device-detail-view'),
    connectionsList: document.getElementById('connections-list-view'),
    connectionForm: document.getElementById('connection-form-view'),
    connectionDetail: document.getElementById('connection-detail-view'),
    projectsList: document.getElementById('projects-list-view'),
    projectForm: document.getElementById('project-form-view'),
    projectDetail: document.getElementById('project-detail-view')
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

    async deleteDevice(id) {
        const response = await fetch(`${API_BASE}/devices/${id}`, {
            method: 'DELETE'
        });
        return response;
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

    // Device duplication API
    async duplicateDevice(deviceId, count) {
        const response = await fetch(`${API_BASE}/devices/${deviceId}/duplicate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count })
        });
        return response.json();
    },

    // Project API functions
    async getProjects() {
        const response = await fetch(`${API_BASE}/projects`);
        const text = await response.text();
        let payload;
        try { payload = text ? JSON.parse(text) : []; }
        catch (_) { payload = { error: text || 'Respuesta no válida' }; }
        if (!response.ok) {
            const msg = (payload && payload.error) ? payload.error : `HTTP ${response.status}`;
            throw new Error(msg);
        }
        return payload;
    },

    async createProject(data) {
        const response = await fetch(`${API_BASE}/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        // Gracefully handle non-JSON error bodies (e.g., HTML 405 page)
        let payload;
        const text = await response.text();
        try {
            payload = text ? JSON.parse(text) : {};
        } catch (_) {
            payload = { error: text };
        }
        if (!response.ok) {
            const msg = (payload && payload.error) ? payload.error : `HTTP ${response.status}`;
            throw new Error(msg);
        }
        return payload;
    },

    async getProject(id) {
        const response = await fetch(`${API_BASE}/projects/${id}`);
        return response.json();
    },

    async updateProject(id, data) {
        const response = await fetch(`${API_BASE}/projects/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteProject(id) {
        const response = await fetch(`${API_BASE}/projects/${id}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async getProjectDevices(id) {
        const response = await fetch(`${API_BASE}/projects/${id}/devices`);
        return response.json();
    },

    async addDevicesToProject(projectId, deviceIds) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/devices`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_ids: deviceIds })
        });
        return response.json();
    },

    async removeDeviceFromProject(projectId, deviceId) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/devices/${deviceId}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async getUnassignedDevices() {
        const response = await fetch(`${API_BASE}/devices/unassigned`);
        return response.json();
    },

    async startProjectTransmission(projectId, connectionId) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/start-transmission`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connection_id: connectionId })
        });
        return response.json();
    },

    async pauseProjectTransmission(projectId) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/pause-transmission`, {
            method: 'POST'
        });
        return response.json();
    },

    async resumeProjectTransmission(projectId) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/resume-transmission`, {
            method: 'POST'
        });
        return response.json();
    },

    async stopProjectTransmission(projectId) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/stop-transmission`, {
            method: 'POST'
        });
        return response.json();
    },

    async getProjectTransmissionHistory(projectId, limit = 100, offset = 0) {
        const response = await fetch(`${API_BASE}/projects/${projectId}/transmission-history?limit=${limit}&offset=${offset}`);
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
        lastTransmissionHistory = Array.isArray(history) ? history : [];
        if (!lastTransmissionHistory || lastTransmissionHistory.length === 0) {
            list.innerHTML = '<div class="loading">Sin transmisiones</div>';
            return;
        }
        populateHistoryConnectionFilter(lastTransmissionHistory);
        attachHistoryFilterListeners();
        renderTransmissionHistory();
    } catch (error) {
        const list = document.getElementById('transmission-history-list');
        if (list) list.innerHTML = '<div class="loading">Error cargando historial</div>';
    }
}

function renderTransmissionHistory() {
    const list = document.getElementById('transmission-history-list');
    if (!list) return;

    const statusFilter = document.getElementById('history-filter-status');
    const connFilter = document.getElementById('history-filter-connection');

    let items = lastTransmissionHistory.slice();

    // Apply status filter
    const statusVal = statusFilter ? statusFilter.value : '';
    if (statusVal) {
        items = items.filter(i => i.status === statusVal);
    }

    // Apply connection filter
    const connVal = connFilter ? connFilter.value : '';
    if (connVal) {
        const connId = Number(connVal);
        items = items.filter(i => Number(i.connection_id) === connId);
    }

    if (items.length === 0) {
        list.innerHTML = '<div class="loading">Sin transmisiones</div>';
        return;
    }

    list.innerHTML = items.map(item => {
        const ts = item.timestamp || item.transmission_time || item.sent_at || item.created_at;
        const when = ts ? new Date(ts).toLocaleString() : '';
        const statusCls = item.status ? item.status.toLowerCase() : '';
        return `
            <div class="history-item ${statusCls}">
                <div class="history-info">
                    <div class="history-result ${statusCls}">
                        ${item.status === 'SUCCESS' ? '✅ Éxito' : '❌ Falló'}
                    </div>
                    <div class="history-time">${when}</div>
                    ${item.error_message ? `<div class="history-error">${item.error_message}</div>` : ''}
                </div>
                ${item.response_time ? `<div class="history-response-time">${item.response_time}ms</div>` : ''}
            </div>
        `;
    }).join('');
}

// History controls
function refreshTransmissionHistory() {
    if (!currentDevice) return;
    loadTransmissionHistory(currentDevice.id);
}

async function exportTransmissionHistory() {
    try {
        if (!currentDevice) return;
        const resp = await fetch(`${API_BASE}/devices/${currentDevice.id}/transmission-history/export?format=csv`);
        if (!resp.ok) throw new Error('Export failed');
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transmission_history_device_${currentDevice.id}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        showNotification('Error exportando historial: ' + e.message, 'error');
    }
}

function loadHistoryPage(direction) {
    // Placeholder for future pagination. Currently just refreshes.
    refreshTransmissionHistory();
}

function populateHistoryConnectionFilter(historyItems) {
    const select = document.getElementById('history-filter-connection');
    if (!select) return;
    const prevValue = select.value;
    const uniqueConnIds = [...new Set(historyItems.map(i => i.connection_id).filter(Boolean))];
    const options = ['<option value="">Todas las conexiones</option>']
        .concat(uniqueConnIds.map(id => `<option value="${id}">Conexión ${id}</option>`));
    select.innerHTML = options.join('');
    // Restore previous selection if still present
    if (prevValue && uniqueConnIds.includes(Number(prevValue))) {
        select.value = prevValue;
    }
}

function attachHistoryFilterListeners() {
    const statusFilter = document.getElementById('history-filter-status');
    const connFilter = document.getElementById('history-filter-connection');
    if (statusFilter && !statusFilter._listenerAttached) {
        statusFilter.addEventListener('change', renderTransmissionHistory);
        statusFilter._listenerAttached = true;
    }
    if (connFilter && !connFilter._listenerAttached) {
        connFilter.addEventListener('change', renderTransmissionHistory);
        connFilter._listenerAttached = true;
    }
}

// ============================================================================
// PROJECT MANAGEMENT FUNCTIONS
// ============================================================================

// Project navigation and loading
async function loadProjects() {
    try {
        const projectsGrid = document.getElementById('projects-grid');
        if (!projectsGrid) return;
        
        projectsGrid.innerHTML = '<div class="loading">Cargando proyectos...</div>';
        
        const projects = await API.getProjects();
        if (!Array.isArray(projects)) {
            const errMsg = projects && projects.error ? projects.error : 'Respuesta inesperada al cargar proyectos';
            throw new Error(errMsg);
        }
        
        if (projects.length === 0) {
            projectsGrid.innerHTML = '<div class="empty-state">No hay proyectos creados</div>';
            return;
        }
        
        projectsGrid.innerHTML = projects.map(project => `
            <div class="project-card" onclick="showProjectDetail(${project.id})">
                <div class="project-header">
                    <h3>${project.name}</h3>
                    <div class="project-status ${project.transmission_status.toLowerCase()}">
                        ${getTransmissionStatusText(project.transmission_status)}
                    </div>
                </div>
                <div class="project-info">
                    <p class="project-description">${project.description || 'Sin descripción'}</p>
                    <div class="project-stats">
                        <span class="device-count">📱 ${project.devices_count} dispositivos</span>
                </div>
                <div class="project-actions">
                    <button class="btn btn-sm btn-info" onclick="event.stopPropagation(); editProject(${project.id})">✏️ ${window.i18n.t('common.actions.edit')}</button>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteProject(${project.id})">🗑️ ${window.i18n.t('common.actions.delete')}</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading projects:', error);
        const projectsGrid = document.getElementById('projects-grid');
        if (projectsGrid) {
            projectsGrid.innerHTML = '<div class="error">Error cargando proyectos</div>';
        }
    }
}

function getTransmissionStatusText(status) {
    const statusMap = {
        'INACTIVE': 'Inactivo',
        'ACTIVE': 'Activo',
        'PAUSED': 'Pausado'
    };
    return statusMap[status] || status;
}

// Project detail view
async function showProjectDetail(projectId) {
    try {
        currentProject = await API.getProject(projectId);
        if (!currentProject) {
            showNotification('Proyecto no encontrado', 'error');
            return;
        }
        
        // Update project header
        document.getElementById('project-detail-title').textContent = currentProject.name;
        
        // Update project status badge
        const statusBadge = document.getElementById('project-status-badge');
        if (statusBadge) {
            const statusClass = currentProject.transmission_status.toLowerCase();
            statusBadge.className = `project-status ${statusClass}`;
            statusBadge.textContent = getTransmissionStatusText(currentProject.transmission_status);
        }
        
        // Update project statistics
        document.getElementById('project-devices-count').textContent = currentProject.devices_count || 0;
        document.getElementById('project-transmissions-count').textContent = currentProject.transmissions_count || 0;
        document.getElementById('project-success-rate').textContent = currentProject.success_rate || '0%';
        
        // Update project info panel with new structure
        document.getElementById('project-info').innerHTML = `
            <div class="info-item">
                <span class="info-label">ID</span>
                <span class="info-value">#${currentProject.id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Nombre</span>
                <span class="info-value">${currentProject.name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Descripción</span>
                <span class="info-value">${currentProject.description || 'Sin descripción'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Estado</span>
                <span class="info-value">${getTransmissionStatusText(currentProject.transmission_status)}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Creado</span>
                <span class="info-value">${formatDate(currentProject.created_at)}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Última transmisión</span>
                <span class="info-value">${currentProject.last_transmission ? formatDate(currentProject.last_transmission) : 'Nunca'}</span>
            </div>
        `;
        
        // Update transmission status indicator
        updateProjectTransmissionStatus(currentProject.transmission_status);
        
        // Load project devices
        await loadProjectDevices(projectId);
        
        // Load connections for selector
        await loadProjectConnectionSelector();
        
        // Load transmission history
        await loadProjectTransmissionHistory(projectId);
        
        showView('projectDetail');
        
    } catch (error) {
        console.error('Error loading project detail:', error);
        showNotification('Error cargando detalle del proyecto', 'error');
    }
}

function updateProjectTransmissionStatus(status) {
    const indicator = document.getElementById('project-transmission-indicator');
    const text = document.getElementById('project-transmission-text');
    
    if (!indicator || !text) return;
    
    // Remove all status classes
    indicator.className = 'transmission-indicator';
    
    switch (status) {
        case 'ACTIVE':
            indicator.classList.add('state-active');
            text.textContent = 'Activo';
            break;
        case 'PAUSED':
            indicator.classList.add('state-paused');
            text.textContent = 'Pausado';
            break;
        default:
            indicator.classList.add('state-inactive');
            text.textContent = 'Inactivo';
    }
    
    // Update button states
    updateProjectTransmissionButtons(status);
}

function updateProjectTransmissionButtons(status) {
    const startBtn = document.getElementById('btn-start-project-transmission');
    const pauseBtn = document.getElementById('btn-pause-project-transmission');
    const resumeBtn = document.getElementById('btn-resume-project-transmission');
    const stopBtn = document.getElementById('btn-stop-project-transmission');
    
    if (!startBtn || !pauseBtn || !resumeBtn || !stopBtn) return;
    
    // Reset all buttons
    [startBtn, pauseBtn, resumeBtn, stopBtn].forEach(btn => {
        btn.disabled = false;
        btn.style.display = 'inline-block';
    });
    
    switch (status) {
        case 'ACTIVE':
            startBtn.disabled = true;
            resumeBtn.style.display = 'none';
            break;
        case 'PAUSED':
            startBtn.disabled = true;
            pauseBtn.style.display = 'none';
            break;
        default: // INACTIVE
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'none';
            stopBtn.disabled = true;
    }
}

// Project devices management
async function loadProjectDevices(projectId) {
    try {
        const devicesList = document.getElementById('project-devices-list');
        if (!devicesList) return;
        
        devicesList.innerHTML = '<div class="loading">Cargando dispositivos...</div>';
        
        const devices = await API.getProjectDevices(projectId);
        
        if (!devices || devices.length === 0) {
            devicesList.innerHTML = '<div class="empty-state">No hay dispositivos en este proyecto</div>';
            return;
        }
        
        devicesList.innerHTML = devices.map(device => `
            <div class="device-card" onclick="viewDevice(${device.id})">
                <div class="device-card-header">
                    <div class="device-name">${device.name}</div>
                    <div class="device-reference">${device.reference}</div>
                </div>
                <div class="device-status">
                    <div class="status-indicator ${device.csv_data ? 'has-data' : 'no-data'}"></div>
                    <span>${device.csv_data ? 'Datos cargados' : 'Sin datos CSV'}</span>
                </div>
                <div class="device-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-info" onclick="viewDevice(${device.id})">${window.i18n.t('common.actions.view_details')}</button>
                    <button class="btn btn-sm btn-danger" onclick="removeDeviceFromProject(${device.id})">${window.i18n.t('projects.actions.remove_devices')}</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading project devices:', error);
        const devicesList = document.getElementById('project-devices-list');
        if (devicesList) {
            devicesList.innerHTML = '<div class="error">Error cargando dispositivos</div>';
        }
    }
}

async function loadProjectConnectionSelector() {
    try {
        const selector = document.getElementById('project-connection-selector');
        if (!selector) return;
        
        const connections = await API.getConnections();
        const activeConnections = connections.filter(conn => conn.is_active);
        
        selector.innerHTML = '<option value="">Usar conexión de cada dispositivo</option>' +
            activeConnections.map(conn => 
                `<option value="${conn.id}">${conn.name} (${conn.type})</option>`
            ).join('');
            
    } catch (error) {
        console.error('Error loading connections for project:', error);
    }
}

// Project transmission operations
async function startProjectTransmission() {
    if (!currentProject) return;
    
    try {
        const connectionId = document.getElementById('project-connection-selector').value || null;
        
        showNotification('Iniciando transmisiones del proyecto...', 'info');
        
        const result = await API.startProjectTransmission(currentProject.id, connectionId);
        
        showOperationResults('Iniciar Transmisiones', result);
        
        // Update project status
        if (result.successful_operations > 0) {
            currentProject.transmission_status = 'ACTIVE';
            updateProjectTransmissionStatus('ACTIVE');
        }
        
    } catch (error) {
        console.error('Error starting project transmission:', error);
        showNotification('Error al iniciar transmisiones del proyecto', 'error');
    }
}

async function pauseProjectTransmission() {
    if (!currentProject) return;
    
    try {
        showNotification('Pausando transmisiones del proyecto...', 'info');
        
        const result = await API.pauseProjectTransmission(currentProject.id);
        
        showOperationResults('Pausar Transmisiones', result);
        
        if (result.successful_operations > 0) {
            currentProject.transmission_status = 'PAUSED';
            updateProjectTransmissionStatus('PAUSED');
        }
        
    } catch (error) {
        console.error('Error pausing project transmission:', error);
        showNotification('Error al pausar transmisiones del proyecto', 'error');
    }
}

async function resumeProjectTransmission() {
    if (!currentProject) return;
    
    try {
        showNotification('Reanudando transmisiones del proyecto...', 'info');
        
        const result = await API.resumeProjectTransmission(currentProject.id);
        
        showOperationResults('Reanudar Transmisiones', result);
        
        if (result.successful_operations > 0) {
            currentProject.transmission_status = 'ACTIVE';
            updateProjectTransmissionStatus('ACTIVE');
        }
        
    } catch (error) {
        console.error('Error resuming project transmission:', error);
        showNotification('Error al reanudar transmisiones del proyecto', 'error');
    }
}

async function stopProjectTransmission() {
    if (!currentProject) return;
    
    try {
        showNotification('Deteniendo transmisiones del proyecto...', 'info');
        
        const result = await API.stopProjectTransmission(currentProject.id);
        
        showOperationResults('Detener Transmisiones', result);
        
        currentProject.transmission_status = 'INACTIVE';
        updateProjectTransmissionStatus('INACTIVE');
        
    } catch (error) {
        console.error('Error stopping project transmission:', error);
        showNotification('Error al detener transmisiones del proyecto', 'error');
    }
}

// Project transmission history
async function loadProjectTransmissionHistory(projectId) {
    try {
        const list = document.getElementById('project-transmission-history-list');
        if (!list) return;
        
        list.innerHTML = '<div class="loading">Cargando historial...</div>';
        
        const response = await API.getProjectTransmissionHistory(projectId);
        const history = response.transmissions || [];
        
        lastProjectTransmissionHistory = Array.isArray(history) ? history : [];
        
        if (!lastProjectTransmissionHistory || lastProjectTransmissionHistory.length === 0) {
            list.innerHTML = '<div class="loading">Sin transmisiones</div>';
            return;
        }
        
        populateProjectHistoryDeviceFilter(lastProjectTransmissionHistory);
        attachProjectHistoryFilterListeners();
        renderProjectTransmissionHistory();
        
    } catch (error) {
        console.error('Error loading project transmission history:', error);
        const list = document.getElementById('project-transmission-history-list');
        if (list) list.innerHTML = '<div class="loading">Error cargando historial</div>';
    }
}

function renderProjectTransmissionHistory() {
    const list = document.getElementById('project-transmission-history-list');
    if (!list) return;
    
    const deviceFilter = document.getElementById('project-history-filter-device');
    const statusFilter = document.getElementById('project-history-filter-status');
    
    let filteredHistory = [...lastProjectTransmissionHistory];
    
    // Apply device filter
    if (deviceFilter && deviceFilter.value) {
        filteredHistory = filteredHistory.filter(item => 
            item.device_id == deviceFilter.value
        );
    }
    
    // Apply status filter
    if (statusFilter && statusFilter.value) {
        filteredHistory = filteredHistory.filter(item => 
            item.status === statusFilter.value
        );
    }
    
    if (filteredHistory.length === 0) {
        list.innerHTML = '<div class="loading">No hay transmisiones que coincidan con los filtros</div>';
        return;
    }
    
    list.innerHTML = filteredHistory.map(item => {
        const timestamp = item.timestamp || item.transmission_time || item.sent_at || item.created_at;
        const statusClass = item.status === 'SUCCESS' ? 'success' : 'failed';
        
        return `
            <div class="history-item ${statusClass}">
                <div class="history-header">
                    <span class="device-name">${item.device_name} (${item.device_reference})</span>
                    <span class="connection-name">${item.connection_name}</span>
                    <span class="timestamp">${formatDate(timestamp)}</span>
                </div>
                <div class="history-details">
                    <span class="status ${statusClass}">${item.status}</span>
                    <span class="transmission-type">${item.transmission_type}</span>
                    ${item.row_index !== null ? `<span class="row-index">Fila: ${item.row_index}</span>` : ''}
                    ${item.error_message ? `<span class="error-message">Error: ${item.error_message}</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function populateProjectHistoryDeviceFilter(historyItems) {
    const select = document.getElementById('project-history-filter-device');
    if (!select) return;
    
    const prevValue = select.value;
    const uniqueDevices = [...new Map(historyItems.map(i => [i.device_id, i])).values()];
    
    const options = ['<option value="">Todos los dispositivos</option>']
        .concat(uniqueDevices.map(item => 
            `<option value="${item.device_id}">${item.device_name} (${item.device_reference})</option>`
        ));
    
    select.innerHTML = options.join('');
    
    // Restore previous selection if still present
    if (prevValue && uniqueDevices.some(d => d.device_id == prevValue)) {
        select.value = prevValue;
    }
}

function attachProjectHistoryFilterListeners() {
    const deviceFilter = document.getElementById('project-history-filter-device');
    const statusFilter = document.getElementById('project-history-filter-status');
    
    if (deviceFilter && !deviceFilter._projectListenerAttached) {
        deviceFilter.addEventListener('change', renderProjectTransmissionHistory);
        deviceFilter._projectListenerAttached = true;
    }
    if (statusFilter && !statusFilter._projectListenerAttached) {
        statusFilter.addEventListener('change', renderProjectTransmissionHistory);
        statusFilter._projectListenerAttached = true;
    }
}

function refreshProjectTransmissionHistory() {
    if (!currentProject) return;
    loadProjectTransmissionHistory(currentProject.id);
}

function exportProjectTransmissionHistory() {
    if (!lastProjectTransmissionHistory || lastProjectTransmissionHistory.length === 0) {
        showNotification('No hay datos para exportar', 'warning');
        return;
    }
    
    try {
        const csvContent = 'data:text/csv;charset=utf-8,' + 
            'Dispositivo,Referencia,Conexión,Estado,Tipo,Fila,Fecha,Error\n' +
            lastProjectTransmissionHistory.map(item => {
                const timestamp = item.timestamp || item.transmission_time || item.sent_at || item.created_at;
                return [
                    item.device_name,
                    item.device_reference,
                    item.connection_name,
                    item.status,
                    item.transmission_type,
                    item.row_index || '',
                    timestamp,
                    item.error_message || ''
                ].map(field => `"${field}"`).join(',');
            }).join('\n');
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `historial_proyecto_${currentProject.name}_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('Historial exportado correctamente', 'success');
    } catch (e) {
        showNotification('Error exportando historial: ' + e.message, 'error');
    }
}

// Device management for projects
async function showAddDevicesModal() {
    if (!currentProject) return;
    
    try {
        const modal = document.getElementById('add-devices-modal');
        const selector = document.getElementById('unassigned-devices-selector');
        
        if (!modal || !selector) return;
        
        // Load unassigned devices
        const devices = await API.getUnassignedDevices();
        
        if (!devices || devices.length === 0) {
            selector.innerHTML = '<div class="empty-state">No hay dispositivos disponibles para asignar</div>';
        } else {
            selector.innerHTML = devices.map(device => `
                <div class="device-checkbox-item">
                    <input type="checkbox" id="device-${device.id}" value="${device.id}">
                    <label for="device-${device.id}">
                        <strong>${device.name}</strong>
                        <span class="device-reference">Ref: ${device.reference}</span>
                        <span class="device-type">Tipo: ${device.device_type}</span>
                    </label>
                </div>
            `).join('');
        }
        
        modal.style.display = 'block';
        
    } catch (error) {
        console.error('Error loading unassigned devices:', error);
        showNotification('Error cargando dispositivos disponibles', 'error');
    }
}

async function addSelectedDevicesToProject() {
    if (!currentProject) return;
    
    try {
        const checkboxes = document.querySelectorAll('#unassigned-devices-selector input[type="checkbox"]:checked');
        const deviceIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
        
        if (deviceIds.length === 0) {
            showNotification('Selecciona al menos un dispositivo', 'warning');
            return;
        }
        
        const result = await API.addDevicesToProject(currentProject.id, deviceIds);
        
        // Show results
        const successCount = result.results.filter(r => r.status === 'SUCCESS').length;
        const failedCount = result.results.filter(r => r.status === 'FAILED').length;
        
        if (successCount > 0) {
            showNotification(`${successCount} dispositivos agregados correctamente`, 'success');
            await loadProjectDevices(currentProject.id);
        }
        
        if (failedCount > 0) {
            showNotification(`${failedCount} dispositivos no pudieron ser agregados`, 'warning');
        }
        
        hideAddDevicesModal();
        
    } catch (error) {
        console.error('Error adding devices to project:', error);
        showNotification('Error agregando dispositivos al proyecto', 'error');
    }
}

async function removeDeviceFromProject(deviceId) {
    if (!currentProject || !confirm('¿Estás seguro de que quieres remover este dispositivo del proyecto?')) {
        return;
    }
    
    try {
        await API.removeDeviceFromProject(currentProject.id, deviceId);
        showNotification('Dispositivo removido del proyecto', 'success');
        await loadProjectDevices(currentProject.id);
        
    } catch (error) {
        console.error('Error removing device from project:', error);
        showNotification('Error removiendo dispositivo del proyecto', 'error');
    }
}

// Modal management
function hideAddDevicesModal() {
    const modal = document.getElementById('add-devices-modal');
    if (modal) modal.style.display = 'none';
}

function showOperationResults(operation, result) {
    const modal = document.getElementById('operation-results-modal');
    const title = modal.querySelector('.operation-title');
    const summary = modal.querySelector('.operation-summary');
    const details = modal.querySelector('.operation-details');
    
    if (!modal || !title || !summary || !details) return;
    
    title.textContent = `Resultado: ${operation}`;
    summary.innerHTML = `
        <div class="result-summary">
            <span class="total">Total: ${result.total_devices}</span>
            <span class="success">Éxitos: ${result.successful_operations}</span>
            <span class="failed">Fallos: ${result.failed_operations}</span>
        </div>
    `;
    
    details.innerHTML = result.results.map(r => `
        <div class="device-result ${r.status.toLowerCase()}">
            <strong>${r.device_name}</strong>
            <span class="status">${r.status}</span>
            <span class="message">${r.message}</span>
        </div>
    `).join('');
    
    modal.style.display = 'block';
}

function hideOperationResultsModal() {
    const modal = document.getElementById('operation-results-modal');
    if (modal) modal.style.display = 'none';
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
        if (view) view.classList.remove('active');
    });
    
    // Show selected view
    if (views[viewName]) {
        views[viewName].classList.add('active');
    }
    
    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`nav-${viewName.replace('List', 's').replace('Detail', '').replace('Form', '').replace('Create', '')}`);
    if (activeBtn) activeBtn.classList.add('active');
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
        devices = await API.getDevices(); // Store in global variable
        renderDevices(devices);
    } catch (error) {
        showNotification('Error al cargar dispositivos: ' + error.message, 'error');
    } finally {
        elements.devicesLoading.style.display = 'none';
    }
}

function renderDevices(devicesArray) {
    // Also update global devices array when rendering
    devices = devicesArray;
    
    if (devicesArray.length === 0) {
        elements.devicesGrid.innerHTML = '<div class="loading">No hay dispositivos creados</div>';
        return;
    }

    elements.devicesGrid.innerHTML = devicesArray.map(device => `
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
                    ${window.i18n.t('common.actions.view_details')}
                </button>
                <button class="btn btn-secondary btn-small" onclick="showDuplicateModal(${device.id})">
                    ${window.i18n.t('common.actions.duplicate')}
                </button>
                <button class="btn btn-danger btn-small" onclick="showDeleteModal(${device.id})">
                    ${window.i18n.t('common.actions.delete')}
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
        
        // Initialize modern layout functionality
        setTimeout(() => {
            initializeUploadArea();
            initializePreviewTabs();
        }, 100);
        
        showView('deviceDetail');
    } catch (error) {
        showNotification('Error al cargar dispositivo: ' + error.message, 'error');
    }
}

function renderDeviceDetail(device) {
    // Update header elements
    document.getElementById('device-detail-title').textContent = device.name;
    document.getElementById('device-reference').textContent = device.reference;
    
    // Update status badge
    const statusText = device.csv_data ? 'Datos cargados' : 'Sin datos CSV';
    const statusBadge = document.getElementById('device-status-badge');
    const statusTextElement = document.getElementById('device-status-text');
    
    if (statusTextElement) {
        statusTextElement.textContent = statusText;
    }
    
    if (statusBadge) {
        if (device.csv_data) {
            statusBadge.style.background = 'rgba(34,197,94,0.12)';
            statusBadge.style.color = 'var(--success)';
            statusBadge.querySelector('.status-dot').style.background = 'var(--success)';
        } else {
            statusBadge.style.background = 'rgba(156,163,175,0.12)';
            statusBadge.style.color = 'var(--muted)';
            statusBadge.querySelector('.status-dot').style.background = 'var(--muted)';
        }
    }
    
    // Update info panel with new structure
    elements.deviceInfo.innerHTML = `
        <div class="info-item">
            <span class="info-label">Referencia</span>
            <span class="info-value">${device.reference}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Nombre</span>
            <span class="info-value">${device.name}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Descripción</span>
            <span class="info-value">${device.description || 'Sin descripción'}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Creado</span>
            <span class="info-value">${formatDate(device.created_at)}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Estado CSV</span>
            <span class="info-value">${device.csv_data ? 'Datos cargados' : 'Sin datos'}</span>
        </div>
    `;

    // Initialize preview tabs functionality
    initializePreviewTabs();

    // If device already has CSV data saved, render previews by default
    const sendBtn = document.getElementById('btn-send-data');
    if (device.csv_data) {
        csvPreviewData = device.csv_data;
        // Render CSV table and JSON preview
        elements.csvPreviewTable.innerHTML = renderCSVPreview(csvPreviewData);
        updatePreviewContent('csv'); // Show CSV by default
        elements.previewSection.style.display = 'block';
        if (sendBtn) sendBtn.style.display = 'inline-block';
    } else {
        // Hide preview if no data
        elements.csvPreviewTable.innerHTML = '';
        elements.previewSection.style.display = 'none';
        if (sendBtn) sendBtn.style.display = 'none';
    }
}

// Initialize preview tabs functionality
function initializePreviewTabs() {
    const tabs = document.querySelectorAll('.preview-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active to clicked tab
            tab.classList.add('active');
            
            // Update content based on tab
            const tabType = tab.getAttribute('data-tab');
            updatePreviewContent(tabType);
        });
    });
}

// Update preview content based on tab selection
function updatePreviewContent(tabType) {
    const content = document.getElementById('preview-content');
    if (!content || !csvPreviewData) return;
    
    if (tabType === 'csv') {
        content.innerHTML = `
            <div class="table-container">
                <table id="csv-preview-table" class="preview-table">
                    ${renderCSVPreview(csvPreviewData)}
                </table>
            </div>
        `;
    } else if (tabType === 'json') {
        content.innerHTML = `
            <pre class="json-preview">${JSON.stringify(csvPreviewData.json_preview || [], null, 2)}</pre>
        `;
    }
}

// Initialize upload functionality for modern layout
function initializeUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('csv-file-input');
    const uploadLink = uploadArea?.querySelector('.upload-link');

    if (!uploadArea || !fileInput) return;

    // Click to select file
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // Drag and drop functionality
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
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
        // Update preview content with new structure
        updatePreviewContent('csv'); // Show CSV by default
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
function initializeEventListeners() {
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

    document.getElementById('nav-projects').addEventListener('click', () => {
        setActiveNav('projects');
        showView('projectsList');
        loadProjects();
    });

    // Connection event listeners
    document.getElementById('btn-new-connection').addEventListener('click', () => {
        editingConnection = null;
        document.getElementById('connection-form-title').textContent = '🔌 Nueva Conexión';
        document.getElementById('connection-submit-text').textContent = '💾 Crear Conexión';
        document.getElementById('connection-form').reset();
        clearAuthFields();
        clearAdvancedFields();
        updateConfigPreview();
        updateTestButtonState();
        showView('connectionForm');
    });

    document.getElementById('btn-back-to-connections').addEventListener('click', () => {
        showView('connectionsList');
    });

    document.getElementById('btn-back-from-connection-detail').addEventListener('click', () => {
        showView('connectionsList');
    });

    // Edit connection from detail view
    document.getElementById('btn-edit-connection').addEventListener('click', () => {
        if (currentConnection) {
            editConnection(currentConnection.id);
        }
    });

    document.getElementById('btn-cancel-connection').addEventListener('click', () => {
        document.getElementById('connection-form').reset();
        showView('connectionsList');
    });

    // Connection form handlers
    document.getElementById('connection-type').addEventListener('change', handleConnectionTypeChange);
    document.getElementById('auth-type').addEventListener('change', handleAuthTypeChange);
    
    // Advanced toggle handler
    const toggleAdvanced = document.getElementById('toggle-advanced');
    if (toggleAdvanced) {
        toggleAdvanced.addEventListener('click', function() {
            const advancedConfig = document.getElementById('advanced-config');
            const icon = this.querySelector('.toggle-icon');
            if (advancedConfig.classList.contains('hidden')) {
                advancedConfig.classList.remove('hidden');
                icon.textContent = '▲';
            } else {
                advancedConfig.classList.add('hidden');
                icon.textContent = '▼';
            }
        });
    }
    
    // Form input listeners for config preview
    document.addEventListener('input', function(e) {
        if (e.target.closest('#connection-form')) {
            updateConfigPreview();
            updateTestButtonState();
        }
    });
    
    document.addEventListener('change', function(e) {
        if (e.target.closest('#connection-form')) {
            updateConfigPreview();
            updateTestButtonState();
        }
    });

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
}

// Navigation functions
function setActiveNav(section) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`nav-${section}`).classList.add('active');
}

// Connection functions
async function loadConnections() {
    const grid = document.getElementById('connections-grid');
    const loading = document.getElementById('connections-loading');
    
    if (!grid) {
        console.warn('connections-grid element not found, skipping load');
        return;
    }
    
    if (!loading) {
        console.warn('connections-loading element not found, continuing without loading indicator');
    }
    
    try {
        if (loading) {
            loading.style.display = 'block';
        }
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
                <button class="btn btn-info btn-sm" onclick="viewConnection(${connection.id})">${window.i18n.t('common.actions.view_details')}</button>
                <button class="btn btn-warning btn-sm" onclick="editConnection(${connection.id})">${window.i18n.t('common.actions.edit')}</button>
                <button class="btn btn-success btn-sm" onclick="testConnection(${connection.id})">${window.i18n.t('connections.actions.test_connection')}</button>
                <button class="btn btn-danger btn-sm" onclick="deleteConnection(${connection.id})">${window.i18n.t('common.actions.delete')}</button>
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
        
        // Show the form view first to ensure elements exist
        showView('connectionForm');
        
        // Use setTimeout to ensure DOM is ready
        setTimeout(() => {
            try {
                const titleElement = document.getElementById('connection-form-title');
                const submitTextElement = document.getElementById('connection-submit-text');
                
                if (titleElement) titleElement.textContent = '🔌 Editar Conexión';
                if (submitTextElement) submitTextElement.textContent = '💾 Actualizar Conexión';
                
                // Fill form with connection data
                const nameField = document.getElementById('connection-name');
                const descField = document.getElementById('connection-description');
                const typeField = document.getElementById('connection-type');
                const hostField = document.getElementById('connection-host');
                const portField = document.getElementById('connection-port');
                const endpointField = document.getElementById('connection-endpoint');
                const authTypeField = document.getElementById('auth-type');
                
                if (nameField) nameField.value = connection.name;
                if (descField) descField.value = connection.description || '';
                if (typeField) typeField.value = connection.type;
                if (hostField) hostField.value = connection.host;
                if (portField) portField.value = connection.port || '';
                if (endpointField) endpointField.value = connection.endpoint || '';
                if (authTypeField) authTypeField.value = connection.auth_type;
                
                // Fill advanced fields if available
                if (connection.timeout) {
                    const timeoutField = document.getElementById('connection-timeout');
                    if (timeoutField) timeoutField.value = connection.timeout;
                }
                if (connection.retries) {
                    const retriesField = document.getElementById('connection-retries');
                    if (retriesField) retriesField.value = connection.retries;
                }
                if (connection.additional_headers) {
                    const headersField = document.getElementById('connection-headers');
                    if (headersField) headersField.value = JSON.stringify(connection.additional_headers, null, 2);
                }
                
                // Trigger change events to show appropriate fields
                handleConnectionTypeChange();
                handleAuthTypeChange();
                
                // Fill auth config if available
                if (connection.auth_config) {
                    fillAuthFields(connection.auth_config);
                }
                
                // Update preview and test button
                updateConfigPreview();
                updateTestButtonState();
                
            } catch (domError) {
                console.error('Error filling form fields:', domError);
                showNotification('Error llenando formulario: ' + domError.message, 'error');
            }
        }, 100);
        
        
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
    updateConfigPreview();
}

function showAuthFields(authType) {
    // Hide all auth field sections
    document.querySelectorAll('.connection-auth-fields').forEach(field => {
        field.classList.add('hidden');
    });

    // Show the appropriate section based on auth type
    if (authType !== 'NONE') {
        const targetField = document.getElementById(`auth-${authType.toLowerCase().replace('_', '-')}`);
        if (targetField) {
            targetField.classList.remove('hidden');
        }
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
                    <select class="filter-select" id="mqtt-qos" name="qos">
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
                    <select class="filter-select" id="https-method" name="method">
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
    // Clear all auth field sections in the new structure
    document.querySelectorAll('.connection-auth-fields').forEach(field => {
        field.classList.add('hidden');
        // Clear input values within each section
        field.querySelectorAll('input, select, textarea').forEach(input => {
            input.value = '';
        });
    });
}

function clearAdvancedFields() {
    const advancedConfig = document.getElementById('advanced-config');
    if (advancedConfig) {
        advancedConfig.classList.add('hidden');
        // Clear input values within advanced section
        advancedConfig.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
        });
    }
}

function fillAuthFields(authConfig) {
    // Fill auth fields based on current auth type and config
    const authType = document.getElementById('auth-type').value;
    
    if (authType === 'USER_PASS' && authConfig.username) {
        const usernameField = document.getElementById('auth-username');
        const passwordField = document.getElementById('auth-password');
        if (usernameField) usernameField.value = authConfig.username;
        if (passwordField && authConfig.password) passwordField.value = authConfig.password;
    } else if (authType === 'TOKEN' && authConfig.token) {
        const tokenField = document.getElementById('auth-token-value');
        if (tokenField) tokenField.value = authConfig.token;
    } else if (authType === 'API_KEY' && authConfig.key) {
        const headerField = document.getElementById('api-key-header');
        const keyField = document.getElementById('api-key-value');
        if (headerField && authConfig.header_name) headerField.value = authConfig.header_name;
        if (keyField) keyField.value = authConfig.key;
    }
}

function updateTestButtonState() {
    const testBtn = document.getElementById('btn-test-connection');
    if (!testBtn) return;
    
    const nameField = document.getElementById('connection-name');
    const typeField = document.getElementById('connection-type');
    const hostField = document.getElementById('connection-host');
    const authTypeField = document.getElementById('auth-type');
    
    if (!nameField || !typeField || !hostField || !authTypeField) return;
    
    const name = nameField.value;
    const type = typeField.value;
    const host = hostField.value;
    const authType = authTypeField.value;
    
    testBtn.disabled = !(name && type && host && authType);
}

function updateConfigPreview() {
    const configPreview = document.getElementById('config-preview');
    if (!configPreview) return;
    
    const nameField = document.getElementById('connection-name');
    const typeField = document.getElementById('connection-type');
    const hostField = document.getElementById('connection-host');
    const portField = document.getElementById('connection-port');
    const endpointField = document.getElementById('connection-endpoint');
    const authTypeField = document.getElementById('auth-type');
    const timeoutField = document.getElementById('connection-timeout');
    const retriesField = document.getElementById('connection-retries');
    
    if (!nameField || !typeField || !hostField || !authTypeField) return;
    
    const config = {
        name: nameField.value || "",
        type: typeField.value || "",
        host: hostField.value || "",
        port: portField ? portField.value || null : null,
        endpoint: endpointField ? endpointField.value || "" : "",
        auth_type: authTypeField.value || "NONE",
        timeout: timeoutField ? timeoutField.value || 30 : 30,
        retries: retriesField ? retriesField.value || 3 : 3
    };
    
    // Add auth config based on type
    const authType = config.auth_type;
    if (authType === 'USER_PASS') {
        const username = document.getElementById('auth-username');
        const password = document.getElementById('auth-password');
        if (username && password) {
            config.auth_config = {
                username: username.value || "",
                password: password.value ? "••••••••" : ""
            };
        }
    } else if (authType === 'TOKEN') {
        const token = document.getElementById('auth-token-value');
        if (token) {
            config.auth_config = {
                token: token.value ? "••••••••" : ""
            };
        }
    } else if (authType === 'API_KEY') {
        const header = document.getElementById('api-key-header');
        const key = document.getElementById('api-key-value');
        if (header && key) {
            config.auth_config = {
                header_name: header.value || "X-API-Key",
                api_key: key.value ? "••••••••" : ""
            };
        }
    }
    
    // Add additional headers if present
    const additionalHeaders = document.getElementById('connection-headers');
    if (additionalHeaders && additionalHeaders.value.trim()) {
        try {
            config.additional_headers = JSON.parse(additionalHeaders.value);
        } catch (e) {
            config.additional_headers = "Invalid JSON";
        }
    }
    
    configPreview.textContent = JSON.stringify(config, null, 2);
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
        const includeDeviceIdEl = document.getElementById('include-device-id');
        if (includeDeviceIdEl) includeDeviceIdEl.checked = !!config.include_device_id_in_payload;
        
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
    const includeDeviceId = document.getElementById('include-device-id')?.checked || false;
    
    try {
        const response = await fetch(`${API_BASE}/devices/${currentDevice.id}/transmission-config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_type: deviceType,
                transmission_frequency: frequency,
                transmission_enabled: enabled,
                connection_id: connectionId || null,
                include_device_id_in_payload: includeDeviceId
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

// Removed - consolidated into main DOMContentLoaded handler

// Event Listeners for Transmission Controls - Will be initialized by main DOMContentLoaded handler
function initializeTransmissionControls() {
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
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });

    // Project event listeners
    document.getElementById('btn-new-project').addEventListener('click', () => {
        currentProject = null;
        document.getElementById('project-form-title').textContent = 'Nuevo Proyecto';
        document.getElementById('project-submit-text').textContent = 'Crear Proyecto';
        document.getElementById('project-form').reset();
        showView('projectForm');
    });

    document.getElementById('btn-back-to-projects').addEventListener('click', () => {
        showView('projectsList');
        loadProjects();
    });

    document.getElementById('btn-back-from-project-detail').addEventListener('click', () => {
        showView('projectsList');
        loadProjects();
    });

    document.getElementById('btn-edit-project').addEventListener('click', () => {
        if (!currentProject) return;
        
        document.getElementById('project-form-title').textContent = 'Editar Proyecto';
        document.getElementById('project-submit-text').textContent = 'Actualizar Proyecto';
        document.getElementById('project-name').value = currentProject.name;
        document.getElementById('project-description').value = currentProject.description || '';
        showView('projectForm');
    });

    document.getElementById('btn-delete-project').addEventListener('click', async () => {
        if (!currentProject || !confirm(`¿Estás seguro de que quieres eliminar el proyecto "${currentProject.name}"?`)) {
            return;
        }
        
        try {
            await API.deleteProject(currentProject.id);
            showNotification('Proyecto eliminado correctamente', 'success');
            showView('projectsList');
            loadProjects();
        } catch (error) {
            console.error('Error deleting project:', error);
            showNotification('Error eliminando proyecto', 'error');
        }
    });

    // Project form submission
    document.getElementById('project-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name').trim(),
            description: formData.get('description').trim()
        };
        
        if (!data.name) {
            showNotification('El nombre del proyecto es requerido', 'error');
            return;
        }
        
        try {
            if (currentProject) {
                // Update existing project
                await API.updateProject(currentProject.id, data);
                showNotification('Proyecto actualizado correctamente', 'success');
            } else {
                // Create new project
                await API.createProject(data);
                showNotification('Proyecto creado correctamente', 'success');
            }
            
            showView('projectsList');
            loadProjects();
            
        } catch (error) {
            console.error('Error saving project:', error);
            const errorMsg = error.message || 'Error guardando proyecto';
            showNotification(errorMsg, 'error');
        }
    });

    document.getElementById('btn-cancel-project').addEventListener('click', () => {
        showView('projectsList');
        loadProjects();
    });

    // Project transmission control buttons
    document.getElementById('btn-start-project-transmission').addEventListener('click', startProjectTransmission);
    document.getElementById('btn-pause-project-transmission').addEventListener('click', pauseProjectTransmission);
    document.getElementById('btn-resume-project-transmission').addEventListener('click', resumeProjectTransmission);
    document.getElementById('btn-stop-project-transmission').addEventListener('click', stopProjectTransmission);

    // Project device management
    document.getElementById('btn-add-devices-to-project').addEventListener('click', showAddDevicesModal);
    document.getElementById('btn-confirm-add-devices').addEventListener('click', addSelectedDevicesToProject);
    document.getElementById('btn-cancel-add-devices').addEventListener('click', hideAddDevicesModal);

    // Device duplication event listeners
    document.getElementById('duplicate-count').addEventListener('input', updateDuplicatePreview);
    document.getElementById('btn-confirm-duplicate').addEventListener('click', confirmDuplicateDevice);
    document.getElementById('btn-cancel-duplicate').addEventListener('click', hideDuplicateModal);

    // Device deletion event listeners
    document.getElementById('btn-confirm-delete').addEventListener('click', confirmDeleteDevice);
    document.getElementById('btn-cancel-delete').addEventListener('click', hideDeleteModal);
}

// Project CRUD functions
async function editProject(projectId) {
    try {
        const project = await API.getProject(projectId);
        if (!project) {
            showNotification('Proyecto no encontrado', 'error');
            return;
        }
        
        currentProject = project;
        document.getElementById('project-form-title').textContent = 'Editar Proyecto';
        document.getElementById('project-submit-text').textContent = 'Actualizar Proyecto';
        document.getElementById('project-name').value = project.name;
        document.getElementById('project-description').value = project.description || '';
        showView('projectForm');
        
    } catch (error) {
        console.error('Error loading project for edit:', error);
        showNotification('Error cargando proyecto', 'error');
    }
}

async function deleteProject(projectId) {
    try {
        const project = await API.getProject(projectId);
        if (!project) {
            showNotification('Proyecto no encontrado', 'error');
            return;
        }
        
        if (!confirm(`¿Estás seguro de que quieres eliminar el proyecto "${project.name}"?`)) {
            return;
        }
        
        await API.deleteProject(projectId);
        showNotification('Proyecto eliminado correctamente', 'success');
        loadProjects();
        
    } catch (error) {
        console.error('Error deleting project:', error);
        showNotification('Error eliminando proyecto', 'error');
    }
}

// Initialize visualization tabs
// (Device analytics/dashboard removed by design)

// Device Duplication Functions
let currentDeviceForDuplication = null;

async function showDuplicateModal(deviceId) {
    currentDeviceForDuplication = deviceId;
    
    // Find device in current devices list to get name
    let device = devices.find(d => d.id === deviceId);
    
    // If device not found in current array, fetch it from API
    if (!device) {
        try {
            device = await API.getDevice(deviceId);
        } catch (error) {
            console.error('Error fetching device:', error);
            showNotification('Error al cargar dispositivo', 'error');
            return;
        }
    }
    
    if (!device) {
        showNotification('Dispositivo no encontrado', 'error');
        return;
    }
    
    console.log('Found device for duplication:', device.name);
    
    // Show modal first to ensure DOM elements exist
    document.getElementById('duplicate-device-modal').classList.add('active');
    
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
        const deviceNameElement = document.getElementById('device-name-to-duplicate');
        const duplicateCountElement = document.getElementById('duplicate-count');
        
        if (deviceNameElement) {
            deviceNameElement.textContent = device.name;
        }
        if (duplicateCountElement) {
            duplicateCountElement.value = 1;
        }
        updateDuplicatePreview();
    }, 50);
}

function hideDuplicateModal() {
    document.getElementById('duplicate-device-modal').classList.remove('active');
    currentDeviceForDuplication = null;
}

function updateDuplicatePreview() {
    const countElement = document.getElementById('duplicate-count');
    const previewList = document.getElementById('duplicate-names-preview');
    
    if (!countElement || !previewList) return;
    
    const count = parseInt(countElement.value) || 1;
    
    // Get device name from the modal display instead of searching the array
    const deviceNameElement = document.getElementById('device-name-to-duplicate');
    const deviceName = deviceNameElement ? deviceNameElement.textContent : 'Dispositivo';
    
    previewList.innerHTML = '';
    
    for (let i = 1; i <= Math.min(count, 50); i++) {
        const li = document.createElement('li');
        li.textContent = `${deviceName} ${i}`;
        previewList.appendChild(li);
    }
}

async function confirmDuplicateDevice() {
    if (!currentDeviceForDuplication) return;
    
    const count = parseInt(document.getElementById('duplicate-count').value);
    
    if (!count || count < 1 || count > 50) {
        showNotification('El número de duplicados debe estar entre 1 y 50', 'error');
        return;
    }
    
    try {
        showNotification('Duplicando dispositivo...', 'info');
        
        const result = await API.duplicateDevice(currentDeviceForDuplication, count);
        
        hideDuplicateModal();
        
        showNotification(
            `Dispositivo duplicado exitosamente. ${result.duplicates_created} copias creadas.`,
            'success'
        );
        
        // Reload devices list to show new duplicates
        loadDevices();
        
    } catch (error) {
        console.error('Error duplicating device:', error);
        showNotification('Error duplicando dispositivo: ' + error.message, 'error');
    }
}

// Delete Device Modal Functions
let currentDeviceForDeletion = null;

async function showDeleteModal(deviceId) {
    currentDeviceForDeletion = deviceId;
    
    // Find device in current devices list to get name
    let device = devices.find(d => d.id === deviceId);
    
    // If device not found in current array, fetch it from API
    if (!device) {
        try {
            device = await API.getDevice(deviceId);
        } catch (error) {
            console.error('Error fetching device:', error);
            showNotification('Error al cargar dispositivo', 'error');
            return;
        }
    }
    
    if (!device) {
        showNotification('Dispositivo no encontrado', 'error');
        return;
    }
    
    console.log('Found device for deletion:', device.name);
    
    // Show modal first to ensure DOM elements exist
    document.getElementById('delete-device-modal').classList.add('active');
    
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
        const deviceNameElement = document.getElementById('device-name-to-delete');
        if (deviceNameElement) {
            deviceNameElement.textContent = device.name;
        }
    }, 50);
}

function hideDeleteModal() {
    document.getElementById('delete-device-modal').classList.remove('active');
    currentDeviceForDeletion = null;
}

async function confirmDeleteDevice() {
    if (!currentDeviceForDeletion) {
        showNotification('Error: No hay dispositivo seleccionado para eliminar', 'error');
        return;
    }

    // Disable buttons during deletion
    const confirmBtn = document.getElementById('btn-confirm-delete');
    const cancelBtn = document.getElementById('btn-cancel-delete');
    const originalConfirmText = confirmBtn.textContent;
    
    confirmBtn.disabled = true;
    cancelBtn.disabled = true;
    confirmBtn.textContent = 'Eliminando...';

    try {
        const response = await API.deleteDevice(currentDeviceForDeletion);
        
        if (response.ok) {
            const result = await response.json();
            hideDeleteModal();
            showNotification('Dispositivo eliminado correctamente', 'success');
            
            // Refresh devices list
            await loadDevices();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Error al eliminar dispositivo', 'error');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        showNotification('Error de conexión al eliminar dispositivo', 'error');
    } finally {
        // Re-enable buttons
        confirmBtn.disabled = false;
        cancelBtn.disabled = false;
        confirmBtn.textContent = originalConfirmText;
    }
}

// Global functions for onclick handlers
window.viewDevice = viewDevice;
window.viewConnection = viewConnection;
window.editConnection = editConnection;
window.testConnection = testConnection;
window.showDuplicateModal = showDuplicateModal;
window.hideDuplicateModal = hideDuplicateModal;
window.showDeleteModal = showDeleteModal;
window.hideDeleteModal = hideDeleteModal;
window.deleteConnection = deleteConnection;
window.showProjectDetail = showProjectDetail;
window.editProject = editProject;
window.deleteProject = deleteProject;
window.removeDeviceFromProject = removeDeviceFromProject;
window.refreshProjectTransmissionHistory = refreshProjectTransmissionHistory;
window.exportProjectTransmissionHistory = exportProjectTransmissionHistory;
window.hideOperationResultsModal = hideOperationResultsModal;
window.selectConnection = selectConnection;
window.selectTransmitConnection = selectTransmitConnection;

// Initialize i18n system when DOM is loaded
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 Initializing Device Simulator with i18n support');
    
    try {
        // Initialize i18n system
        await window.i18n.initialize();
        
        // Setup language selector
        initializeLanguageSelector();
        
        // Initialize the rest of the application
        await initializeApp();
        
        console.log('✅ Device Simulator initialized successfully');
    } catch (error) {
        console.error('❌ Error initializing Device Simulator:', error);
        showNotification('Error al inicializar la aplicación', 'error');
    }
});

// Initialize language selector functionality
function initializeLanguageSelector() {
    const languageSelector = document.getElementById('language-selector');
    
    if (languageSelector) {
        languageSelector.addEventListener('click', async () => {
            const currentLang = window.i18n.getCurrentLanguage();
            const newLang = currentLang === 'es' ? 'en' : 'es';
            
            try {
                await window.i18n.changeLanguage(newLang);
                
                // Show notification about language change
                const message = newLang === 'es' 
                    ? 'Idioma cambiado a Español' 
                    : 'Language changed to English';
                showNotification(message, 'success');
                
                // Update dynamic content that might not be covered by data-i18n
                updateDynamicTranslations();
                
            } catch (error) {
                console.error('Error changing language:', error);
                showNotification('Error al cambiar idioma', 'error');
            }
        });
    }
    
    // Listen for language change events
    document.addEventListener('languageChanged', (event) => {
        console.log('🌐 Language changed to:', event.detail.language);
        updateDynamicTranslations();
    });
}

// Update translations for dynamically generated content
function updateDynamicTranslations() {
    // Update loading messages
    const devicesLoading = document.getElementById('devices-loading');
    if (devicesLoading) {
        devicesLoading.textContent = window.i18n.t('devices.messages.loading_devices');
    }
    
    const connectionsLoading = document.getElementById('connections-loading');
    if (connectionsLoading) {
        connectionsLoading.textContent = window.i18n.t('connections.messages.loading_connections');
    }
    
    const projectsLoading = document.getElementById('projects-loading');
    if (projectsLoading) {
        projectsLoading.textContent = window.i18n.t('projects.messages.loading_projects');
    }
    
    // Re-render current view content if needed
    if (devices.length > 0) {
        renderDevices();
    }
    if (connections.length > 0) {
        renderConnections();
    }
}

// Initialize sidebar navigation
function initializeDefaultNavigation() {
    // Navigation
    document.getElementById('nav-devices').addEventListener('click', () => {
        setActiveNav('devices');
        showView('devicesList');
        loadDevices();
    });

    document.getElementById('nav-projects').addEventListener('click', () => {
        setActiveNav('projects');
        showView('projectsList');
        loadProjects();
    });

    document.getElementById('nav-connections').addEventListener('click', () => {
        setActiveNav('connections');
        showView('connectionsList');
        loadConnections();
    });

    // Set default active navigation
    setActiveNav('devices');
    showView('devicesList');
}

// Initialize the main application
async function initializeApp() {
    // Initialize sidebar navigation
    initializeDefaultNavigation();
    
    // Load initial data
    await loadDevices();
    await loadConnections();
    
    // Initialize forms and event listeners
    initializeEventListeners();
    
    // Initialize transmission controls
    initializeTransmissionControls();
    
    // Initialize transmission API if available
    if (typeof TransmissionAPI !== 'undefined') {
        transmissionAPI = new TransmissionAPI(API_BASE);
    }
    
    // Initialize real-time monitoring if available
    if (typeof RealtimeMonitor !== 'undefined') {
        realtimeMonitor = new RealtimeMonitor();
        realtimeMonitor.connect();
    }
}
