# WireGuard Real Panel - Stackdome

This build explicitly sets Flask's `template_folder` to the same directory as `app.py` (i.e. `/app` inside the image), and `login.html`, `dashboard.html`, and `base.html` are copied flat into that same directory — avoiding TemplateNotFound when deployed from the project root.

## Stackdome
- Build with Dockerfile.
- Expose HTTP port 5000.
- For real WireGuard: the runtime must permit NET_ADMIN/TUN and UDP 51820, or WireGuard must run on the host.
- Persistent volumes: `/data` and `/etc/wireguard`.

Default login: admin / admin123 (change via environment variables).
