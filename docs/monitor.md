# KSTT Web Monitor

Install the optional server dependencies:

```bash
python -m pip install -e '.[monitor]'
export KSTT_ADMIN_TOKEN='use-a-long-random-operator-secret'
kstt monitor start --local
```

Create a diagnostic session in another terminal:

```bash
kstt monitor create --json
```

The visitor page reports normal HTTP request metadata and displays a clear consent explanation. Location is sent only after `navigator.geolocation.getCurrentPosition` grants permission. IP-derived information is never presented as GPS.

Set `monitor.base_url` to the public HTTPS origin when using a separately configured reverse proxy or Cloudflare Tunnel. `KSTT_TRUSTED_PROXIES` accepts comma-separated proxy IPs; forwarded headers from other clients are ignored. Set `monitor.location_enabled: false` to disable location storage. Use `kstt monitor purge` for retention cleanup.

Administrative routes under `/api/*` require `Authorization: Bearer $KSTT_ADMIN_TOKEN`; visitor routes are isolated under `/public/*`, and live streams under `/ws/*` are token-scoped.