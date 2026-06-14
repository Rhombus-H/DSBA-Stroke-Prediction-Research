from pathlib import Path
from typing import Optional, Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

DATA_PATH = Path('healthcare-dataset-stroke-data.xls')

app = FastAPI(
    title='Stroke Dataset API',
    description='Query the stroke dataset and add new patient records.',
    version='1.0.0',
)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    df['bmi'] = pd.to_numeric(df['bmi'], errors='coerce')
    return df


DATA = load_data()


def _clean_records(frame: pd.DataFrame) -> list[dict]:
    return frame.replace({np.nan: None}).to_dict(orient='records')


class PatientIn(BaseModel):
    gender: Literal['Male', 'Female', 'Other']
    age: float = Field(..., ge=0, le=120)
    hypertension: Literal[0, 1]
    heart_disease: Literal[0, 1]
    ever_married: Literal['Yes', 'No']
    work_type: Literal['Private', 'Self-employed', 'Govt_job',
                        'children', 'Never_worked']
    Residence_type: Literal['Urban', 'Rural']
    avg_glucose_level: float = Field(..., ge=0)
    bmi: Optional[float] = Field(None, ge=0)
    smoking_status: Literal['formerly smoked', 'never smoked',
                            'smokes', 'Unknown']
    stroke: Literal[0, 1]

    model_config = {
        'json_schema_extra': {
            'example': {
                'gender': 'Male', 'age': 67, 'hypertension': 0,
                'heart_disease': 1, 'ever_married': 'Yes',
                'work_type': 'Private', 'Residence_type': 'Urban',
                'avg_glucose_level': 228.69, 'bmi': 36.6,
                'smoking_status': 'formerly smoked', 'stroke': 1,
            }
        }
    }


@app.get('/')
def root():
    return {'status': 'ok', 'rows': len(DATA)}


@app.get('/patients')
def get_patients(
    gender: Optional[str] = Query(None, description='Male / Female / Other'),
    min_age: Optional[float] = Query(None, ge=0, description='Minimum age'),
    max_age: Optional[float] = Query(None, le=120, description='Maximum age'),
    hypertension: Optional[int] = Query(None, ge=0, le=1),
    heart_disease: Optional[int] = Query(None, ge=0, le=1),
    stroke: Optional[int] = Query(None, ge=0, le=1),
    smoking_status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=5000, description='Max rows to return'),
    offset: int = Query(0, ge=0),
):
    df = DATA
    mask = pd.Series(True, index=df.index)
    if gender is not None:
        mask &= df['gender'].str.lower() == gender.lower()
    if min_age is not None:
        mask &= df['age'] >= min_age
    if max_age is not None:
        mask &= df['age'] <= max_age
    if hypertension is not None:
        mask &= df['hypertension'] == hypertension
    if heart_disease is not None:
        mask &= df['heart_disease'] == heart_disease
    if stroke is not None:
        mask &= df['stroke'] == stroke
    if smoking_status is not None:
        mask &= df['smoking_status'].str.lower() == smoking_status.lower()

    result = df[mask]
    return {
        'count': int(mask.sum()),
        'returned': int(min(limit, max(0, mask.sum() - offset))),
        'results': _clean_records(result.iloc[offset: offset + limit]),
    }


@app.post('/patients', status_code=201)
def create_patient(patient: PatientIn):
    global DATA
    new_id = int(DATA['id'].max()) + 1 if len(DATA) else 1
    row = patient.model_dump()
    row['id'] = new_id
    DATA = pd.concat([DATA, pd.DataFrame([row])], ignore_index=True)
    return {'message': 'Patient created', 'patient': row, 'total_rows': len(DATA)}


@app.get('/stats')
def stats():
    return {
        'total': len(DATA),
        'stroke_rate_pct': round(100 * DATA['stroke'].mean(), 2),
        'mean_age': round(DATA['age'].mean(), 1),
        'mean_glucose': round(DATA['avg_glucose_level'].mean(), 1),
        'by_gender': DATA['gender'].value_counts().to_dict(),
    }
