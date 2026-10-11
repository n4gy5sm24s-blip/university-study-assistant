from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.answers import GroundedAnswerService
from app.courses import CourseRepository
from app.documents import DocumentRepository


class GroundedAnswerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.answers = GroundedAnswerService(self.database)

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


if __name__ == "__main__":
    unittest.main()
