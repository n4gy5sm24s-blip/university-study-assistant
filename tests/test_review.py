from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.courses import CourseRepository
from app.documents import DocumentRepository
from app.learning_state import LearningStateRepository
from app.retrieval import RetrievalRepository
from app.review import ReviewCoachService, ReviewPlanService, ReviewValidationError


class MasteryGenerator:
    method_name = "mastery_generator"

    def generate(self, question: str, evidence: list[str], task_instructions: str = "") -> str:
        return "定义准确，也说明了团队成员敢于提问的作用。\n[[MASTERY: mastered]]"


class ReviewPlanServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.course = self.courses.create("管理学")
        self.document = self.documents.create(
            self.course.id,
            "review.md",
            "# 竞争优势\n竞争优势来自成本领先或差异化能力。\n\n"
            "# 心理安全\n心理安全让成员能够提出问题并承认错误。\n\n"
            "# 团队规范\n团队规范是成员对可接受行为的共同预期。",
        )
        self.service = ReviewPlanService(self.database)
        self.learning = LearningStateRepository(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_plan_uses_all_available_minutes_and_sources(self) -> None:
        plan = self.service.create_plan(self.course.id, "全部内容", 2)
        self.assertEqual(plan.status, "ready")
        self.assertEqual(plan.total_minutes, 120)
        self.assertEqual(sum(block.minutes for block in plan.blocks), 120)
        self.assertEqual(len(plan.citations), 3)
        self.assertEqual(len(plan.self_test), 3)

    def test_weak_topic_is_scheduled_first(self) -> None:
        plan = self.service.create_plan(
            self.course.id, "全部内容", 1, "心理安全"
        )
        self.assertEqual(plan.blocks[0].topic, "心理安全")

    def test_persisted_review_topic_is_scheduled_first(self) -> None:
        chunk = RetrievalRepository(self.database).search(self.course.id, "团队规范")[0]
        record = self.learning.record_interaction(
            self.course.id,
            self.document.id,
            chunk.sequence,
            chunk.section_title,
            "团队规范没听懂",
        )
        self.learning.update_status(self.course.id, record.id, "review")
        plan = self.service.create_plan(self.course.id, "全部内容", 1)
        self.assertEqual(plan.blocks[0].topic, "团队规范")
        self.assertIn("1 个来自你的待复习记录", plan.overview)

    def test_unknown_scope_returns_no_evidence(self) -> None:
        plan = self.service.create_plan(self.course.id, "量子力学", 1)
        self.assertEqual(plan.status, "no_evidence")
        self.assertEqual(plan.blocks, [])
        self.assertEqual(plan.citations, [])

    def test_course_without_documents_returns_no_evidence(self) -> None:
        empty_course = self.courses.create("空课程")
        plan = self.service.create_plan(empty_course.id, "全部内容", 1)
        self.assertEqual(plan.status, "no_evidence")

    def test_plan_does_not_include_another_course(self) -> None:
        other = self.courses.create("物理学")
        self.documents.create(other.id, "physics.md", "# 量子力学\n量子力学测试内容。")
        plan = self.service.create_plan(self.course.id, "全部内容", 1)
        self.assertNotIn("量子力学", [block.topic for block in plan.blocks])

    def test_rejects_invalid_available_time(self) -> None:
        with self.assertRaises(ReviewValidationError):
            self.service.create_plan(self.course.id, "全部内容", 0.25)

    def test_coach_evaluates_answer_against_course_evidence(self) -> None:
        coach = ReviewCoachService(
            self.database, use_environment_generator=False
        )
        result = coach.evaluate(
            self.course.id,
            "心理安全",
            "心理安全让团队成员愿意提出问题和承认错误。",
        )
        self.assertEqual(result.status, "reviewed")
        self.assertEqual(result.generation_method, "extractive")
        self.assertEqual(result.citation.section_title, "心理安全")
        self.assertIn("参考依据", result.feedback)
        self.assertEqual(result.mastery_status, "review")

    def test_model_mastery_updates_learning_state_and_removes_marker(self) -> None:
        coach = ReviewCoachService(
            self.database, generator=MasteryGenerator(), use_environment_generator=False
        )
        result = coach.evaluate(
            self.course.id,
            "心理安全",
            "心理安全让成员敢于提出问题和承认错误，因此团队能更早发现风险。",
        )
        self.assertEqual(result.mastery_status, "mastered")
        self.assertNotIn("MASTERY", result.feedback)
        summary = self.learning.summary(self.course.id)
        record = next(item for item in summary["records"] if item["topic"] == "心理安全")
        self.assertEqual(record["status"], "mastered")

    def test_coach_rejects_unknown_topic(self) -> None:
        coach = ReviewCoachService(
            self.database, use_environment_generator=False
        )
        with self.assertRaises(ReviewValidationError):
            coach.evaluate(self.course.id, "量子纠缠", "这是一个回答。")


if __name__ == "__main__":
    unittest.main()
