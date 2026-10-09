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
    create_course,
    create_document,
    delete_course,
    delete_document,
    health,
    list_courses,
    list_documents,
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

        delete_document(int(course["id"]), int(document["id"]))
        assert list_documents(int(course["id"])) == []
        delete_course(int(course["id"]))
        assert list_courses() == []
        print("INTEGRATION OK: course and document lifecycle")
    finally:
        shutil.rmtree(CHECK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
