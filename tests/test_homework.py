from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.courses import CourseRepository
from app.documents import DocumentRepository
from app.homework import HomeworkService, HomeworkValidationError


class CapturingGenerator:
    method_name = "capturing_generator"

    def __init__(self) -> None:
        self.task_instructions = ""
        self.question = ""

    def generate(
        self, question: str, evidence: list[str], task_instructions: str = ""
    ) -> str:
        self.question = question
        self.task_instructions = task_instructions
        return "先说明心理安全的含义，再分析案例中的发言环境。[1]"


class HomeworkServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.course = self.courses.create("管理学")
        self.documents.create(
            self.course.id,
            "teams.md",
            "# 心理安全\n心理安全让团队成员可以提出问题、承认错误并表达不同意见。",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_hint_mode_returns_grounded_first_step(self) -> None:
        service = HomeworkService(self.database, use_environment_generator=False)
        result = service.guide(
            self.course.id, "请分析心理安全如何影响团队合作", "hint"
        )
        self.assertEqual(result.mode, "hint")
        self.assertEqual(result.grounding_status, "grounded")
        self.assertIn("第一步", result.guidance)
        self.assertEqual(result.citations[0].section_title, "心理安全")

    def test_review_mode_requires_student_attempt(self) -> None:
        service = HomeworkService(self.database, use_environment_generator=False)
        with self.assertRaises(HomeworkValidationError):
            service.guide(self.course.id, "分析心理安全的作用", "review", "")

    def test_steps_mode_returns_structured_process(self) -> None:
        service = HomeworkService(self.database, use_environment_generator=False)
        result = service.guide(
            self.course.id, "分析心理安全如何影响团队合作", "steps"
        )
        self.assertEqual(result.mode, "steps")
        self.assertIn("1.", result.guidance)
        self.assertIn("4.", result.guidance)
        self.assertEqual(result.citations[0].section_title, "心理安全")

    def test_review_mode_sends_attempt_and_restricted_instruction(self) -> None:
        generator = CapturingGenerator()
        service = HomeworkService(
            self.database,
            generator=generator,
            use_environment_generator=False,
        )
        result = service.guide(
            self.course.id,
            "分析心理安全的作用",
            "review",
            "我的答案认为心理安全就是大家意见完全一致。",
        )
        self.assertEqual(result.generation_method, "capturing_generator")
        self.assertIn("我的答案", generator.question)
        self.assertIn("不冒充学生", generator.task_instructions)

    def test_missing_course_evidence_does_not_generate_guidance(self) -> None:
        service = HomeworkService(self.database, use_environment_generator=False)
        result = service.guide(self.course.id, "计算圆锥体积", "steps")
        self.assertEqual(result.grounding_status, "no_evidence")
        self.assertEqual(result.citations, [])


if __name__ == "__main__":
    unittest.main()
