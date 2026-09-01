# 🚀 VibeSplit Hosting & Deployment Guide

This guide details how to host and deploy **VibeSplit** across various platforms (Free Cloud, Docker, VPS, or PaaS).

---

## 🌟 Option 1: Render.com (Recommended Free Hosting)

1. Push this folder to a GitHub repository.
2. Go to [Render.com](https://render.com) and click **New +** $\rightarrow$ **Blueprint** (or **Web Service**).
3. Connect your GitHub repository.
4. Render will automatically detect [`render.yaml`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/render.yaml) and configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.10
5. Click **Apply / Deploy**. Your app will be live at `https://your-app-name.onrender.com`!

---

## 🌟 Option 2: Railway.app (1-Click Deployment)

1. Push your code to GitHub.
2. Go to [Railway.app](https://railway.app) and click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically pick up [`railway.json`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/railway.json) / [`Dockerfile`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/Dockerfile) and launch your instance with a public HTTPS domain.

---

## 🌟 Option 3: Docker & Docker Compose (Any VPS, DigitalOcean, AWS EC2)

With Docker installed on your server:

```bash
# Clone or copy project files to your server
cd vibe-split

# Build and start in background with persistent database volume
docker compose up -d --build
```

- Your app is now running on port `8000`.
- To view logs: `docker compose logs -f`
- To stop: `docker compose down`

---

## 🌟 Option 4: Direct Linux VPS (Ubuntu / Debian / Nginx)

1. **Install Python & Pip**:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
   ```

2. **Setup virtual environment**:
   ```bash
   cd /var/www/vibe-split
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create a Systemd Service** (`/etc/systemd/system/vibesplit.service`):
   ```ini
   [Unit]
   Description=VibeSplit Web App
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/vibe-split
   ExecStart=/var/www/vibe-split/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Start & Enable Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now vibesplit
   ```

5. **Nginx Reverse Proxy Config** (`/etc/nginx/sites-available/vibesplit`):
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

6. Enable HTTPS with Certbot:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

---

## 📁 Summary of Included Hosting Files

| File | Description |
|---|---|
| [`Dockerfile`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/Dockerfile) | Production multi-stage container build |
| [`docker-compose.yml`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/docker-compose.yml) | Local & VPS multi-container orchestration with persistent volume |
| [`.dockerignore`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/.dockerignore) | Excludes dev files from Docker context |
| [`render.yaml`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/render.yaml) | Infrastructure as Code for Render.com |
| [`railway.json`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/railway.json) | Deployment config for Railway |
| [`Procfile`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/Procfile) | Process runner for Heroku/Render/Dokku |
| [`start.sh`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/start.sh) | Production Linux bash startup script |
| [`.env.example`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/.env.example) | Environment variable template |
| [`requirements.txt`](file:///C:/Users/dhairya/.gemini/antigravity/scratch/vibe-split/requirements.txt) | Python dependencies |
