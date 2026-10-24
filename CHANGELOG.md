# Changelog

All notable changes to **SuperDato** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-24

### Added
- Multi-tenant household management with role-based access control (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`).
-Deterministic Mercadona digital PDF receipt parser (`pdfplumber`) with SHA-256 deduplication and math reconciliation.
- Automatic product catalog normalization, price history tracking, and personal CPI (IPC Personal) inflation engine.
- Smart shopping list predictor based on purchase cadence and consumption intervals.
- Optional Google Gmail OAuth2 (`gmail.readonly`) integration with AES-256-GCM encrypted token storage.
- SuperAdmin panel for managing registration invitation tokens, users, sample receipts, and dynamic Google OAuth settings.
- Zero-config Docker Compose deployment with automatic `SECRET_KEY` / `ENCRYPTION_MASTER_KEY` persistence, automatic Alembic database migrations, and one-time random SuperAdmin password bootstrap.
- GDPR data portability (`GET /api/v1/auth/me/export`) and account deletion (`POST /api/v1/auth/me/delete`) endpoints.
- Synthetic sample receipt PDF generator (`backend/scripts/generate_sample_receipts.py`) and CLI admin password reset script (`backend/scripts/reset_admin.py`).

