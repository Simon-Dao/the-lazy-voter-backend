# The Lazy Voter — Backend

This repository contains the Django backend for **The Lazy Voter**. It does two main jobs:

## What this backend does

### 1) Caches government data locally (avoids rate limits)
Instead of forcing the frontend to hit rate-limited government APIs directly, this backend downloads and stores data in a local database.

It can download and store:
- Bills
- Legislators
- Campaign / finance data
### Updating / downloading data (updater_service)

Government data is downloaded and cached locally using the **`updater_service`**.

Right now, the updater is run manually via:

- **`updater_service/populate.py`**

This script pulls data from government APIs and writes it into the local database so the frontend can query cached data without getting bottlenecked by rate limits.


> Note 1: The population will take **hours** depending on how much data you choose to download. Downloading *all* government data locally is unrealistic. The updater script only downloads a **relevant subset** of data needed for this application.

#### Roadmap
In the future, this will be replaced with a **command-line tool** for interacting with the updater service (e.g., running partial updates, selecting datasets, scheduling refreshes, etc.).

### 2) Serves API endpoints to the frontend
The backend exposes REST-style API routes that the frontend uses to query the cached data (e.g., search legislators/candidates, fetch bill details, etc.).

---

## Tech stack
- Django (Python)
- SQLite (default, stored locally)
- Docker + Docker Compose (recommended for running)

---

## Getting started

### Prerequisites
- Docker Desktop (or Docker Engine) installed
- Docker Compose v2 (`docker compose ...`)

### Run with Docker Compose
1) Clone the repository:
```bash
git clone <YOUR_REPO_URL>
cd <REPO_FOLDER>

docker compose up --build