from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status

from .database import get_connection, initialize_database
from .schemas import (
    AskRequest,
    AskResponse,
    StudentCreate,
    StudentOut,
    StudentPage,
    StudentReplace,
    StudentUpdate,
)

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]
FIELDS = ("name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date")


def row_to_student(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    for field in ("date_of_birth", "enrollment_date"):
        result[field] = date.fromisoformat(result[field]) if result[field] else None
    return result


def get_student_or_404(connection: sqlite3.Connection, student_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return row


def validate_contact(email: str | None, phone: str | None) -> None:
    if not email and not phone:
        raise HTTPException(status_code=422, detail="At least one of email or phone must be present")


def validate_required_values(values: dict[str, Any]) -> None:
    if not values.get("name") or not values.get("date_of_birth"):
        raise HTTPException(status_code=422, detail="name and date_of_birth cannot be null")


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Student Records API",
    description="Student CRUD service backed by SQLite. Optional Ollama support is disabled unless AI_ENABLED=true.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED, tags=["students"])
def create_student(payload: StudentCreate, connection: Connection) -> dict[str, Any]:
    values = payload.model_dump(mode="json")
    try:
        connection.execute(
            """INSERT INTO students
            (student_id, name, date_of_birth, email, phone, course, address, enrollment_date)
            VALUES (:student_id, :name, :date_of_birth, :email, :phone, :course, :address, :enrollment_date)""",
            values,
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        if "students.student_id" in str(exc):
            raise HTTPException(status_code=409, detail="A student with this ID already exists") from exc
        raise HTTPException(status_code=422, detail="Student record violates a data constraint") from exc
    return row_to_student(get_student_or_404(connection, payload.student_id))


@app.get("/students", response_model=StudentPage, tags=["students"])
def list_students(
    connection: Connection,
    name: str | None = Query(default=None, min_length=1, max_length=200),
    course: str | None = Query(default=None, min_length=1, max_length=200),
    email: str | None = Query(default=None, min_length=1, max_length=320),
    dob_after: date | None = Query(default=None),
    dob_before: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    if dob_after and dob_before and dob_after > dob_before:
        raise HTTPException(status_code=422, detail="dob_after must be on or before dob_before")
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (("name", name), ("course", course)):
        if value:
            clauses.append(f"{column} LIKE ? COLLATE NOCASE")
            params.append(f"%{value.strip()}%")
    if email:
        clauses.append("email = ? COLLATE NOCASE")
        params.append(email.strip())
    if dob_after:
        clauses.append("date_of_birth >= ?")
        params.append(dob_after.isoformat())
    if dob_before:
        clauses.append("date_of_birth <= ?")
        params.append(dob_before.isoformat())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    total = connection.execute(f"SELECT COUNT(*) FROM students{where}", params).fetchone()[0]
    rows = connection.execute(
        f"SELECT * FROM students{where} ORDER BY student_id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {"items": [row_to_student(row) for row in rows], "limit": limit, "offset": offset, "total": total}


@app.get("/students/{student_id}", response_model=StudentOut, tags=["students"])
def read_student(student_id: str, connection: Connection) -> dict[str, Any]:
    return row_to_student(get_student_or_404(connection, student_id))


@app.put("/students/{student_id}", response_model=StudentOut, tags=["students"])
def replace_student(student_id: str, payload: StudentReplace, connection: Connection) -> dict[str, Any]:
    existing = get_student_or_404(connection, student_id)
    values = payload.model_dump(mode="json")
    validate_contact(values["email"], values["phone"])
    validate_required_values(values)
    assignments = ", ".join(f"{field} = :{field}" for field in FIELDS)
    values["student_id"] = student_id
    connection.execute(f"UPDATE students SET {assignments} WHERE student_id = :student_id", values)
    connection.commit()
    return row_to_student(get_student_or_404(connection, student_id))


@app.patch("/students/{student_id}", response_model=StudentOut, tags=["students"])
def update_student(student_id: str, payload: StudentUpdate, connection: Connection) -> dict[str, Any]:
    existing = get_student_or_404(connection, student_id)
    updates = payload.model_dump(exclude_unset=True, mode="json")
    merged = dict(existing)
    merged.update(updates)
    validate_contact(merged["email"], merged["phone"])
    validate_required_values(merged)
    assignments = ", ".join(f"{field} = ?" for field in updates)
    connection.execute(
        f"UPDATE students SET {assignments} WHERE student_id = ?",
        [*updates.values(), student_id],
    )
    connection.commit()
    return row_to_student(get_student_or_404(connection, student_id))


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["students"])
def delete_student(student_id: str, connection: Connection) -> Response:
    get_student_or_404(connection, student_id)
    connection.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    connection.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/ask", response_model=AskResponse, tags=["optional AI"])
async def ask_students(payload: AskRequest, connection: Connection) -> AskResponse:
    if os.getenv("AI_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=404, detail="Optional AI endpoint is disabled")
    rows = connection.execute(
        "SELECT student_id, name, date_of_birth, email, phone, course, enrollment_date FROM students ORDER BY student_id LIMIT 100"
    ).fetchall()
    records = [dict(row) for row in rows]
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
    prompt = (
        "Answer the user's question using only the JSON student records below. "
        "If the records do not contain the answer, say so. Do not infer missing facts.\n"
        f"Records JSON: {records}\nQuestion: {payload.question}"
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not get a response from the configured Ollama service") from exc
    if not answer:
        raise HTTPException(status_code=502, detail="The configured Ollama model returned an empty answer")
    return AskResponse(answer=answer, records_used=len(records))
