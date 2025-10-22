#!/bin/sh
# =============================================================================
# DevSim Frontend Production Entrypoint
# =============================================================================
# This script handles SSL certificate setup and nginx startup for production
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Let's Encrypt certificates exist
check_letsencrypt_certs() {
    local domain=${DOMAIN_NAME:-localhost}
    
    if [ -f "/etc/letsencrypt/live/$domain/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/$domain/privkey.pem" ]; then
        log_info "Let's Encrypt certificates found for $domain"
        return 0
    else
        log_warn "Let's Encrypt certificates not found for $domain"
        return 1
    fi
}

# Function to update nginx configuration based on certificate availability
update_nginx_config() {
    local domain=${DOMAIN_NAME:-localhost}
    local config_file="/etc/nginx/conf.d/default.conf"
    
    if check_letsencrypt_certs; then
        log_info "Using Let's Encrypt certificates"
        # Replace placeholder domain with actual domain
        sed -i "s/DOMAIN_PLACEHOLDER/$domain/g" "$config_file"
    else
        log_warn "Using self-signed certificates for initial setup"
        # Create a temporary config that uses self-signed certificates
        cat > "$config_file" << EOF
# Temporary configuration with self-signed certificates
server {
    listen 80;
    server_name $domain;
    
    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect HTTP to HTTPS (except ACME challenges)
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $domain;
    
    # Use self-signed certificates initially
    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;
    
    # Basic SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Serve static files
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    # Proxy to backend
    location /api/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket proxy
    location /ws/ {
        proxy_pass http://backend:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    fi
}

# Function to test nginx configuration
test_nginx_config() {
    log_info "Testing nginx configuration..."
    if nginx -t; then
        log_info "Nginx configuration is valid"
        return 0
    else
        log_error "Nginx configuration is invalid"
        return 1
    fi
}

# Function to wait for backend to be ready
wait_for_backend() {
    local max_attempts=30
    local attempt=1
    
    log_info "Waiting for backend to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://backend:5000/api/health > /dev/null 2>&1; then
            log_info "Backend is ready"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Backend not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Backend failed to become ready after $max_attempts attempts"
    return 1
}

# Main execution
main() {
    log_info "Starting DevSim Frontend (Production)"
    
    # Set default domain if not provided
    export DOMAIN_NAME=${DOMAIN_NAME:-localhost}
    log_info "Domain: $DOMAIN_NAME"
    
    # Update nginx configuration based on certificate availability
    update_nginx_config
    
    # Test nginx configuration
    if ! test_nginx_config; then
        log_error "Failed to validate nginx configuration"
        exit 1
    fi
    
    # Wait for backend (optional, with timeout)
    if [ "${WAIT_FOR_BACKEND:-true}" = "true" ]; then
        wait_for_backend || log_warn "Backend not ready, continuing anyway..."
    fi
    
    log_info "Starting nginx..."
    
    # Execute the original command
    exec "$@"
}

# Run main function
main "$@"