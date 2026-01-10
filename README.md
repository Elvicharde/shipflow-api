# ShipFlow API

ShipFlow API is the backend service that powers the ShipFlow bulk shipping label creation platform.

It is responsible for ingesting and validating shipping data, handling address verification, managing shipping workflows, and generating shipping labels in bulk. The system is designed with production-style concerns in mind, including resilience to imperfect input data, clear error reporting, and maintainable architecture.

---

## Core Responsibilities

- CSV upload and ingestion of shipping orders
- Validation and normalization of shipping data
- Address verification using third-party APIs with fallback support
- Exposing REST endpoints for review and edit workflows
- Shipping service selection and pricing logic
- Purchase validation and mock label generation

---

## Tech Stack

- Python
- Django
- Django REST Framework
- PostgreSQL (SQLite supported for local development)
- Pydantic (schema validation and parsing)

---

## API Overview

Base path: /api/v1

Key endpoints:
- `POST /uploads` — Upload and parse CSV files
- `GET /orders` — Retrieve parsed shipping orders
- `PATCH /orders/{id}` — Edit and revalidate an order
- `POST /addresses/validate` — Address validation
- `GET /shipping/services` — Available shipping services
- `POST /purchase` — Validate and complete bulk purchase

---

## Setup Instructions

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies
4. Configure environment variables
5. Run database migrations
6. Start the development server

Example:
python manage.py migrate
python manage.py runserver


---

## Assumptions & Design Notes

- All business logic and validation live in the backend.
- CSV files may contain incomplete or invalid data; partial failures are expected and handled explicitly.
- Address validation uses a primary provider with a fallback mechanism.
- Label generation is mocked, as the focus is on workflow correctness rather than carrier integration.

Additional assumptions and trade-offs are documented where relevant in the codebase.

---

## Status

This API is part of a technical assessment project and is hosted for evaluation purposes.

