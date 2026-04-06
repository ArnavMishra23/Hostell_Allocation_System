# Hostel Room Allocation System

Web application for managing student hostel room allocation with separate student and admin workflows.

## Project Description

This project digitizes the hostel room allocation process for a college environment.
Students can apply for rooms and track their status, while administrators manage rooms, review applications, and run allocations using a transparent priority approach.

## Features

- Student registration and login
- Student profile update
- Room application with preference and special requirements
- Application status tracking
- Admin dashboard with key metrics
- Room management: add, edit, and controlled delete
- Application review and rejection
- Allocation execution and allocation reports
- Role-based access with password hashing and CSRF protection

## Tech Stack

- Python, Flask
- SQLAlchemy ORM
- SQLite for local development
- Gunicorn for production serving
- Bootstrap, HTML, CSS, JavaScript

## Quick Start

1. Create a virtual environment and activate it.
2. Install dependencies.
3. Set environment variables.
4. Run the app.

Example:

    python -m venv .venv
    source .venv/Scripts/activate
    pip install -r requirements.txt
    export SECRET_KEY="your-local-secret"
    export DEFAULT_ADMIN_EMAIL="admin@example.com"
    export DEFAULT_ADMIN_PASSWORD="StrongPassword123"
    python app.py

Open in browser:

    http://127.0.0.1:5000

## Deployment

This project is deployment-ready for Render.

- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Required environment variables:
  - SECRET_KEY
  - DATABASE_URL
  - DEFAULT_ADMIN_EMAIL
  - DEFAULT_ADMIN_PASSWORD

## Future Improvements

- Email notifications for status updates
- Better waitlist workflow
- Audit trail enhancements
- Automated test coverage and CI pipeline

## License

Educational project for learning and demonstration purposes.
