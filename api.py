"""
SalaryAI — api.py
FastAPI backend with MySQL prediction logging via PyMySQL
Run: python api.py
Requires: pip install fastapi uvicorn pandas scikit-learn pymysql
"""

import pickle
import os
import pymysql
import pymysql.cursors
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn

# ============================================================
#  APP INIT
# ============================================================
app = FastAPI(
    title="SalaryAI API",
    description="ML-powered salary prediction with MySQL logging",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  MYSQL CONFIGURATION  ← Change these to match your XAMPP setup
# ============================================================
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",       # XAMPP default user
    "password": "",           # XAMPP default = empty password
    "database": "salaryai",
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_db():
    """Open and return a fresh PyMySQL connection."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.MySQLError as e:
        print(f"❌ DB connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

# ============================================================
#  LOAD ML MODEL
# ============================================================
MODEL_PATH = "salary_model.pkl"
if not os.path.exists(MODEL_PATH):
    print("❌ Model not found! Run: python train_model.py")
    exit(1)

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)
print("✅ Model loaded!")

# ============================================================
#  VALUE MAPS  (frontend label → model training label)
# ============================================================
education_map = {
    "High School": "HighSchool",
    "Bachelor":    "BSc",
    "Master":      "MSc",
    "PhD":         "PhD",
}

role_map = {
    "Software Engineer": "Software",
    "Data Scientist":    "Data Analyst",
    "Manager":           "Manager",
    "Analyst":           "Data Analyst",
}

location_map = {
    "USA":    "US",
    "Canada": "Canada",
    "UK":     "UK",
    "Remote": "Remote",
}

# ============================================================
#  PYDANTIC SCHEMAS
# ============================================================
class SalaryRequest(BaseModel):
    years_experience: float = Field(..., ge=0, le=60)
    age:              int   = Field(..., ge=18, le=80)
    education_level:  str
    job_role:         str
    location:         str

class SalaryResponse(BaseModel):
    predicted_salary: int
    currency:         str = "USD"
    saved:            bool = True   # whether DB save succeeded

class PredictionRecord(BaseModel):
    id:               int
    predicted_salary: float
    years_experience: float
    age:              int
    education_level:  str
    job_role:         str
    location:         str
    created_at:       str           # ISO string

class HistoryResponse(BaseModel):
    total:   int
    records: List[PredictionRecord]

class StatsResponse(BaseModel):
    total_predictions: int
    avg_salary:        Optional[float]
    max_salary:        Optional[float]
    min_salary:        Optional[float]

# ============================================================
#  ROUTES
# ============================================================

@app.get("/")
async def root():
    return {"message": "SalaryAI API v2 is running 🚀", "status": "ok"}

@app.get("/health")
async def health():
    # Quick DB ping
    try:
        conn = get_db()
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "unavailable"
    return {"status": "healthy", "db": db_status}


@app.post("/predict", response_model=SalaryResponse)
async def predict(request: SalaryRequest):
    """Run salary prediction and log result to MySQL."""
    try:
        # 1. Build input DataFrame
        input_df = pd.DataFrame([{
            "experience": request.years_experience,
            "age":        request.age,
            "location":   location_map.get(request.location, "US"),
            "degree":     education_map.get(request.education_level, "BSc"),
            "job_role":   role_map.get(request.job_role, "Software"),
        }])

        # 2. Predict
        salary = int(round(model.predict(input_df)[0]))

        # 3. Save to MySQL
        saved = False
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO predictions
                        (predicted_salary, years_experience, age,
                         education_level, job_role, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    salary,
                    request.years_experience,
                    request.age,
                    request.education_level,
                    request.job_role,
                    request.location,
                ))
            conn.commit()
            conn.close()
            saved = True
            print(f"💾 Saved prediction: ${salary:,}  [{request.job_role} · {request.location}]")
        except Exception as db_err:
            print(f"⚠️  DB save failed (prediction still returned): {db_err}")

        return SalaryResponse(predicted_salary=salary, saved=saved)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", response_model=HistoryResponse)
async def history(limit: int = 50, offset: int = 0):
    """Return paginated prediction history from MySQL."""
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            # Total count
            cursor.execute("SELECT COUNT(*) AS cnt FROM predictions")
            total = cursor.fetchone()["cnt"]

            # Records newest-first
            cursor.execute(
                """SELECT id, predicted_salary, years_experience, age,
                          education_level, job_role, location,
                          DATE_FORMAT(created_at, '%%Y-%%m-%%dT%%H:%%i:%%s') AS created_at
                   FROM predictions
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            rows = cursor.fetchall()
        conn.close()

        records = [PredictionRecord(**row) for row in rows]
        return HistoryResponse(total=total, records=records)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Aggregate stats for the dashboard counters."""
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*)       AS total_predictions,
                    AVG(predicted_salary) AS avg_salary,
                    MAX(predicted_salary) AS max_salary,
                    MIN(predicted_salary) AS min_salary
                FROM predictions
            """)
            row = cursor.fetchone()
        conn.close()

        return StatsResponse(
            total_predictions=row["total_predictions"] or 0,
            avg_salary=round(float(row["avg_salary"]), 2) if row["avg_salary"] else None,
            max_salary=float(row["max_salary"]) if row["max_salary"] else None,
            min_salary=float(row["min_salary"]) if row["min_salary"] else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{record_id}")
async def delete_record(record_id: int):
    """Delete a single prediction record."""
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM predictions WHERE id = %s", (record_id,))
            affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": record_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
#  ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("🚀  SalaryAI API v2 starting...")
    print(f"📁  Model : {MODEL_PATH}")
    print(f"🗄️   DB    : {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print("🌐  URL   : http://127.0.0.1:8000")
    print("📖  Docs  : http://127.0.0.1:8000/docs")
    print("=" * 55 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
