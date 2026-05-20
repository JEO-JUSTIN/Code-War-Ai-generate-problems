# ⚔️ CodeWar — Intra-Department Contest Platform

A full-stack competitive programming platform with **AI-generated problems** (via Hugging Face), **Docker-sandboxed code execution**, real-time leaderboards, and an admin contest manager.

---

## 🗂️ Project Structure

```
Code War/
├── .env                          # API keys (HF_TOKEN, etc.)
└── code-executor/
    ├── app.py                    # FastAPI backend (main entry point)
    ├── auth.py                   # JWT authentication
    ├── contests.py               # Contest & problem management
    ├── llm.py                    # Hugging Face problem generator
    ├── executor.py               # Docker code execution engine
    ├── database.py               # SQLAlchemy models & DB setup
    ├── languages.py              # Language configs
    ├── requirements.txt          # Python dependencies
    ├── Dockerfile                # Multi-language Docker runtime image
    ├── venv/                     # Python virtual environment
    └── frontend/                 # React + Vite frontend
        ├── src/
        ├── package.json
        └── vite.config.js
```

---

## ⚙️ Prerequisites

Make sure you have these installed before starting:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.9+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |

> ⚠️ **Docker Desktop must be running** before you start the backend.

---

## 🔑 Step 1 — Configure Environment Variables

Edit the `.env` file at `d:\Code War\.env`:

```env
HF_TOKEN="hf_your_huggingface_token_here"
SECRET_KEY="your_jwt_secret_key_here"
```

- Get your **Hugging Face token** at: https://huggingface.co/settings/tokens  
  *(Must have at least Read access to use the Inference API)*
- `SECRET_KEY` can be any long random string for JWT signing.

---

## 🐍 Step 2 — Set Up Python Virtual Environment

Open PowerShell and navigate to the backend folder:

```powershell
cd "d:\JEO\Code War"
```

Create the virtual environment:

```powershell
python -m venv venv
```

Install all dependencies **inside** the venv:

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 🐳 Step 3 — Build the Docker Image (One-time)

This builds the container image used to safely run user code:

```powershell
cd "d:\JEO\Code War"
docker build -t code-executor:latest .
```

> ⏱ First build downloads Ubuntu + language runtimes (~500 MB). Subsequent builds use cache and are fast.

---

## 🚀 Step 4 — Start the Backend

```powershell
cd "d:\JEO\Code War"
.\venv\Scripts\python.exe -m uvicorn app:app --reload --port 8000
```

The backend will be live at: **http://localhost:8000**  
Interactive API docs: **http://localhost:8000/docs**

On first startup, a default admin account is auto-created:
```
Username : admin
Password : admin123
```
> 🔐 Change this after your first login.

---

## 🌐 Step 5 — Start the Frontend

Open a **new PowerShell window**:

```powershell
cd "d:\Code War\code-executor\frontend"
npm install
npm run dev
```

The frontend will be live at: **http://localhost:5173**

---

## ✅ Full Startup Checklist

```
[ ] Docker Desktop is running
[ ] .env has HF_TOKEN set
[ ] Backend running  →  .\venv\Scripts\python.exe -m uvicorn app:app --reload --port 8000
[ ] Frontend running →  npm run dev  (inside frontend/)
[ ] Open browser    →  http://localhost:5173
```

---

## 🤖 How Problem Generation Works

Problems are generated using the **Hugging Face Inference API** with the `Qwen/Qwen2.5-72B-Instruct` model.

- Admin selects **topic** + **difficulty** in the Admin panel
- The backend calls `llm.py → generate_problem(topic, difficulty)`
- The LLM returns a full problem: statement, constraints, 10 test cases, and driver code for Python / C / Java
- The problem is stored in the database and made available in the contest

To change the model, edit this line in `code-executor/llm.py`:
```python
HF_MODEL = "Qwen/Qwen2.5-72B-Instruct"
```

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Make sure you're using `.\venv\Scripts\python.exe`, not system Python |
| `Docker not found` | Start Docker Desktop and wait for it to fully load |
| `HF API 401 Unauthorized` | Check your `HF_TOKEN` in `.env` — must be a valid Read token |
| `Port 8000 in use` | Run `uvicorn ... --port 8001` and update frontend `api.js` accordingly |
| `CORS error in browser` | Ensure backend is running at `http://localhost:8000` |
| `npm: command not found` | Install Node.js from https://nodejs.org |

---

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login, returns JWT token |
| `GET` | `/contests/` | List all contests |
| `POST` | `/contests/` | Create a contest (admin only) |
| `POST` | `/contests/{id}/generate-problem` | AI-generate a problem |
| `POST` | `/execute` | Execute code in Docker sandbox |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 🛡️ Code Execution Safety

| Constraint | Value |
|------------|-------|
| Memory limit | 128 MB |
| CPU limit | 0.5 cores |
| Network | Disabled (`--network none`) |
| PID limit | 64 (blocks fork bombs) |
| Compile timeout | 15 seconds |
| Run timeout | 10 seconds |
| Container cleanup | Auto-removed after exit (`--rm`) |
