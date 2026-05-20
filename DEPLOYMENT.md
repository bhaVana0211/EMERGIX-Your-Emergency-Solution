# EMERGIX — Production Deployment Guide

This guide covers deploying EMERGIX to a production server. Three deployment options are provided — pick whichever fits your infrastructure.

---

## Option 1: Docker Compose (Recommended)

The simplest way to deploy. Everything runs in containers — no manual installs needed.

### Prerequisites
- A Linux server (Ubuntu 22.04+ recommended) with a public IP
- Docker Engine 24+ and Docker Compose v2 installed
- A domain name pointing to your server (e.g. `emergix.yourdomain.com`)

### Step-by-Step

#### 1. Clone and configure
```bash
git clone https://github.com/bhaVana0211/EMERGIX-Your-Emergency-Solution.git
cd EMERGIX-Your-Emergency-Solution

cp .env.example .env
nano .env
```

Set these values in `.env`:
```env
FLASK_ENV=production
SECRET_KEY=<generate-a-strong-random-string>
DATABASE_URL=postgresql://emergix:emergix@db:5432/emergix_db
REDIS_URL=redis://redis:6379/0
SOCKETIO_MESSAGE_QUEUE=redis://redis:6379/0

# Google OAuth (optional — leave blank to disable)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

> **Tip:** Generate a secret key with `python3 -c "import secrets; print(secrets.token_hex(32))"`

#### 2. Launch the stack
```bash
docker compose up -d --build
```

This starts 5 services:
| Service     | Purpose                                    |
|-------------|--------------------------------------------|
| `web`       | Flask app via Gunicorn + Eventlet          |
| `simulator` | Background bed update simulator (optional) |
| `db`        | PostgreSQL 16 with PostGIS                 |
| `redis`     | Message queue for Socket.IO                |
| `nginx`     | Reverse proxy with WebSocket support       |

#### 3. Seed the database (first time only)
```bash
docker compose exec web python seed_data.py
```

#### 4. Verify
Open `http://<your-server-ip>` in a browser. You should see the EMERGIX landing page.

#### 5. Set up SSL with Let's Encrypt

Install Certbot on your host:
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d emergix.yourdomain.com
```

Update `nginx/nginx.conf` to use HTTPS:
```nginx
server {
    listen 80;
    server_name emergix.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name emergix.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/emergix.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/emergix.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://web:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

Mount the certificate volume in `docker-compose.yml` under the `nginx` service:
```yaml
volumes:
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro
```

Then restart:
```bash
docker compose restart nginx
```

---

## Option 2: Manual Deployment (VPS / Bare Metal)

For when you want direct control without Docker.

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ with PostGIS extension
- Redis 6+
- Nginx
- A domain name

### Step-by-Step

#### 1. Set up the database
```bash
sudo -u postgres psql
CREATE USER emergix WITH PASSWORD 'your-secure-password';
CREATE DATABASE emergix_db OWNER emergix;
\c emergix_db
CREATE EXTENSION postgis;
\q
```

#### 2. Clone and install
```bash
git clone https://github.com/bhaVana0211/EMERGIX-Your-Emergency-Solution.git
cd EMERGIX-Your-Emergency-Solution

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install psycopg2-binary
```

#### 3. Configure environment
```bash
cp .env.example .env
nano .env
```
Set `DATABASE_URL=postgresql://emergix:your-secure-password@localhost:5432/emergix_db` and the other variables.

#### 4. Seed the database
```bash
python seed_data.py
```

#### 5. Run with Gunicorn
```bash
gunicorn --worker-class eventlet -w 1 -b 127.0.0.1:5000 "Emergix:create_app()"
```

#### 6. Set up as a systemd service
Create `/etc/systemd/system/emergix.service`:
```ini
[Unit]
Description=EMERGIX Web Application
After=network.target postgresql.service redis.service

[Service]
User=www-data
WorkingDirectory=/opt/emergix
Environment="PATH=/opt/emergix/venv/bin"
EnvironmentFile=/opt/emergix/.env
ExecStart=/opt/emergix/venv/bin/gunicorn --worker-class eventlet -w 1 -b 127.0.0.1:5000 "Emergix:create_app()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable emergix
sudo systemctl start emergix
```

#### 7. Configure Nginx
Create `/etc/nginx/sites-available/emergix`:
```nginx
server {
    listen 80;
    server_name emergix.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/emergix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d emergix.yourdomain.com
```

---

## Option 3: Platform-as-a-Service (Render / Railway / Fly.io)

For the quickest path to a live URL without managing servers.

### Render (example)

1. Push your repo to GitHub.
2. Go to [render.com](https://render.com) and create a **New Web Service**.
3. Connect your GitHub repo.
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT "Emergix:create_app()"`
5. Add environment variables in the Render dashboard (`SECRET_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, etc.).
6. Create a **PostgreSQL** database on Render and link the `DATABASE_URL`.
7. Create a **Redis** instance on Render and link `REDIS_URL` and `SOCKETIO_MESSAGE_QUEUE`.
8. Deploy. Render gives you a public `https://emergix-xxxx.onrender.com` URL.

---

## Database Management

### Backup (Docker)
```bash
docker compose exec db pg_dump -U emergix emergix_db > backup_$(date +%F).sql
```

### Restore (Docker)
```bash
cat backup_YYYY-MM-DD.sql | docker compose exec -T db psql -U emergix emergix_db
```

### Re-seed (wipe and reload)
```bash
# Docker
docker compose exec web python seed_data.py --force

# Manual
python seed_data.py --force
```

---

## Monitoring & Health Check

- **Health endpoint:** `GET /health` returns `{"status": "ok"}`.
- **Docker logs:** `docker compose logs -f web`
- **Systemd logs:** `journalctl -u emergix -f`

---

## Google OAuth (Production)

When deploying to production, update your Google Cloud Console:
1. Go to **APIs & Services > Credentials**.
2. Edit your OAuth Client.
3. Add `https://emergix.yourdomain.com/auth/google/callback` as an authorized redirect URI.
4. Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `pg_config not found` | Install `libpq-dev` (Linux) or use `psycopg2-binary` |
| WebSocket 400 errors | Ensure Nginx has the `Upgrade` and `Connection` headers set |
| Google login redirects fail | Check redirect URI matches exactly in Google Console |
| Unicode errors on Windows | Set `PYTHONIOENCODING=utf-8` in your environment |
| Port already in use | Kill existing process: `lsof -i :5000` or change the port |
