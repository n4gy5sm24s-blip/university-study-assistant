from __future__ import annotations

import os
from pathlib import Path
import shutil
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECK_ROOT = PROJECT_ROOT / "tests" / ".tmp" / uuid4().hex
CHECK_ROOT.mkdir(parents=True)
os.environ["STUDY_ASSISTANT_DB"] = str(CHECK_ROOT / "integration.db")
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_MODEL"] = ""

from app.main import (  # noqa: E402
    AssignmentCreate,
    AssignmentUpdate,
    CoursePreferencesUpdate,
    CourseCreate,
    DocumentCreate,
    HomeworkCreate,
    QuestionCreate,
    ReviewPlanCreate,
    ask_course,
    create_course,
    create_assignment,
    create_document,
    create_review_plan,
    delete_course,
    delete_document,
    health,
    guide_homework,
    get_course_preferences,
    list_courses,
    list_assignments,
    list_documents,
    search_course,
    update_assignment,
    update_course_preferences,
)


def main() -> None:
    try:
        assert health() == {"status": "ok"}
        course = create_course(
            CourseCreate(name="测试课程", description="集成检查")
        )
        assert len(list_courses()) == 1
        preferences = update_course_preferences(
            int(course["id"]),
            CoursePreferencesUpdate(
                language="英文",
                citation_style="APA 7th",
                tone="正式、简洁",
                target_length="800 words",
                teacher_requirements="结合课程案例",
            ),
        )
        assert preferences["citation_style"] == "APA 7th"
        assert get_course_preferences(int(course["id"]))["language"] == "英文"

        document = create_document(
            int(course["id"]),
            DocumentCreate(
                filename="demo.md",
                content="# 自制测试资料\n这是用于产品验证的虚构内容。",
            ),
        )
        assert document["status"] == "ready"
        assert len(list_documents(int(course["id"]))) == 1
        results = search_course(int(course["id"]), "虚构内容")
        assert len(results) == 1
        assert results[0]["filename"] == "demo.md"
        assert results[0]["section_title"] == "自制测试资料"
        answer = ask_course(
            int(course["id"]), QuestionCreate(question="什么是虚构内容？")
        )
        assert answer["grounding_status"] == "grounded"
        assert answer["generation_method"] == "extractive"
        assert answer["citations"][0]["filename"] == "demo.md"
        missing = ask_course(
            int(course["id"]), QuestionCreate(question="什么是量子纠缠？")
        )
        assert missing["grounding_status"] == "no_evidence"
        assert missing["citations"] == []
        homework = guide_homework(
            int(course["id"]),
            HomeworkCreate(
                question="请分析虚构内容在案例中的作用",
                mode="hint",
            ),
        )
        assert homework["grounding_status"] == "grounded"
        assert homework["mode"] == "hint"
        assert homework["citations"][0]["filename"] == "demo.md"
        assignment = create_assignment(
            int(course["id"]),
            AssignmentCreate(
                title="案例作业",
                prompt="请分析虚构内容在案例中的作用",
                draft=str(homework["guidance"]),
                citations=homework["citations"],
            ),
        )
        assert len(list_assignments(int(course["id"]))) == 1
        completed = update_assignment(
            int(course["id"]),
            int(assignment["id"]),
            AssignmentUpdate(final_text="经过修改的最终稿", status="complete"),
        )
        assert completed["status"] == "complete"
        review_plan = create_review_plan(
            int(course["id"]),
            ReviewPlanCreate(scope="全部内容", available_hours=1),
        )
        assert review_plan["status"] == "ready"
        assert review_plan["total_minutes"] == 60
        assert sum(block["minutes"] for block in review_plan["blocks"]) == 60

        delete_document(int(course["id"]), int(document["id"]))
        assert list_documents(int(course["id"])) == []
        assert search_course(int(course["id"]), "虚构内容") == []
        delete_course(int(course["id"]))
        assert list_courses() == []
        print("INTEGRATION OK: preferences, upload, Q&A, homework, assignment projects, review plan, citations, deletion")
    finally:
        shutil.rmtree(CHECK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
