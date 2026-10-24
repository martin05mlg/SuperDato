# Contributing to SuperDato

Thank you for your interest in contributing to **SuperDato**!

## Development Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Docker & Docker Compose** (optional, for full-stack testing)

### Backend Setup
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Run backend tests:
```bash
PYTHONPATH=backend pytest -q
```

### Frontend Setup
```bash
cd frontend
npm ci
npm run dev
```

Build and typecheck frontend:
```bash
cd frontend
npm run build
```

## Important Privacy Rule for Sample Receipts

**Never commit real Mercadona receipts (PDFs, images, or raw dumps) to the repository.**
Real receipts contain personal store addresses, timestamps, invoice numbers, and masked bank card digits (`****1234`).
Always use `python backend/scripts/generate_sample_receipts.py` to generate 100% synthetic sample PDFs for testing.

## Pull Request Process

1. Fork the repository and create a feature branch (`git checkout -b feat/my-feature`).
2. Add or update unit tests in `backend/tests/` for any backend change.
3. Ensure `pytest` and `npm --prefix frontend run build` pass without errors.
4. Open a Pull Request describing the motivation and changes.

