# น้องเก็บให้ (Nong Kep Hai)

Thai Voice Assistant for Business

## Setup

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/nong-kep-hai.git
cd nong-kep-hai
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Config
```bash
copy .env.example .env
# แก้ไข .env ใส่ค่าจริง
```

### 3. Run STT Server
```bash
python stt_server.py
# หรือ
start-stt-server.bat
```

### 4. Test
```bash
python test_stt.py audio\test.wav
python db.py  # test database connection
```

## Architecture

```
LIFF (Frontend)
     │
     ▼
Backend Server ──→ STT Server (Local Monsoon)
     │
     ├──→ Database (Neon PostgreSQL)
     │
     └──→ LLM API (Kimi/Google → Local)
```

## Files

| File | Description |
|------|-------------|
| stt_server.py | STT API Server |
| db.py | Database connection |
| test_stt.py | Test STT |
| schema.sql | Database schema |
