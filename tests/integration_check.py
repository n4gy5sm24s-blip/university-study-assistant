from __future__ import annotations

import os
from pathlib import Path
import shutil
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECK_ROOT = PROJECT_ROOT / "tests" / ".tmp" / uuid4().hex
CHECK_ROOT.mkdir(parents=True)
os.environ["STUDY_ASSISTANT_DB"] = str(CHECK_ROOT / "integration.db")

from app.main import (  # noqa: E402
    CourseCreate,
    DocumentCreate,
    HomeworkCreate,
    QuestionCreate,
    ask_course,
    create_course,
    create_document,
    delete_course,
    delete_document,
    health,
    guide_homework,
    list_courses,
    list_documents,
    search_course,
)


def main() -> None:
    try:
        assert health() == {"status": "ok"}
        course = create_course(
            CourseCreate(name="测试课程", description="集成检查")
        )
        assert len(list_courses()) == 1

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

        delete_document(int(course["id"]), int(document["id"]))
        assert list_documents(int(course["id"])) == []
        assert search_course(int(course["id"]), "虚构内容") == []
        delete_course(int(course["id"]))
        assert list_courses() == []
        print("INTEGRATION OK: upload, Q&A, homework guidance, citations, and deletion")
    finally:
        shutil.rmtree(CHECK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
