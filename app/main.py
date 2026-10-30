from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .answers import GroundedAnswerService, QuestionValidationError
from .assignments import AssignmentNotFoundError, AssignmentRepository, AssignmentValidationError
from .course_profile import CourseProfileService
from .course_preferences import CoursePreferencesNotFoundError, CoursePreferencesRepository
from .courses import CourseNotFoundError, CourseRepository
from .documents import (
    CourseNotFoundError as DocumentCourseNotFoundError,
    DocumentNotFoundError,
    DocumentRepository,
    DocumentValidationError,
    DuplicateDocumentError,
)
from .homework import HomeworkService, HomeworkValidationError
from .learning_state import LearningRecordNotFoundError, LearningStateRepository
from .model_config import (
    DEFAULT_MODEL,
    ModelConfigurationError,
    model_configuration_write_enabled,
    model_status,
    save_model_configuration,
)
from .retrieval import (
    RetrievalRepository,
    SearchCourseNotFoundError,
    SearchValidationError,
)
from .review import ReviewCoachService, ReviewPlanService, ReviewValidationError


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"
ENV_PATH = Path(os.environ.get("STUDY_ASSISTANT_ENV", BASE_DIR / ".env"))
load_dotenv(ENV_PATH)

app = FastAPI(title="大学生学习助手", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
repository = CourseRepository()
document_repository = DocumentRepository()
retrieval_repository = RetrievalRepository()
answer_service = GroundedAnswerService()
homework_service = HomeworkService()
review_service = ReviewPlanService()
review_coach_service = ReviewCoachService()
course_profile_service = CourseProfileService()
assignment_repository = AssignmentRepository()
course_preferences_repository = CoursePreferencesRepository()
learning_state_repository = LearningStateRepository()

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = ""
    file_data_url: str = Field(default="", max_length=35_000_000)


class QuestionCreate(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=6)


class HomeworkCreate(BaseModel):
    question: str = Field(default="", max_length=5000)
    mode: str = Field(default="draft", max_length=20)
    student_attempt: str = Field(default="", max_length=10000)
    image_data_url: str = Field(default="", max_length=8_000_000)
    allow_general_knowledge: bool = False
    history: list[dict[str, str]] = Field(default_factory=list, max_length=6)


class ReviewPlanCreate(BaseModel):
    scope: str = Field(default="全部已上传资料", max_length=1000)
    available_hours: float = Field(ge=0.5, le=168)
    weak_topics: str = Field(default="", max_length=1000)


class ReviewAnswerCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2, max_length=5000)


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=5000)
    draft: str = Field(default="", max_length=30000)
    citations: list[dict[str, object]] = Field(default_factory=list)


class AssignmentUpdate(BaseModel):
    final_text: str = Field(min_length=1, max_length=30000)
    status: str = Field(default="draft", max_length=20)


class CoursePreferencesUpdate(BaseModel):
    language: str = Field(min_length=1, max_length=60)
    citation_style: str = Field(min_length=1, max_length=120)
    tone: str = Field(min_length=1, max_length=200)
    target_length: str = Field(default="", max_length=100)
    teacher_requirements: str = Field(default="", max_length=3000)


class ModelConfigurationUpdate(BaseModel):
    api_key: str = Field(default="", max_length=500)
    model: str = Field(default=DEFAULT_MODEL, min_length=1, max_length=120)


class LearningStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=20)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/model")
def get_model_configuration() -> dict[str, object]:
    return model_status().to_dict()


@app.put("/api/model")
def update_model_configuration(payload: ModelConfigurationUpdate) -> dict[str, object]:
    global answer_service, homework_service, review_coach_service
    if not model_configuration_write_enabled():
        raise HTTPException(
            status_code=403,
            detail="线上环境不允许通过网页修改模型密钥，请在部署平台配置环境变量。",
        )
    try:
        current = save_model_configuration(ENV_PATH, payload.api_key, payload.model)
    except ModelConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    answer_service = GroundedAnswerService()
    homework_service = HomeworkService()
    review_coach_service = ReviewCoachService()
    return current.to_dict()


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


@app.get("/api/courses/{course_id}/profile")
def course_profile(course_id: int) -> dict[str, object]:
    try:
        return course_profile_service.build(course_id).to_dict()
    except DocumentCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/courses/{course_id}/learning")
def learning_summary(course_id: int) -> dict[str, object]:
    try:
        return learning_state_repository.summary(course_id)
    except LearningRecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/api/courses/{course_id}/learning/{record_id}")
def update_learning_status(
    course_id: int, record_id: int, payload: LearningStatusUpdate
) -> dict[str, object]:
    try:
        return learning_state_repository.update_status(
            course_id, record_id, payload.status
        ).to_dict()
    except LearningRecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/courses/{course_id}/preferences")
def get_course_preferences(course_id: int) -> dict[str, object]:
    try:
        return course_preferences_repository.get(course_id).to_dict()
    except CoursePreferencesNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.put("/api/courses/{course_id}/preferences")
def update_course_preferences(course_id: int, payload: CoursePreferencesUpdate) -> dict[str, object]:
    try:
        return course_preferences_repository.save(
            course_id,
            payload.language,
            payload.citation_style,
            payload.tone,
            payload.target_length,
            payload.teacher_requirements,
        ).to_dict()
    except CoursePreferencesNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/courses/{course_id}/assignments")
def list_assignments(course_id: int) -> list[dict[str, object]]:
    return [assignment.to_dict() for assignment in assignment_repository.list_for_course(course_id)]


@app.post("/api/courses/{course_id}/assignments", status_code=status.HTTP_201_CREATED)
def create_assignment(course_id: int, payload: AssignmentCreate) -> dict[str, object]:
    try:
        return assignment_repository.create(
            course_id, payload.title, payload.prompt, payload.draft, payload.citations
        ).to_dict()
    except AssignmentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AssignmentValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.patch("/api/courses/{course_id}/assignments/{assignment_id}")
def update_assignment(course_id: int, assignment_id: int, payload: AssignmentUpdate) -> dict[str, object]:
    try:
        return assignment_repository.update(
            course_id, assignment_id, payload.final_text, payload.status
        ).to_dict()
    except AssignmentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AssignmentValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/api/courses/{course_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    course_id: int, payload: DocumentCreate
) -> dict[str, object]:
    try:
        return document_repository.create(
            course_id, payload.filename, payload.content, payload.file_data_url
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


@app.get("/api/courses/{course_id}/search")
def search_course(course_id: int, q: str, limit: int = 10) -> list[dict[str, object]]:
    try:
        return [
            result.to_dict()
            for result in retrieval_repository.search(course_id, q, limit)
        ]
    except SearchCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SearchValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/courses/{course_id}/questions")
def ask_course(course_id: int, payload: QuestionCreate) -> dict[str, object]:
    try:
        result = answer_service.answer(course_id, payload.question, payload.history)
        response = result.to_dict()
        if result.grounding_status == "grounded" and result.citations:
            primary = result.citations[0]
            response["learning_record"] = learning_state_repository.record_interaction(
                course_id,
                primary.document_id,
                primary.sequence,
                primary.section_title or primary.filename,
                payload.question,
            ).to_dict()
        else:
            response["learning_record"] = None
        return response
    except SearchCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (QuestionValidationError, SearchValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/courses/{course_id}/homework-guidance")
def guide_homework(course_id: int, payload: HomeworkCreate) -> dict[str, object]:
    try:
        return homework_service.guide(
            course_id,
            payload.question,
            payload.mode,
            payload.student_attempt,
            payload.image_data_url,
            payload.allow_general_knowledge,
            payload.history,
        ).to_dict()
    except SearchCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (HomeworkValidationError, SearchValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/courses/{course_id}/review-plans")
def create_review_plan(
    course_id: int, payload: ReviewPlanCreate
) -> dict[str, object]:
    try:
        return review_service.create_plan(
            course_id,
            payload.scope,
            payload.available_hours,
            payload.weak_topics,
        ).to_dict()
    except SearchCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ReviewValidationError, SearchValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/courses/{course_id}/review-coach")
def review_answer(course_id: int, payload: ReviewAnswerCreate) -> dict[str, object]:
    try:
        return review_coach_service.evaluate(
            course_id, payload.topic, payload.answer
        ).to_dict()
    except SearchCourseNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ReviewValidationError, SearchValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
