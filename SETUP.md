# SalaryAI v2 — Setup Guide

## Folder Structure
```
SalaryAI_v2/
├── api.py              ← FastAPI backend (updated with MySQL)
├── train_model.py      ← (unchanged) ML model training
├── salary_model.pkl    ← (your existing trained model)
├── index.html
├── style.css
├── script.js
└── database/
    └── setup.sql       ← Run this ONCE in phpMyAdmin
```

---

## Step 1 — Create the MySQL Database (XAMPP)

1. Start **XAMPP** → start **Apache** and **MySQL**
2. Open **phpMyAdmin**: http://localhost/phpmyadmin
3. Click **SQL** tab (top menu)
4. Paste the contents of `database/setup.sql` and click **Go**
5. You should see the `salaryai` database with a `predictions` table ✅

---

## Step 2 — Install Python Dependencies

```bash
pip install fastapi uvicorn pandas scikit-learn pymysql
```

---

## Step 3 — Configure DB credentials in api.py

Open `api.py` and find the `DB_CONFIG` block (~line 30):

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",   # ← XAMPP default
    "password": "",       # ← XAMPP default is empty
    "database": "salaryai",
    ...
}
```

If you set a MySQL root password in XAMPP, update `"password"` here.

---

## Step 4 — Start the API

```bash
# Make sure salary_model.pkl is in the same folder as api.py
python api.py
```

You should see:
```
✅ Model loaded!
🚀  SalaryAI API v2 starting...
🌐  URL: http://127.0.0.1:8000
```

---

## Step 5 — Open the UI

Open `index.html` in your browser (or serve via XAMPP htdocs).

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/predict` | Run prediction + save to DB |
| GET | `/history?limit=10&offset=0` | Paginated history |
| GET | `/stats` | Aggregate stats |
| DELETE | `/history/{id}` | Delete a record |
| GET | `/health` | DB + model health check |

Interactive docs: http://127.0.0.1:8000/docs
