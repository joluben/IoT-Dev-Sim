# DevSim Gunicorn Production Setup

This document describes the Gunicorn production server configuration for DevSim backend.

## Overview

DevSim uses Gunicorn as the production WSGI server, replacing the Flask development server for better performance, stability, and security in production environments.

## Configuration Files

### `gunicorn_config.py`
Production-ready Gunicorn configuration with:
- Optimized worker processes (CPU cores * 2 + 1, capped at 8)
- Proper timeouts and connection limits
- Security settings and request limits
- Comprehensive logging configuration
- Process lifecycle hooks for monitoring

### `logging_config.py`
Structured logging configuration with:
- JSON and detailed text formatters
- Log rotation and retention policies
- Separate error logging
- Performance and security event logging

### `run.py`
Enhanced application entry point that:
- Creates WSGI app instance for Gunicorn
- Supports both development and production modes
- Validates production environment settings
- Sets up production logging

## Health Check Endpoints

The production setup includes comprehensive health monitoring:

- `/api/health` - Basic health check
- `/api/health/detailed` - Detailed component status
- `/api/health/system` - System resource monitoring
- `/api/health/readiness` - Kubernetes readiness probe
- `/api/health/liveness` - Kubernetes liveness probe
- `/api/health/security` - Security status check

## Usage

### Development Mode
```bash
# Traditional Flask development server
python run.py
```

### Production Mode
```bash
# Using Gunicorn directly
gunicorn --config gunicorn_config.py run:app

# Using the production startup script
python scripts/start_production.py

# Using Docker (recommended)
docker-compose -f docker-compose.prod.yml up -d
```

## Testing

### Test Gunicorn Configuration
```bash
# Run comprehensive Gunicorn tests
python scripts/test_gunicorn.py

# Test health endpoints
python scripts/health_check.py --verbose

# Load testing (if available)
python scripts/load_test.py
```

## Production Deployment

### Docker Deployment (Recommended)
```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up --build -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Manual Deployment
```bash
# Install production dependencies
pip install -r requirements-prod.txt

# Set environment variables
export FLASK_ENV=production
export FLASK_DEBUG=false
export SECRET_KEY="your-secret-key"
export ENCRYPTION_KEY="your-encryption-key"
export JWT_SECRET_KEY="your-jwt-secret"

# Start with Gunicorn
gunicorn --config gunicorn_config.py run:app
```

## Configuration Options

### Worker Configuration
- **Workers**: `CPU cores * 2 + 1` (capped at 8 for resource efficiency)
- **Worker Class**: `sync` (use `gevent` for async workloads)
- **Timeout**: 60 seconds (increased for file uploads)
- **Keepalive**: 5 seconds (improved connection reuse)

### Security Settings
- **Request Line Limit**: 4094 bytes
- **Request Fields**: 100 maximum
- **Field Size**: 8190 bytes maximum
- **Max Request Size**: 10MB (for CSV uploads)

### Logging
- **Access Log**: `/app/logs/gunicorn_access.log`
- **Error Log**: `/app/logs/gunicorn_error.log`
- **Application Logs**: `/app/logs/devsim.log` (detailed), `/app/logs/devsim.json` (structured)

## Monitoring and Alerting

### Health Checks
- Container health checks every 30 seconds
- Readiness probes for load balancer integration
- System resource monitoring (CPU, memory, disk)

### Performance Metrics
- Request response times
- Worker process status
- System resource utilization
- Error rates and patterns

### Log Analysis
- Structured JSON logs for automated analysis
- Error aggregation and alerting
- Performance trend monitoring
- Security event tracking

## Troubleshooting

### Common Issues

#### Gunicorn Won't Start
```bash
# Check configuration syntax
python -c "import gunicorn_config; print('Config OK')"

# Check application import
python -c "from run import app; print('App OK')"

# Check environment variables
python scripts/start_production.py
```

#### High Memory Usage
- Reduce worker count in `gunicorn_config.py`
- Enable worker recycling with `max_requests`
- Monitor memory leaks in application code

#### Slow Response Times
- Check system resource usage
- Review database query performance
- Monitor worker process status
- Consider async worker class for I/O bound workloads

#### Connection Errors
- Verify network configuration
- Check firewall settings
- Review proxy configuration (Nginx)
- Validate SSL/TLS setup

### Log Analysis
```bash
# View recent errors
tail -f /app/logs/devsim_errors.log

# Monitor access patterns
tail -f /app/logs/gunicorn_access.log

# Analyze JSON logs
jq '.level' /app/logs/devsim.json | sort | uniq -c
```

## Performance Tuning

### Worker Optimization
- Monitor CPU and memory usage per worker
- Adjust worker count based on load patterns
- Consider worker recycling frequency
- Use async workers for I/O heavy workloads

### Resource Limits
- Set appropriate memory limits in Docker
- Configure CPU limits for consistent performance
- Monitor disk I/O for log files and uploads
- Implement connection pooling for databases

### Caching Strategy
- Enable Redis caching for frequently accessed data
- Implement response caching for static content
- Use database query caching
- Configure CDN for static assets

## Security Considerations

### Process Security
- Run as non-root user (`appuser`)
- Limit file system access
- Use Docker secrets for sensitive data
- Enable security headers in Nginx

### Network Security
- Use HTTPS/TLS for all connections
- Implement rate limiting
- Configure CORS policies
- Monitor for suspicious activity

### Data Protection
- Encrypt sensitive data at rest
- Use secure session management
- Implement proper authentication
- Regular security audits

## Maintenance

### Regular Tasks
- Monitor log file sizes and rotation
- Review performance metrics
- Update dependencies regularly
- Test backup and recovery procedures

### Updates and Patches
- Test configuration changes in staging
- Use blue-green deployment for updates
- Monitor application after deployments
- Maintain rollback procedures

### Capacity Planning
- Monitor resource usage trends
- Plan for traffic growth
- Scale worker processes as needed
- Optimize database performance

## Support and Documentation

### Additional Resources
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Flask Production Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Docker Production Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Team Contacts
- DevOps Team: For infrastructure and deployment issues
- Development Team: For application-specific problems
- Security Team: For security-related concerns

---

**Last Updated**: Task 1.6 Implementation - Production Application Server
**Version**: 1.0.0
**Status**: Production Ready