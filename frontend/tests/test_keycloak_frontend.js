/**
 * Frontend tests for Keycloak authentication
 * Tests the KeycloakAuthManager and authentication flow
 */

// Mock fetch for testing
global.fetch = jest.fn();
global.localStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn()
};

// Mock window.location
delete window.location;
window.location = {
    href: '',
    origin: 'http://localhost',
    pathname: '/',
    search: '',
    hash: ''
};

// Mock URLSearchParams
global.URLSearchParams = class URLSearchParams {
    constructor(search) {
        this.params = new Map();
        if (search) {
            const pairs = search.replace('?', '').split('&');
            pairs.forEach(pair => {
                const [key, value] = pair.split('=');
                if (key) this.params.set(key, decodeURIComponent(value || ''));
            });
        }
    }
    
    get(key) {
        return this.params.get(key);
    }
    
    delete(key) {
        this.params.delete(key);
    }
};

// Import the module to test
const KeycloakAuthManager = require('../static/keycloak-auth.js');

describe('KeycloakAuthManager', () => {
    let authManager;
    
    beforeEach(() => {
        // Reset mocks
        fetch.mockClear();
        localStorage.getItem.mockClear();
        localStorage.setItem.mockClear();
        localStorage.removeItem.mockClear();
        
        // Reset window location
        window.location.search = '';
        window.location.href = 'http://localhost';
        
        // Create new instance
        authManager = new KeycloakAuthManager();
    });
    
    describe('Configuration Loading', () => {
        test('should load configuration from backend', async () => {
            const mockConfig = {
                enabled: true,
                server_url: 'http://localhost:8080',
                realm: 'devsim',
                client_id: 'devsim-app'
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockConfig)
            });
            
            await authManager.loadConfig();
            
            expect(fetch).toHaveBeenCalledWith('/api/auth/config');
            expect(authManager.config).toEqual(mockConfig);
        });
        
        test('should handle config loading failure', async () => {
            fetch.mockRejectedValueOnce(new Error('Network error'));
            
            await authManager.loadConfig();
            
            expect(authManager.config).toEqual({ enabled: false });
        });
    });
    
    describe('Token Management', () => {
        test('should restore tokens from localStorage', () => {
            const mockUser = { username: 'testuser', roles: ['user'] };
            
            localStorage.getItem.mockImplementation((key) => {
                switch (key) {
                    case 'keycloak_access_token': return 'test_access_token';
                    case 'keycloak_refresh_token': return 'test_refresh_token';
                    case 'keycloak_user': return JSON.stringify(mockUser);
                    default: return null;
                }
            });
            
            authManager.restoreTokensFromStorage();
            
            expect(authManager.accessToken).toBe('test_access_token');
            expect(authManager.refreshToken).toBe('test_refresh_token');
            expect(authManager.user).toEqual(mockUser);
        });
        
        test('should handle invalid user data in localStorage', () => {
            localStorage.getItem.mockImplementation((key) => {
                if (key === 'keycloak_user') return 'invalid_json';
                return null;
            });
            
            authManager.restoreTokensFromStorage();
            
            expect(authManager.user).toBeNull();
            expect(localStorage.removeItem).toHaveBeenCalledWith('keycloak_user');
        });
        
        test('should clear tokens', () => {
            authManager.accessToken = 'test_token';
            authManager.refreshToken = 'test_refresh';
            authManager.user = { username: 'test' };
            
            authManager.clearTokens();
            
            expect(authManager.accessToken).toBeNull();
            expect(authManager.refreshToken).toBeNull();
            expect(authManager.user).toBeNull();
            expect(localStorage.removeItem).toHaveBeenCalledTimes(3);
        });
    });
    
    describe('Authentication Flow', () => {
        test('should handle OAuth callback with code', async () => {
            window.location.search = '?code=test_code&state=test_state';
            
            const mockTokenResponse = {
                access_token: 'new_access_token',
                refresh_token: 'new_refresh_token',
                expires_in: 3600,
                user: { username: 'testuser' }
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockTokenResponse)
            });
            
            const handleAuthSuccessSpy = jest.spyOn(authManager, 'handleAuthSuccess');
            
            await authManager.handleOAuthCallback();
            
            expect(fetch).toHaveBeenCalledWith('/api/auth/callback?code=test_code&state=test_state', {
                method: 'GET'
            });
            expect(handleAuthSuccessSpy).toHaveBeenCalledWith(mockTokenResponse);
        });
        
        test('should handle OAuth callback with error', async () => {
            window.location.search = '?error=access_denied';
            
            const showAuthErrorSpy = jest.spyOn(authManager, 'showAuthError');
            const clearUrlParamsSpy = jest.spyOn(authManager, 'clearUrlParams');
            
            await authManager.handleOAuthCallback();
            
            expect(showAuthErrorSpy).toHaveBeenCalledWith('Authentication failed: access_denied');
            expect(clearUrlParamsSpy).toHaveBeenCalled();
        });
        
        test('should initiate login redirect', async () => {
            authManager.config = { enabled: true };
            
            const mockLoginResponse = {
                auth_url: 'http://keycloak/auth?client_id=test&redirect_uri=callback',
                state: 'test_state'
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockLoginResponse)
            });
            
            // Mock window.location.href setter
            const originalHref = window.location.href;
            Object.defineProperty(window.location, 'href', {
                writable: true,
                value: originalHref
            });
            
            await authManager.redirectToLogin();
            
            expect(fetch).toHaveBeenCalledWith('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    redirect_uri: 'http://localhost/api/auth/callback'
                })
            });
        });
    });
    
    describe('Token Validation', () => {
        test('should validate token successfully', async () => {
            authManager.accessToken = 'valid_token';
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ valid: true })
            });
            
            const result = await authManager.validateToken();
            
            expect(result).toBe(true);
            expect(fetch).toHaveBeenCalledWith('/api/auth/validate', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer valid_token',
                    'Content-Type': 'application/json'
                }
            });
        });
        
        test('should handle invalid token', async () => {
            authManager.accessToken = 'invalid_token';
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ valid: false })
            });
            
            const result = await authManager.validateToken();
            
            expect(result).toBe(false);
        });
        
        test('should handle validation error', async () => {
            authManager.accessToken = 'test_token';
            
            fetch.mockRejectedValueOnce(new Error('Network error'));
            
            const result = await authManager.validateToken();
            
            expect(result).toBe(false);
        });
    });
    
    describe('Token Refresh', () => {
        test('should refresh token successfully', async () => {
            authManager.refreshToken = 'valid_refresh_token';
            
            const mockRefreshResponse = {
                access_token: 'new_access_token',
                refresh_token: 'new_refresh_token',
                expires_in: 3600,
                user: { username: 'testuser' }
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockRefreshResponse)
            });
            
            const handleAuthSuccessSpy = jest.spyOn(authManager, 'handleAuthSuccess');
            
            const result = await authManager.refreshAccessToken();
            
            expect(result).toBe(true);
            expect(fetch).toHaveBeenCalledWith('/api/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: 'valid_refresh_token' })
            });
            expect(handleAuthSuccessSpy).toHaveBeenCalledWith(mockRefreshResponse);
        });
        
        test('should handle refresh failure', async () => {
            authManager.refreshToken = 'invalid_refresh_token';
            
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401
            });
            
            const clearTokensSpy = jest.spyOn(authManager, 'clearTokens');
            
            const result = await authManager.refreshAccessToken();
            
            expect(result).toBe(false);
            expect(clearTokensSpy).toHaveBeenCalled();
        });
    });
    
    describe('Authentication Status', () => {
        test('should return true when authenticated', () => {
            authManager.config = { enabled: true };
            authManager.accessToken = 'valid_token';
            authManager.user = { username: 'testuser' };
            
            expect(authManager.isAuthenticated()).toBe(true);
        });
        
        test('should return false when not authenticated', () => {
            authManager.config = { enabled: true };
            authManager.accessToken = null;
            authManager.user = null;
            
            expect(authManager.isAuthenticated()).toBe(false);
        });
        
        test('should return true when authentication is disabled', () => {
            authManager.config = { enabled: false };
            
            expect(authManager.isAuthenticated()).toBe(true);
        });
    });
    
    describe('Role Management', () => {
        beforeEach(() => {
            authManager.user = {
                username: 'testuser',
                roles: ['user', 'viewer'],
                client_roles: ['client_admin']
            };
        });
        
        test('should check if user has specific role', () => {
            expect(authManager.hasRole('user')).toBe(true);
            expect(authManager.hasRole('client_admin')).toBe(true);
            expect(authManager.hasRole('admin')).toBe(false);
        });
        
        test('should check if user has any of multiple roles', () => {
            expect(authManager.hasAnyRole(['admin', 'user'])).toBe(true);
            expect(authManager.hasAnyRole(['admin', 'superuser'])).toBe(false);
            expect(authManager.hasAnyRole(['client_admin', 'admin'])).toBe(true);
        });
        
        test('should return false for roles when no user', () => {
            authManager.user = null;
            
            expect(authManager.hasRole('user')).toBe(false);
            expect(authManager.hasAnyRole(['user', 'admin'])).toBe(false);
        });
    });
    
    describe('Logout', () => {
        test('should logout successfully', async () => {
            authManager.config = { 
                enabled: true,
                logout_url: 'http://keycloak/logout'
            };
            authManager.refreshToken = 'test_refresh_token';
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ message: 'Logout successful' })
            });
            
            const clearTokensSpy = jest.spyOn(authManager, 'clearTokens');
            
            // Mock window.location.href setter
            Object.defineProperty(window.location, 'href', {
                writable: true,
                value: 'http://localhost'
            });
            
            await authManager.logout();
            
            expect(fetch).toHaveBeenCalledWith('/api/auth/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: 'test_refresh_token' })
            });
            expect(clearTokensSpy).toHaveBeenCalled();
        });
    });
});

describe('authenticatedFetch', () => {
    let authManager;
    
    beforeEach(() => {
        // Mock global keycloakAuth
        authManager = {
            getAuthHeaders: jest.fn(() => ({ 'Authorization': 'Bearer test_token' })),
            config: { enabled: true },
            clearTokens: jest.fn(),
            redirectToLogin: jest.fn()
        };
        
        global.window = {
            keycloakAuth: authManager
        };
        
        fetch.mockClear();
    });
    
    test('should add auth headers to request', async () => {
        fetch.mockResolvedValueOnce({
            status: 200,
            json: () => Promise.resolve({ data: 'test' })
        });
        
        // Import authenticatedFetch function
        const { authenticatedFetch } = require('../static/keycloak-auth.js');
        
        await authenticatedFetch('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        expect(fetch).toHaveBeenCalledWith('/api/test', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json'
            }
        });
    });
    
    test('should handle 401 response by redirecting to login', async () => {
        fetch.mockResolvedValueOnce({
            status: 401
        });
        
        const { authenticatedFetch } = require('../static/keycloak-auth.js');
        
        const result = await authenticatedFetch('/api/test');
        
        expect(authManager.clearTokens).toHaveBeenCalled();
        expect(authManager.redirectToLogin).toHaveBeenCalled();
        expect(result).toBeNull();
    });
});

// Test runner
if (typeof module !== 'undefined' && require.main === module) {
    console.log('🧪 Running Keycloak Frontend Tests');
    console.log('=' * 40);
    
    // Note: This is a simplified test runner
    // In a real environment, you would use Jest or another test framework
    console.log('✅ Frontend tests would run with: npm test');
    console.log('📝 Tests cover:');
    console.log('  - Configuration loading');
    console.log('  - Token management');
    console.log('  - OAuth flow handling');
    console.log('  - Authentication status');
    console.log('  - Role management');
    console.log('  - Logout functionality');
    console.log('  - Authenticated fetch wrapper');
}
