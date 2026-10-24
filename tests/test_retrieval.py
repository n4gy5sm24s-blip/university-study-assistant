from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from app.courses import CourseRepository
from app.documents import DocumentRepository
from app.retrieval import (
    RetrievalRepository,
    SearchCourseNotFoundError,
    SearchValidationError,
    split_text,
)


class RetrievalRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)
        self.database = self.root / "test.db"
        self.courses = CourseRepository(self.database)
        self.documents = DocumentRepository(self.database, self.root / "uploads")
        self.retrieval = RetrievalRepository(self.database)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_markdown_chunks_keep_heading_and_order(self) -> None:
        chunks = split_text(
            "# 第一章\n第一段。\n\n第二段。\n# 第二章\n第三段。",
            "text/markdown",
        )
        self.assertEqual([chunk.section_title for chunk in chunks], ["第一章", "第二章"])
        self.assertEqual([chunk.sequence for chunk in chunks], [0, 1])

    def test_search_returns_source_and_relevance_score(self) -> None:
        course = self.courses.create("管理学")
        document = self.documents.create(
            course.id,
            "strategy.md",
            "# 竞争战略\n差异化战略通过独特价值建立竞争优势。",
        )
        results = self.retrieval.search(course.id, "竞争优势")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, document.id)
        self.assertEqual(results[0].filename, "strategy.md")
        self.assertEqual(results[0].section_title, "竞争战略")
        self.assertIsInstance(results[0].score, float)

    def test_no_result_and_course_isolation(self) -> None:
        first = self.courses.create("课程甲")
        second = self.courses.create("课程乙")
        self.documents.create(first.id, "one.txt", "独特测试词汇蓝海战略")
        self.documents.create(second.id, "two.txt", "另一个课程讨论财务预算")
        self.assertEqual(self.retrieval.search(first.id, "财务预算"), [])
        self.assertEqual(self.retrieval.search(second.id, "蓝海战略"), [])

    def test_delete_document_removes_search_results(self) -> None:
        course = self.courses.create("经济学")
        document = self.documents.create(course.id, "lesson.txt", "机会成本用于比较选择")
        self.assertEqual(len(self.retrieval.search(course.id, "机会成本")), 1)
        self.documents.delete(course.id, document.id)
        self.assertEqual(self.retrieval.search(course.id, "机会成本"), [])

    def test_delete_course_removes_its_search_index(self) -> None:
        course = self.courses.create("市场营销")
        self.documents.create(course.id, "lesson.txt", "消费者细分帮助确定目标市场")
        self.assertEqual(len(self.retrieval.search(course.id, "目标市场")), 1)
        self.courses.delete(course.id)
        with self.assertRaises(SearchCourseNotFoundError) as error:
            self.retrieval.search(course.id, "目标市场")
        self.assertIn("不存在", str(error.exception))

    def test_rejects_too_short_query(self) -> None:
        course = self.courses.create("测试")
        with self.assertRaises(SearchValidationError):
            self.retrieval.search(course.id, "成本")

    def test_exhibit_reference_uses_exact_number_and_prefers_text_alternative(self) -> None:
        course = self.courses.create("管理学")
        self.documents.create(
            course.id,
            "chapter4.md",
            "# Exhibit 4.3 Hierarchy of Goals\n其他图表。\n\n"
            "# Exhibit 4.9 Sample SWOT Analysis\n只有图片。\n\n"
            "# Exhibit 4.9 Sample SWOT Analysis - Text Alternative\n"
            "Strengths: established customer base. Weaknesses: limited resources.",
        )
        results = self.retrieval.search(course.id, "给我讲讲exhibit4.9")
        self.assertEqual(len(results), 2)
        self.assertIn("Text Alternative", results[0].section_title)
        self.assertTrue(all("4.9" in result.section_title for result in results))
        self.assertEqual(self.retrieval.search(course.id, "exhibit 4.8"), [])


if __name__ == "__main__":
    unittest.main()
