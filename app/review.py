from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .answers import Citation
from .retrieval import RetrievalRepository, SearchResult


@dataclass(frozen=True)
class ReviewBlock:
    order: int
    minutes: int
    topic: str
    activity: str
    citation_number: int | None


@dataclass(frozen=True)
class ReviewPlan:
    status: str
    scope: str
    total_minutes: int
    overview: str
    assumptions: list[str]
    blocks: list[ReviewBlock]
    self_test: list[str]
    citations: list[Citation]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ReviewValidationError(ValueError):
    pass


class ReviewPlanService:
    def __init__(self, database: Path | None = None) -> None:
        self.retrieval = RetrievalRepository(database)

    def create_plan(
        self,
        course_id: int,
        scope: str,
        available_hours: float,
        weak_topics: str = "",
    ) -> ReviewPlan:
        clean_scope = scope.strip() or "全部已上传资料"
        clean_weak_topics = weak_topics.strip()
        if available_hours < 0.5 or available_hours > 168:
            raise ReviewValidationError("可用时间需要在 0.5 到 168 小时之间")
        if not self._is_all_scope(clean_scope) and len(clean_scope) < 3:
            raise ReviewValidationError("考试范围至少需要 3 个字符，或填写“全部内容”")

        candidates: list[SearchResult] = []
        if len(clean_weak_topics) >= 3:
            candidates.extend(
                self.retrieval.search(course_id, clean_weak_topics, limit=10)
            )
        if not self._is_all_scope(clean_scope):
            scope_results = self.retrieval.search(course_id, clean_scope, limit=20)
            if not scope_results:
                candidates = []
            else:
                candidates.extend(scope_results)
        else:
            candidates.extend(self.retrieval.list_course_chunks(course_id, limit=50))
        selected = self._unique_topics(candidates, maximum=6)
        total_minutes = round(available_hours * 60)

        if not selected:
            return ReviewPlan(
                "no_evidence",
                clean_scope,
                total_minutes,
                "当前课程没有可用于制定复习计划的资料。",
                ["未找到课程资料，因此没有推测考试重点。"],
                [],
                [],
                [],
            )

        citations = [self._citation(index, item) for index, item in enumerate(selected, 1)]
        blocks = self._build_blocks(total_minutes, citations)
        self_test = [
            f"不用看资料，用自己的话解释“{self._topic(citation)}”，并举一个例子。"
            for citation in citations
        ]
        assumptions = [
            "计划只依据已上传资料的章节覆盖，不代表教师公布的考试权重。",
            "薄弱点优先排列；未提供薄弱点时按资料出现顺序安排。",
            "最后约 30% 时间用于自测和回顾。",
        ]
        return ReviewPlan(
            "ready",
            clean_scope,
            total_minutes,
            f"共安排 {len(blocks)} 个复习块，覆盖 {len(citations)} 个资料主题。",
            assumptions,
            blocks,
            self_test,
            citations,
        )

    @staticmethod
    def _is_all_scope(scope: str) -> bool:
        return scope in {"全部", "全部内容", "全部范围", "全部已上传资料"}

    @classmethod
    def _unique_topics(
        cls, results: list[SearchResult], maximum: int
    ) -> list[SearchResult]:
        selected: list[SearchResult] = []
        seen: set[str] = set()
        for result in results:
            topic = cls._topic_from_result(result)
            if topic in seen:
                continue
            seen.add(topic)
            selected.append(result)
            if len(selected) == maximum:
                break
        return selected

    @staticmethod
    def _topic_from_result(result: SearchResult) -> str:
        return result.section_title or result.filename

    @staticmethod
    def _topic(citation: Citation) -> str:
        return citation.section_title or citation.filename

    @classmethod
    def _build_blocks(
        cls, total_minutes: int, citations: list[Citation]
    ) -> list[ReviewBlock]:
        learn_minutes = round(total_minutes * 0.7)
        test_minutes = max(1, round(total_minutes * 0.2))
        recap_minutes = total_minutes - learn_minutes - test_minutes
        per_topic, remainder = divmod(learn_minutes, len(citations))
        blocks: list[ReviewBlock] = []
        for index, citation in enumerate(citations, 1):
            minutes = per_topic + (1 if index <= remainder else 0)
            blocks.append(
                ReviewBlock(
                    index,
                    minutes,
                    cls._topic(citation),
                    "阅读对应依据，写出三条核心结论，并用自己的例子复述。",
                    citation.number,
                )
            )
        blocks.append(
            ReviewBlock(
                len(blocks) + 1,
                test_minutes,
                "闭卷自测",
                "完成自测题；答不出的题目标记为薄弱点。",
                None,
            )
        )
        if recap_minutes > 0:
            blocks.append(
                ReviewBlock(
                    len(blocks) + 1,
                    recap_minutes,
                    "最后回顾",
                    "只复习自测错误和仍然说不清的主题。",
                    None,
                )
            )
        return blocks

    @staticmethod
    def _citation(number: int, result: SearchResult) -> Citation:
        return Citation(
            number,
            result.chunk_id,
            result.document_id,
            result.filename,
            result.section_title,
            result.sequence,
            result.content,
        )
