from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .courses import CourseNotFoundError, CourseRepository
from .documents import (
    CourseNotFoundError as DocumentCourseNotFoundError,
    DocumentNotFoundError,
    DocumentRepository,
    DocumentValidationError,
    DuplicateDocumentError,
)


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="大学生学习助手", version="0.1.0")
repository = CourseRepository()
document_repository = DocumentRepository()

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/courses")
def list_courses() -> list[dict[str, object]]:
    return [course.to_dict() for course in repository.list_all()]


@app.post("/api/courses", status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate) -> dict[str, object]:
    try:
        return repository.create(payload.name, payload.description).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.delete("/api/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int) -> Response:
    try:
        repository.delete(course_id)
    except CourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    document_repository.delete_course_storage(course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/courses/{course_id}/documents")
def list_documents(course_id: int) -> list[dict[str, object]]:
    try:
        return [
            document.to_dict()
            for document in document_repository.list_for_course(course_id)
        ]
    except DocumentCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post(
    "/api/courses/{course_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    course_id: int, payload: DocumentCreate
) -> dict[str, object]:
    try:
        return document_repository.create(
            course_id, payload.filename, payload.content
        ).to_dict()
    except DocumentCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateDocumentError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DocumentValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.delete(
    "/api/courses/{course_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(course_id: int, document_id: int) -> Response:
    try:
        document_repository.delete(course_id, document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
