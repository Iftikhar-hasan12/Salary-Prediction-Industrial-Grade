"""
SalaryAI — api.py
FastAPI backend with MySQL prediction logging via PyMySQL
"""

import pickle
import os
import pymysql
import pymysql.cursors

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
#  MYSQL CONFIGURATION
# ============================================================
DB_CONFIG = {
    'host':        'sql12.freesqldatabase.com',
    'user':        '00',
    'password':    '00',
    'database':    '00',
    'port':        00,
    'cursorclass': pymysql.cursors.DictCursor,
}


def get_db():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.MySQLError as e:
        print(f"DB connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


# ============================================================
#  LOAD ML MODEL
# ============================================================
MODEL_PATH = "salary_model.pkl"
if not os.path.exists(MODEL_PATH):
    print("Model not found! Run: python train_model.py")
    exit(1)

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)
print("Model loaded!")

# ============================================================
#  VALUE MAPS
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
    saved:            bool = True

class PredictionRecord(BaseModel):
    id:               int
    predicted_salary: float
    years_experience: float
    age:              int
    education_level:  str
    job_role:         str
    location:         str
    created_at:       str

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
    return {"message": "SalaryAI API v2 is running", "status": "ok"}


@app.get("/health")
async def health():
    try:
        conn = get_db()
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "unavailable"
    return {"status": "healthy", "db": db_status}


@app.post("/predict", response_model=SalaryResponse)
async def predict(request: SalaryRequest):
    try:
        input_df = pd.DataFrame([{
            "experience": request.years_experience,
            "age":        request.age,
            "location":   location_map.get(request.location, "US"),
            "degree":     education_map.get(request.education_level, "BSc"),
            "job_role":   role_map.get(request.job_role, "Software"),
        }])

        salary = int(round(model.predict(input_df)[0]))

        saved = False
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO mytable
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
        except Exception as db_err:
            print(f"DB save failed: {db_err}")

        return SalaryResponse(predicted_salary=salary, saved=saved)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", response_model=HistoryResponse)
async def history(limit: int = 50, offset: int = 0):
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM mytable")
            total = cursor.fetchone()["cnt"]

            cursor.execute(
                """SELECT id, predicted_salary, years_experience, age,
                          education_level, job_role, location,
                          CAST(created_at AS CHAR) AS created_at
                   FROM mytable
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            rows = cursor.fetchall()
        conn.close()

        records = []
        for row in rows:
            row["created_at"] = str(row["created_at"])
            records.append(PredictionRecord(**row))

        return HistoryResponse(total=total, records=records)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def stats():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*)              AS total_predictions,
                    AVG(predicted_salary) AS avg_salary,
                    MAX(predicted_salary) AS max_salary,
                    MIN(predicted_salary) AS min_salary
                FROM mytable
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
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM mytable WHERE id = %s", (record_id,))
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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
