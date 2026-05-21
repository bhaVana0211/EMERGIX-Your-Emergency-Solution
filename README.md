# # EMERGIX — Hospital Live Bed Availability & Booking Platform

[![Flask Version](https://img.shields.io/badge/Flask-3.x-004d40.svg?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-Real--Time-01579b.svg?style=flat-square&logo=socketdotio)](https://socket.io/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-0288d1.svg?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Deployment](https://img.shields.io/badge/Deployment-Docker%20%7C%20Nginx-388e3c.svg?style=flat-square&logo=docker)](https://www.docker.com/)

> Real-time hospital bed discovery, pre-arrival emergency alerting, and live administrative management dashboards localized for Bhubaneswar, Odisha. Designed to mitigate critical communication bottlenecks during medical emergencies.

---

## 📌 Table of Contents
1. [Core Problem Statement & Impact](#-core-problem-statement--impact)
2. [Key Features](#-key-features)
3. [System Architecture](#-system-architecture)
4. [Tech Stack](#-tech-stack)
5. [Database Schema & Models](#-database-schema--models)
6. [API Endpoints Reference](#-api-endpoints-reference)
7. [Installation & Setup](#-installation--setup)
8. [Running the Live Simulation](#-running-the-live-simulation)
9. [Production Deployment (Docker)](#-production-deployment-docker)
10. [Default Credentials](#-default-credentials)

---

## ⚡ Core Problem Statement & Impact

During public health crises, information asymmetry regarding critical care availability directly correlates with increased mortality. **EMERGIX** solves the bed discovery failure by providing an end-to-end, sub-second latency synchronization layer between hospital triage desks and citizens. 

*   **Proximity-First Triage:** Automatically surfaces healthcare facilities within a strict 10 km radius using client-side GPS and high-precision geodesic arithmetic.
*   **Actionable Pre-Arrival Alerts:** Replaces passive status tracking with active, stateful telemetry sent to ER crash rooms before the ambulance arrives.
*   **Operational Validation:** Built as a Smart India Hackathon blueprint, aiming for a **50–80% reduction in emergency admission delays** via programmatic bed allocation.

---

## ✨ Key Features

*   **Auto-Location Engine:** Implicitly extracts browser geolocation coordinates to compute localized matrix routing using the Haversine formula.
*   **Granular Inventory Tracking:** Tracks 8 distinct, critical bed topologies (e.g., ICU with Ventilator, Neonatal ICU, General Isolation, Oxygen Supported).
*   **Reactive UI Updates:** Bi-directional event pipelining seamlessly streams remote state updates without costly polling or page invalidation.
*   **Dual-Channel Authentication Stack:** Isolated, stateful session schemas tailored to consumer (Patient) actions versus operational (Hospital Admin) command views.
*   **Live Bed Count Adjustment:** Frictionless `+/-` admin controls with auto-save debouncing and immediate system-wide state mutation broadcasts.

---

## 🏗 System Architecture

```

EMERGIX/
├── app/
│   ├── **init**.py          # Application Factory pattern initialization
│   ├── config.py            # Environment-driven Configuration parser
│   ├── extensions.py        # Centralized Flask Extension registry
│   ├── models.py            # Declarative SQLAlchemy Object-Relational Mapping
│   ├── sockets.py           # Real-time WebSocket event emission handlers
│   ├── blueprints/
│   │   ├── auth.py          # Session management, multi-role registration
│   │   ├── main.py          # Static views and cluster health checks
│   │   ├── hospitals.py     # Consumer-facing discovery and detail processing
│   │   ├── admin.py         # Multi-facility analytical control views
│   │   ├── api.py           # Strictly typed RESTful API endpoints
│   │   └── user.py          # Citizen personal tracking dashboard
│   ├── utils/
│   │   ├── geo.py           # Low-level mathematical Haversine computations
│   │   └── decorators.py    # Custom RBAC (Role-Based Access Control) gates
│   ├── templates/           # Server-rendered semantic Jinja2 modules
│   └── static/
│       ├── css/main.css     # UI System: Teal/Ice Glassmorphism specification
│       ├── css/admin.css    # High-density UI layouts for admins
│       └── js/              # Client-side Socket.IO hooks and location handlers
├── seed_data.py             # Idempotent database seeder engine
├── seed_hospitals.json      # Structured real-world coordinates for 20 Bhubaneswar hospitals
├── mock_bed_simulator.py    # Multi-threaded background mock telemetrist
├── run.py                   # WSGI/SocketIO execution runner entrypoint
├── requirements.txt         # Rigidly pinned pip packaging manifest
├── Dockerfile               # Lean multi-stage runtime build manifest
└── docker-compose.yml       # Production-ready orchestrator config

```

---

## 🛠 Tech Stack

*   **Backend:** Python 3.11 / Flask 3.x WSGI Framework
*   **Asynchronous I/O Layer:** Flask-SocketIO (Event-driven engine executing over thread pools)
*   **Persistence Layer:** SQLAlchemy 2.x ORM abstracting SQLite (Local Dev) & PostgreSQL (Production)
*   **Client Core:** Vanilla JS / Alpine.js (Reactive front-end layer omitting heavy SPA compilation compilation steps)
*   **Styling Engine:** Custom CSS Variables with CSS Grid/Flexbox implementing a modern Glassmorphic theme

---

## 🗄 Database Schema & Models

The architecture enforces strict entity relations to ensure real-time transaction integrity.


```

```
   +-------------------+               +-------------------+
   |       USER        |               |     HOSPITAL      |
   +-------------------+               +-------------------+
   | id (PK)           |               | id (PK)           |
   | email             |               | name              |
   | password_hash     |               | latitude          |
   | role              |               | longitude         |
   +---------+---------+               +---------+---------+
             |                                   |
             | 1                                 | 1
             |                                   |
             | M                                 | M
   +---------v---------+               +---------v---------+
   |   PRE_ARRIVAL     |               |   BED_INVENTORY   |
   |      ALERT        |               +-------------------+
   +-------------------+               | id (PK)           |
   | id (PK)           |               | hospital_id (FK)  |
   | user_id (FK)      |               | bed_type          |
   | hospital_id (FK)  |               | total_allocated   |
   | status            |               | available_count   |
   | critical_notes    |               +-------------------+
   +-------------------+

```

```

---

## 🌐 API Endpoints Reference

### Patient & Discovery API
*   `GET /api/hospitals/nearby`
    *   **Auth:** Patient Session Required
    *   **Query Params:** `lat` (float), `lng` (float), `radius_km` (int, default=10)
    *   **Response:** JSON array containing calculated distances and live aggregate bed counts.
*   `GET /api/hospitals/<id>`
    *   **Auth:** Public
    *   **Response:** Detailed breakdown of all 8 bed categories for the given facility ID.
*   `POST /api/alerts/create`
    *   **Auth:** Patient Session Required
    *   **Payload:** `{ "hospital_id": int, "bed_type": string, "eta_minutes": int, "notes": string }`
    *   **Action:** Triggers database record insert and fires a WebSocket event downstream to the targeted admin.

### Executive & Administrative API
*   `PUT /api/admin/beds/update`
    *   **Auth:** Hospital Admin Role Required
    *   **Payload:** `{ "bed_type": string, "new_count": int }`
    *   **Action:** Mutates state and issues a global broadcast to all listening patients.
*   `PUT /api/admin/alerts/<id>/status`
    *   **Auth:** Hospital Admin Role Required
    *   **Payload:** `{ "status": "ACKNOWLEDGED" | "ADMITTED" | "CANCELLED" }`

---

## 🚀 Installation & Setup

### Prerequisites
*   Python 3.11+ 
*   Pip virtualenv package

### Execution Routine

1. **Clone the repository and enter the workspace root:**
   ```bash
   git clone <your-repo-url>
   cd EMERGIX

```

2. **Initialize and provision your isolated virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

```


3. **Install the pinned development dependency tree:**
```bash
pip install -r requirements.txt

```


4. **Instantiate local configurations:**
```bash
cp .env.example .env

```


> *Note: Open `.env` and alter the `SECRET_KEY` property to prevent default key warnings inside your dev logs.*


5. **Execute the DB migrations and seed realistic geo-coordinates:**
```bash
python seed_data.py

```


*This loads 20 foundational Bhubaneswar hospitals (including AIIMS, Capital Hospital, and AMRI) alongside pre-configured administrative profiles into your local state container.*
6. **Boot up the server factory locally:**
```bash
python run.py

```


Navigating your browser to **`http://localhost:5000`** initializes the glassmorphic gateway portal.

---

## 📈 Running the Live Simulation

To truly witness the real-time reactivity of the system without manual entries, spin up the active synthetic traffic generator inside a separate shell terminal session:

```bash
source venv/bin/activate
python mock_bed_simulator.py

```

### What this does:

The engine launches an active background process looping randomly every 15–45 seconds. It targets arbitrary facility IDs to fluctuate emergency bed capacities. If you leave the main Patient web UI open, you will see target metrics seamlessly increment or flash red to signal depletion without forcing page refreshes.

---

## 🐳 Production Deployment (Docker)

To provision a standardized container setup operating securely behind a reverse proxy configuration:

```bash
# 1. Ensure your environment parameters align with production targets
sed -i 's/FLASK_ENV=development/FLASK_ENV=production/g' .env

# 2. Compile image builds and run detached containers via Docker Compose
docker-compose up --build -d

```

The architecture uses a optimized Nginx wrapper mapping inbound web-traffic over standard port `80`, routing heavy payload caching off the native WSGI execution threads.

---

## 🔐 Default Credentials

Use these preset system profiles to validate application behavior right out of the box:

| Role Identity | Authentication Principal | Plaintext Access Key | Context Scope |
| --- | --- | --- | --- |
| **Demo Patient** | `demo@emergix.health` | `Demo@1234` | Location routing, alert creation inputs |
| **Hospital Admin (AIIMS)** | `admin_1` | `Admin@123` | Control panel access tailored for Facility ID 1 |
| **Hospital Admin (Capital)** | `admin_2` | `Admin@123` | Control panel access tailored for Facility ID 2 |
| **Legacy Site Admin** | `management` | `management123` | High-level read access across active records |

---

> 🎓 **Academic Attribution Notice:** Built as a capstone baseline project solving modern healthcare optimization constraints. The platform leverages actual spatial analytics for the state of Odisha to reflect production-ready implementation environments.

```

```