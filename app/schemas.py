from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator

StudentId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=32)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    student_id: StudentId
    name: NonEmptyText
    date_of_birth: date
    email: EmailStr | None = None
    phone: Phone | None = None
    course: NonEmptyText | None = None
    address: Address | None = None
    enrollment_date: date | None = None

    @model_validator(mode="after")
    def require_contact(self) -> "StudentCreate":
        if not self.email and not self.phone:
            raise ValueError("At least one of email or phone is required")
        return self


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: NonEmptyText | None = None
    date_of_birth: date | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    course: NonEmptyText | None = None
    address: Address | None = None
    enrollment_date: date | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "StudentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class StudentReplace(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: NonEmptyText
    date_of_birth: date
    email: EmailStr | None = None
    phone: Phone | None = None
    course: NonEmptyText | None = None
    address: Address | None = None
    enrollment_date: date | None = None


class StudentOut(BaseModel):
    student_id: str
    name: str
    date_of_birth: date
    email: str | None
    phone: str | None
    course: str | None
    address: str | None
    enrollment_date: date | None


class StudentPage(BaseModel):
    items: list[StudentOut]
    limit: int
    offset: int
    total: int


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]


class AskResponse(BaseModel):
    answer: str
    records_used: int
