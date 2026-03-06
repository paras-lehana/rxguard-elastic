# PharmAI Portal Deployment

## Production URLs

- **Primary**: https://pharmai.lehana.in
- **Mirror**: https://pharmai.aidhunik.com (redirects to pharmai.lehana.in)

## Docker Deployment (Current)

The PharmAI portal now runs as a Docker service with Traefik Docker-label routing.

### Compose Deployment

```bash
cd /root/repo/pharmai_portal
docker compose up -d --build
docker compose ps
```

### Routing Source of Truth

- Router and service discovery: Docker labels on container `pharmai-portal`
- Domain rule: `HostRegexp(^(vps-)?pharmai.(lehana.in|aidhunik.com)$)`
- Dynamic file (`/root/traefik_dynamic.yml`) no longer contains pharmai host backend URL mapping

### Health Validation

```bash
curl -f http://localhost:5000/health
curl -I https://pharmai.lehana.in/health
curl -I https://pharmai.aidhunik.com/health
```

## Service Configuration

- **Application**: Flask app (`/root/repo/pharmai_portal/frontend/app.py`)
- **Port**: 5000 (running on host)
- **Process**: Python 3 Flask development server
- **Reverse Proxy**: Traefik (Docker container `root-traefik-1`)

## Traefik Routing

### Router Configuration
- **File**: `/root/traefik_dynamic.yml`
- **Router Name**: `pharmai-portal`
- **Rule**: `(Host('pharmai.lehana.in') || Host('pharmai.aidhunik.com'))`
- **Priority**: 110
- **Entry Points**: websecure (HTTPS only)
- **Service**: `pharmai-portal-service`

### Service Configuration
- **Service Name**: `pharmai-portal-service`
- **Backend**: `http://172.18.0.1:5000`
- **Note**: Uses Docker gateway IP (172.18.0.1) to access host port from Traefik container

## DNS Records

Both domains configured with DNS-only (not proxied through Cloudflare):

- `pharmai.lehana.in` → A record → 82.112.235.26
- `pharmai.aidhunik.com` → A record → 82.112.235.26

## SSL/TLS

- Wildcard certificates cover both domains:
  - `*.lehana.in` → `/etc/letsencrypt/live/lehana.in/fullchain.pem`
  - `*.aidhunik.com` → `/etc/letsencrypt/live/aidhunik.com/fullchain.pem`
- No per-subdomain certificates needed
- Automatic renewal via certbot-cloudflare

## Deployment Steps (Completed 2026-02-17)

1. ✅ Created Traefik router for pharmai subdomain
2. ✅ Created Traefik service pointing to host port 5000
3. ✅ Created DNS records for both lehana.in and aidhunik.com
4. ✅ Restarted Traefik container
5. ✅ Verified HTTPS connectivity on both domains

## Testing

### Local Testing
```bash
# Test from server
curl -I http://localhost:5000/
curl -I http://localhost:5000/health
```

### External Testing
```bash
# Test production URLs
curl -I https://pharmai.lehana.in
curl -I https://pharmai.lehana.in/health
curl -I https://pharmai.aidhunik.com  # Should redirect to lehana.in
```

### Expected Responses
- **pharmai.lehana.in**: HTTP/2 200 (direct access)
- **pharmai.aidhunik.com**: HTTP/2 308 redirect → pharmai.lehana.in (then HTTP/2 200)
- **Health endpoint**: Returns JSON with service status

## Application Routes

The Flask app serves dual routes for Traefik compatibility:

- **Main app**: `/` and `/pharmai`
- **Health check**: `/health` and `/pharmai/health`
- **Analyze**: `/analyze` and `/pharmai/analyze`
- **APIs**: `/api/*` and `/pharmai/api/*`

**Note**: All `/pharmai/*` routes are maintained for backward compatibility with the old `medical.lehana.in/pharmai` path-based routing.

## Service Management

### Restart Application
```bash
# Find the process
lsof -i:5000

# Kill and restart (if needed)
kill -9 <PID>
cd /root/repo/pharmai_portal/frontend
python3 app.py &
```

### Restart Traefik
```bash
docker restart root-traefik-1

# Verify
docker ps | grep traefik
```

### Check Logs
```bash
# Application logs
tail -f /root/repo/pharmai_portal/frontend/nohup.out

# Traefik logs
docker logs -f root-traefik-1
```

## Maintenance

### DNS Record Updates
Use the automation script for DNS changes:
```bash
cd /root/certbot-cloudflare
./add_dns_record.sh pharmai 82.112.235.26 false
```

### SSL Certificate Renewal
Wildcard certificates auto-renew. Manual renewal if needed:
```bash
cd /root/certbot-cloudflare
./renew_cloudflare.sh
docker restart root-traefik-1
```

### Configuration Updates
After modifying `/root/traefik_dynamic.yml`:
```bash
docker restart root-traefik-1
```

## Troubleshooting

### Service Not Accessible
1. Check if app is running: `lsof -i:5000`
2. Check DNS resolution: `nslookup pharmai.lehana.in`
3. Check Traefik routing: `docker logs root-traefik-1 | grep pharmai`
4. Test local connectivity: `curl http://localhost:5000/health`

### SSL Errors
1. Verify certificate coverage: `openssl x509 -in /etc/letsencrypt/live/lehana.in/fullchain.pem -text -noout | grep DNS:`
2. Should show: `DNS:lehana.in, DNS:*.lehana.in`
3. Restart Traefik if cert was recently renewed

### 502 Bad Gateway
1. Application is down: `lsof -i:5000`
2. Restart the Flask app
3. Check backend connectivity: `curl http://172.18.0.1:5000/health`

## Architecture Notes

### Why 172.18.0.1?
- Traefik runs in Docker container
- Flask app runs directly on host
- Docker gateway IP (172.18.0.1) allows container to reach host services
- Alternative would be `host.docker.internal` but explicit IP is more reliable

### Why DNS-only (not proxied)?
- Traefik handles SSL termination internally
- Cloudflare proxy would be redundant
- Direct connection reduces latency
- Consistent with other lehana.in services

### Dual-Domain Strategy
- All services support both lehana.in and aidhunik.com
- aidhunik.com → lehana.in redirect (priority 2000) unifies traffic
- Avoids duplicate routing rules
- Maintains brand consistency (lehana.in is primary)

---

**Last Updated**: 2026-02-17  
**Deployed By**: AI Agent (GitHub Copilot)  
**Status**: ✅ Production Ready
