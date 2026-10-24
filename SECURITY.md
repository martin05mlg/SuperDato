# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in **SuperDato**, please **do not** open a public GitHub issue.

Instead, report it privately via **GitHub Private Vulnerability Reporting** (Security -> *Report a vulnerability* in this repository).

Please include:
1. A clear description of the vulnerability and affected component (`backend`, `frontend`, `docker-compose`, etc.).
2. Steps to reproduce or a proof-of-concept request/payload.
3. Potential impact and any suggested remediation.

We aim to acknowledge reports within **72 hours** and provide a fix or mitigation plan within **14 days**.

## Security Best Practices for Self-Hosting

- Run SuperDato behind a reverse proxy with **HTTPS (TLS)** enabled (Caddy, Traefik, or Nginx).
- Change the auto-generated initial `SuperAdmin` password immediately upon first login.
- Keep your `app_data` Docker volume (which stores `/app/data/.secrets.json`) backed up and restricted to the container user.
- Do not expose PostgreSQL (`5432`), Redis (`6379`), or the raw FastAPI port (`8000`) directly to the public Internet.

