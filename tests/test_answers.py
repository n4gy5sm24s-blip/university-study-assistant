from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.answers import GroundedAnswerService
from app.courses import CourseRepository
from app.documents import DocumentRepository


class FakeGenerator:
    method_name = "fake_generator"

    def generate(self, question: str, evidence: list[str], task_instructions: str = "") -> str:
        return f"机会成本是放弃的最佳替代选择。[1]"


class FailingGenerator:
    method_name = "failing_generator"

    def generate(self, question: str, evidence: list[str], task_instructions: str = "") -> str:
        raise RuntimeError("temporary failure")


class CapturingGenerator:
    method_name = "capturing_generator"

    def __init__(self) -> None:
        self.question = ""
        self.evidence: list[str] = []
        self.task_instructions = ""

    def generate(self, question: str, evidence: list[str], task_instructions: str = "") -> str:
        self.question = question
        self.evidence = evidence
        self.task_instructions = task_instructions
        return "第33张介绍低成本战略和差异化战略。[1]"


class GroundedAnswerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.answers = GroundedAnswerService(
            self.database, use_environment_generator=False
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_natural_question_returns_grounded_answer_and_citation(self) -> None:
        course = self.courses.create("经济学")
        document = self.documents.create(
            course.id,
            "economics.md",
            "# 基本概念\n机会成本是为了得到某种东西而放弃的其他选择中的最高价值。",
        )
        result = self.answers.answer(course.id, "什么是机会成本？")
        self.assertEqual(result.grounding_status, "grounded")
        self.assertEqual(result.generation_method, "extractive")
        self.assertEqual(result.citations[0].document_id, document.id)
        self.assertEqual(result.citations[0].section_title, "基本概念")
        self.assertIn("机会成本", result.answer)

    def test_missing_evidence_does_not_invent_answer_or_citation(self) -> None:
        course = self.courses.create("经济学")
        self.documents.create(course.id, "economics.txt", "机会成本用于比较不同选择。")
        result = self.answers.answer(course.id, "解释量子纠缠")
        self.assertEqual(result.grounding_status, "no_evidence")
        self.assertEqual(result.generation_method, "none")
        self.assertEqual(result.citations, [])
        self.assertIn("没有找到", result.answer)

    def test_answer_does_not_use_another_course(self) -> None:
        first = self.courses.create("课程甲")
        second = self.courses.create("课程乙")
        self.documents.create(second.id, "private.txt", "波特五力用于分析行业竞争结构。")
        result = self.answers.answer(first.id, "什么是波特五力？")
        self.assertEqual(result.grounding_status, "no_evidence")

    def test_configured_generator_uses_retrieved_evidence(self) -> None:
        course = self.courses.create("经济学")
        self.documents.create(course.id, "lesson.txt", "机会成本是放弃的最佳替代选择。")
        service = GroundedAnswerService(
            self.database,
            generator=FakeGenerator(),
            use_environment_generator=False,
        )
        result = service.answer(course.id, "什么是机会成本？")
        self.assertEqual(result.generation_method, "fake_generator")
        self.assertIn("[1]", result.answer)
        self.assertEqual(len(result.citations), 1)

    def test_generator_failure_falls_back_to_extractive_answer(self) -> None:
        course = self.courses.create("经济学")
        self.documents.create(course.id, "lesson.txt", "机会成本是放弃的最佳替代选择。")
        service = GroundedAnswerService(
            self.database,
            generator=FailingGenerator(),
            use_environment_generator=False,
        )
        result = service.answer(course.id, "什么是机会成本？")
        self.assertEqual(result.generation_method, "extractive_fallback")

    def test_local_answer_for_exhibit_explains_exact_location(self) -> None:
        course = self.courses.create("管理学图表")
        self.documents.create(
            course.id,
            "chapter4.md",
            "# Exhibit 4.9 SWOT - Text Alternative\nStrengths include a customer base. Weaknesses include limited resources.",
        )
        service = GroundedAnswerService(self.database, use_environment_generator=False)
        result = service.answer(course.id, "讲讲 exhibit4.9")
        self.assertIn("精确定位", result.answer)
        self.assertIn("Exhibit 4.9", result.answer)
        self.assertEqual(result.citations[0].section_title, "Exhibit 4.9 SWOT - Text Alternative")
        self.assertEqual(result.grounding_status, "grounded")

    def test_follow_up_uses_recent_context_and_exact_slide(self) -> None:
        course = self.courses.create("管理学")
        self.documents.create(
            course.id,
            "BATE_2025R_Ch04_notes.md",
            "# 第 33 张：Business Strategy\nLow-cost strategy and differentiation strategy.",
        )
        generator = CapturingGenerator()
        service = GroundedAnswerService(
            self.database, generator=generator, use_environment_generator=False
        )
        history = [
            {"role": "user", "content": "讲到 business strategy 这张ppt"},
            {"role": "assistant", "content": "没有找到那一页。"},
        ]
        result = service.answer(course.id, "Ch04的第33张ppt不就是吗", history)
        self.assertEqual(result.citations[0].section_title, "第 33 张：Business Strategy")
        self.assertIn("最近对话", generator.question)
        self.assertIn("business strategy", generator.question)

        follow_up = service.answer(
            course.id,
            "这两种有什么区别？再举个简单例子",
            [
                {"role": "user", "content": "Ch04的第33张ppt不就是Business Strategy吗"},
                {"role": "assistant", "content": result.answer},
            ],
        )
        self.assertEqual(follow_up.citations[0].section_title, "第 33 张：Business Strategy")
        self.assertIn("这两种有什么区别", generator.question)

    def test_teaching_answer_receives_neighboring_slides_and_objectives(self) -> None:
        course = self.courses.create("管理学")
        self.documents.create(
            course.id,
            "BATE_2025R_Ch04_notes.md",
            "# 第 2 张：Learning Objectives\n理解三层战略。\n\n"
            "# 第 32 张：Corporate Strategy\n决定进入哪些业务。\n\n"
            "# 第 33 张：Business Strategy\n低成本战略与差异化战略。\n\n"
            "# 第 34 张：Functional Strategy\n各职能支持业务战略。",
        )
        generator = CapturingGenerator()
        service = GroundedAnswerService(
            self.database, generator=generator, use_environment_generator=False
        )
        result = service.answer(course.id, "Ch04 第33张讲了什么")
        titles = [citation.section_title for citation in result.citations]
        self.assertEqual(titles[0], "第 33 张：Business Strategy")
        self.assertIn("第 32 张：Corporate Strategy", titles)
        self.assertIn("第 34 张：Functional Strategy", titles)
        self.assertIn("第 2 张：Learning Objectives", titles)
        self.assertTrue(any("位置：第 34 张：Functional Strategy" in item for item in generator.evidence))
        self.assertIn("本章中的位置", generator.task_instructions)


if __name__ == "__main__":
    unittest.main()
