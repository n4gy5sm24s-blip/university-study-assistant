from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .answers import Citation
from .generation import AnswerGenerator, generator_from_environment
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


@dataclass(frozen=True)
class ReviewFeedback:
    topic: str
    feedback: str
    status: str
    generation_method: str
    citation: Citation

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ReviewCoachService:
    def __init__(
        self,
        database: Path | None = None,
        generator: AnswerGenerator | None = None,
        use_environment_generator: bool = True,
    ) -> None:
        self.retrieval = RetrievalRepository(database)
        self.generator = (
            generator_from_environment()
            if generator is None and use_environment_generator
            else generator
        )

    def evaluate(self, course_id: int, topic: str, answer: str) -> ReviewFeedback:
        clean_topic = topic.strip()
        clean_answer = answer.strip()
        if len(clean_topic) < 2:
            raise ReviewValidationError("复习主题不能为空")
        if len(clean_answer) < 2:
            raise ReviewValidationError("请先写下你的回答")
        results = self.retrieval.search(course_id, clean_topic, limit=1)
        if not results:
            raise ReviewValidationError("当前课程资料中找不到这个复习主题")
        citation = ReviewPlanService._citation(1, results[0])
        if self.generator is not None:
            try:
                feedback = self.generator.generate(
                    f"复习主题：{clean_topic}\n学生闭卷回答：{clean_answer}",
                    [citation.excerpt],
                    (
                        "你正在带学生考前复习。先指出回答中正确的部分，再指出遗漏或错误，"
                        "最后给出一段不超过120字的参考回答。只依据课程资料，语气直接清楚。"
                    ),
                )
                return ReviewFeedback(
                    clean_topic, feedback, "reviewed", self.generator.method_name, citation
                )
            except Exception:
                pass
        feedback = (
            "已经完成一次闭卷回忆。请对照下面的课程依据检查：你的回答是否包含核心定义、"
            "关键作用以及一个具体例子。\n\n参考依据：\n"
            f"{citation.excerpt}"
        )
        if len(clean_answer) < 20:
            feedback = "你的回答还比较短，至少需要说清核心概念和它的作用。\n\n" + feedback
        return ReviewFeedback(clean_topic, feedback, "reviewed", "extractive", citation)


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
                "当前课程没有可用于开始急救复习的资料。请先上传老师的课件或课堂笔记。",
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
