/**
 * Keycloak Authentication Manager for Device Simulator
 * Handles OAuth2 flow, token management, and redirects to Keycloak login
 */

class KeycloakAuthManager {
    constructor() {
        this.config = null;
        this.accessToken = null;
        this.refreshToken = null;
        this.user = null;
        this.tokenExpirationTimer = null;
        
        // Storage keys
        this.ACCESS_TOKEN_KEY = 'keycloak_access_token';
        this.REFRESH_TOKEN_KEY = 'keycloak_refresh_token';
        this.USER_KEY = 'keycloak_user';
        
        // Initialize on construction
        this.init();
    }
    
    async init() {
        console.log('🔐 Initializing Keycloak Authentication Manager...');
        
        try {
            // Load configuration from backend
            await this.loadConfig();
            
            // Restore tokens from storage
            this.restoreTokensFromStorage();
            
            // Handle OAuth callback if present
            await this.handleOAuthCallback();
            
            // Check if authentication is required
            if (this.config?.enabled) {
                await this.checkAuthenticationStatus();
            }
            
            // Ensure UI reflects current auth state after init
            this.updateAuthenticationUI();

            console.log('✅ Keycloak Authentication Manager initialized');
        } catch (error) {
            console.error('❌ Failed to initialize Keycloak Auth Manager:', error);
        }
    }
    
    async loadConfig() {
        try {
            const response = await fetch('/api/auth/config');
            if (!response.ok) {
                throw new Error(`Config request failed: ${response.status}`);
            }
            
            this.config = await response.json();
            console.log('📋 Keycloak config loaded:', {
                enabled: this.config.enabled,
                realm: this.config.realm,
                client_id: this.config.client_id
            });
        } catch (error) {
            console.error('Failed to load Keycloak config:', error);
            this.config = { enabled: false };
        }
    }
    
    restoreTokensFromStorage() {
        this.accessToken = localStorage.getItem(this.ACCESS_TOKEN_KEY);
        this.refreshToken = localStorage.getItem(this.REFRESH_TOKEN_KEY);
        
        const userStr = localStorage.getItem(this.USER_KEY);
        if (userStr) {
            try {
                this.user = JSON.parse(userStr);
            } catch (error) {
                console.warn('Failed to parse stored user data');
                localStorage.removeItem(this.USER_KEY);
            }
        }
        
        if (this.accessToken) {
            console.log('🔑 Restored tokens from storage');
        }
    }
    
    async handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const authSuccess = urlParams.get('auth');
        const error = urlParams.get('error');
        
        if (error) {
            console.error('OAuth error:', error);
            this.showAuthError(`Authentication failed: ${error}`);
            this.clearUrlParams();
            return;
        }
        
        if (authSuccess === 'success') {
            console.log('🔄 Authentication successful, retrieving session...');
            
            try {
                const response = await fetch('/api/auth/session', {
                    method: 'GET'
                });
                
                if (!response.ok) {
                    throw new Error(`Session retrieval failed: ${response.status}`);
                }
                
                const data = await response.json();
                this.handleAuthSuccess(data);
                this.clearUrlParams();
                
            } catch (error) {
                console.error('Session retrieval error:', error);
                this.showAuthError('Failed to retrieve session');
                this.clearUrlParams();
            }
        }
    }
    
    clearUrlParams() {
        // Remove OAuth parameters from URL without page reload
        const url = new URL(window.location);
        url.searchParams.delete('code');
        url.searchParams.delete('state');
        url.searchParams.delete('error');
        url.searchParams.delete('auth');
        url.searchParams.delete('session_state');
        url.searchParams.delete('iss');
        window.history.replaceState({}, document.title, url.pathname + url.hash);
    }
    
    async checkAuthenticationStatus() {
        if (!this.config?.enabled) {
            return;
        }
        
        // If we have tokens, validate them
        if (this.accessToken) {
            const isValid = await this.validateToken();
            if (!isValid) {
                // Try to refresh token
                const refreshed = await this.refreshAccessToken();
                if (!refreshed) {
                    this.clearTokens();
                    await this.redirectToLogin();
                }
            }
        } else {
            // No token, redirect to login immediately
            console.log('🔐 No access token found, redirecting to login...');
            await this.redirectToLogin();
        }
    }
    
    async validateToken() {
        if (!this.accessToken) return false;
        
        try {
            const response = await fetch('/api/auth/validate', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) return false;
            
            const data = await response.json();
            return data.valid;
            
        } catch (error) {
            console.error('Token validation error:', error);
            return false;
        }
    }
    
    async refreshAccessToken() {
        if (!this.refreshToken) {
            console.log('No refresh token available');
            return false;
        }
        
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken
                })
            });
            
            if (!response.ok) {
                console.log('Token refresh failed');
                this.clearTokens();
                return false;
            }
            
            const data = await response.json();
            this.handleAuthSuccess(data);
            console.log('🔄 Token refreshed successfully');
            return true;
            
        } catch (error) {
            console.error('Token refresh error:', error);
            this.clearTokens();
            return false;
        }
    }
    
    async redirectToLogin() {
        if (!this.config?.enabled) {
            return;
        }
        
        console.log('🔐 Redirecting to Keycloak login...');
        
        // Use the auth_url from config if available
        if (this.config.auth_url) {
            console.log('Using auth_url from config:', this.config.auth_url);
            window.location.href = this.config.auth_url;
            return;
        }
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    redirect_uri: window.location.origin + '/api/auth/callback'
                })
            });
            
            if (!response.ok) {
                throw new Error(`Login initiation failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Redirect to Keycloak login page
            window.location.href = data.auth_url;
            
        } catch (error) {
            console.error('Login redirect failed:', error);
            this.showAuthError('Unable to initiate login');
        }
    }
    
    handleAuthSuccess(data) {
        console.log('✅ Authentication successful');
        
        this.accessToken = data.access_token;
        this.refreshToken = data.refresh_token;
        this.user = data.user;
        
        // Store tokens
        localStorage.setItem(this.ACCESS_TOKEN_KEY, this.accessToken);
        if (this.refreshToken) {
            localStorage.setItem(this.REFRESH_TOKEN_KEY, this.refreshToken);
        }
        localStorage.setItem(this.USER_KEY, JSON.stringify(this.user));
        
        // Set up token refresh timer
        this.setupTokenRefreshTimer(data.expires_in);
        
        // Notify application of successful authentication
        this.onAuthenticationSuccess();
    }
    
    setupTokenRefreshTimer(expiresIn) {
        if (this.tokenExpirationTimer) {
            clearTimeout(this.tokenExpirationTimer);
        }
        
        // Refresh token 5 minutes before expiration
        const refreshTime = (expiresIn - 300) * 1000;
        
        if (refreshTime > 0) {
            this.tokenExpirationTimer = setTimeout(() => {
                this.refreshAccessToken();
            }, refreshTime);
        }
    }
    
    async logout() {
        console.log('🚪 Logging out...');
        
        try {
            if (this.refreshToken && this.config?.enabled) {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        refresh_token: this.refreshToken
                    })
                });
            }
        } catch (error) {
            console.warn('Logout request failed:', error);
        }
        
        this.clearTokens();
        
        // Redirect to Keycloak logout if enabled
        if (this.config?.enabled && this.config.logout_url) {
            const logoutUrl = `${this.config.logout_url}?redirect_uri=${encodeURIComponent(window.location.origin)}`;
            window.location.href = logoutUrl;
        } else {
            window.location.reload();
        }
    }
    
    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        this.user = null;
        
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        
        if (this.tokenExpirationTimer) {
            clearTimeout(this.tokenExpirationTimer);
            this.tokenExpirationTimer = null;
        }
    }
    
    getAuthHeaders() {
        if (this.accessToken) {
            return {
                'Authorization': `Bearer ${this.accessToken}`
            };
        }
        return {};
    }
    
    isAuthenticated() {
        return !this.config?.enabled || (this.accessToken && this.user);
    }
    
    getCurrentUser() {
        return this.user;
    }
    
    hasRole(role) {
        if (!this.user) return false;
        const roles = [...(this.user.roles || []), ...(this.user.client_roles || [])];
        return roles.includes(role);
    }
    
    hasAnyRole(roles) {
        return roles.some(role => this.hasRole(role));
    }
    
    showAuthError(message) {
        console.error('Authentication Error:', message);
        
        // Create simple error notification
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            padding: 16px;
            border-radius: 4px;
            z-index: 10000;
            max-width: 400px;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    onAuthenticationSuccess() {
        // Dispatch custom event for application to handle
        window.dispatchEvent(new CustomEvent('keycloak-auth-success', {
            detail: { user: this.user }
        }));
        
        // Update UI if needed
        this.updateAuthenticationUI();
    }

    updateAuthenticationUI() {
        const authSection = document.getElementById('auth-section');
        const userInfoElement = document.getElementById('user-info') || document.querySelector('.user-info');
        const logoutButton = document.getElementById('logout-button') || document.querySelector('.logout-button');
        const languageBtn = document.getElementById('language-selector');
        const languageContainer = document.querySelector('.language-selector');

        const isAuthed = this.isAuthenticated();

        // Toggle container visibility
        if (authSection) {
            authSection.style.display = isAuthed ? 'block' : 'none';
        }

        // Render user info
        if (userInfoElement) {
            if (isAuthed && this.user) {
                const username = this.user.username || `${this.user.first_name || ''} ${this.user.last_name || ''}`.trim() || 'Usuario';
                const initials = (() => {
                    const name = username.trim();
                    if (!name) return 'U';
                    const parts = name.split(/\s+/);
                    const first = parts[0]?.charAt(0) || '';
                    const second = parts.length > 1 ? parts[1].charAt(0) : (parts[0]?.charAt(1) || '');
                    return (first + second).toUpperCase();
                })();

                userInfoElement.innerHTML = `
                    <div class="user-avatar">${initials}</div>
                    <div class="user-details">
                        <div class="user-name" title="${username}">${username}</div>
                    </div>
                `;
            } else {
                userInfoElement.innerHTML = '';
            }
        }

        // Ensure there is an actions row inside auth section for logout + language
        let authActions = authSection ? authSection.querySelector('.auth-actions') : null;
        if (isAuthed && authSection) {
            if (!authActions) {
                authActions = document.createElement('div');
                authActions.className = 'auth-actions';
                authSection.appendChild(authActions);
            }

            // Move language selector button into actions row
            if (languageBtn && languageBtn.parentElement !== authActions) {
                authActions.appendChild(languageBtn);
            }

            // Move logout button into actions row
            if (logoutButton && logoutButton.parentElement !== authActions) {
                authActions.appendChild(logoutButton);
            }

        } else {
            // Restore language selector to its original container when not authenticated
            if (languageBtn && languageContainer && languageBtn.parentElement !== languageContainer) {
                languageContainer.appendChild(languageBtn);
            }
        }

        // Wire and toggle logout button
        if (logoutButton) {
            logoutButton.style.display = isAuthed ? 'block' : 'none';
            // Ensure label is translatable (use common namespace: common.auth.logout)
            const labelSpan = logoutButton.querySelector('span[data-i18n="common.auth.logout"]');
            if (!labelSpan) {
                logoutButton.innerHTML = `🚪 <span data-i18n="common.auth.logout">Cerrar Sesión</span>`;
            }
            logoutButton.onclick = () => this.logout();
        }

        // Trigger a global i18n refresh to translate any newly added elements
        if (window.i18n && typeof window.i18n.updateDOM === 'function') {
            window.i18n.updateDOM();
        }
    }
}

// Create global instance
window.keycloakAuth = new KeycloakAuthManager();

// Enhanced fetch function that automatically includes auth headers
window.authenticatedFetch = async function(url, options = {}) {
    const authHeaders = window.keycloakAuth.getAuthHeaders();
    
    const config = {
        ...options,
        headers: {
            ...authHeaders,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 responses by redirecting to login
        if (response.status === 401 && window.keycloakAuth.config?.enabled) {
            console.log('🔒 Received 401, redirecting to login...');
            
            try {
                const errorData = await response.json();
                if (errorData.auth_url) {
                    console.log('Redirecting to Keycloak:', errorData.auth_url);
                    window.location.href = errorData.auth_url;
                    return null;
                }
            } catch (e) {
                console.warn('Could not parse 401 response:', e);
            }
            
            // Fallback: clear tokens and try to redirect
            window.keycloakAuth.clearTokens();
            window.keycloakAuth.redirectToLogin();
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('Authenticated fetch error:', error);
        throw error;
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KeycloakAuthManager;
}
