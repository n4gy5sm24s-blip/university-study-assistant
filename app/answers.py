from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from .generation import AnswerGenerator, generator_from_environment
from .retrieval import RetrievalRepository, SearchResult


_FOLLOW_UP = re.compile(
    r"^(?:继续|接着|再讲|展开|详细|简单点|再举)|"
    r"它|这(?:个|张|两种|些)?|那(?:个|张|些)?|两种|前者|后者|上面|刚才|不就是|区别|例子|什么意思"
)

TEACHING_INSTRUCTIONS = """你正在进行课程讲解，而不是复述检索片段。
根据问题复杂度自然组织回答；用户要求讲解概念、PPT、图表或章节时，尽量覆盖：
1. 它在本章中的位置，以及前后内容为什么这样衔接；
2. 核心概念与概念之间的逻辑关系；
3. 为什么重要，不这样做或混淆后会怎样；
4. 一个明确标为“帮助理解的例子”的简单例子；
5. 最后用一句话指出考试或作业最应抓住什么。
不要机械输出五个标题；简单追问可以直接简洁回答。不要声称资料中明确写了你根据相邻页面推断出的关系。"""


@dataclass(frozen=True)
class Citation:
    number: int
    chunk_id: int
    document_id: int
    filename: str
    section_title: str
    sequence: int
    excerpt: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GroundedAnswer:
    question: str
    answer: str
    grounding_status: str
    generation_method: str
    citations: list[Citation]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["citations"] = [citation.to_dict() for citation in self.citations]
        return result


class QuestionValidationError(ValueError):
    pass


class GroundedAnswerService:
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

    def answer(
        self,
        course_id: int,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> GroundedAnswer:
        clean_question = question.strip()
        if len(clean_question) < 3:
            raise QuestionValidationError("问题至少需要 3 个字符")
        clean_history = self._clean_history(history or [])
        retrieval_query = self._retrieval_query(clean_question, clean_history)
        results = self.retrieval.search(course_id, retrieval_query, limit=3)
        if not results:
            return GroundedAnswer(
                question=clean_question,
                answer="当前课程资料中没有找到足够依据。我不能把课程资料没有支持的内容当成答案。",
                grounding_status="no_evidence",
                generation_method="none",
                citations=[],
            )

        results = self.retrieval.expand_course_context(course_id, results)
        citations = [self._citation(index, result) for index, result in enumerate(results, 1)]
        evidence = "\n\n".join(
            f"[{citation.number}] {citation.excerpt}" for citation in citations
        )
        generation_failed = False
        if self.generator is not None:
            try:
                generated = self.generator.generate(
                    self._generation_question(clean_question, clean_history),
                    [
                        f"来源文件：{citation.filename}\n位置：{citation.section_title}\n内容：{citation.excerpt}"
                        for citation in citations
                    ],
                    TEACHING_INSTRUCTIONS,
                )
                return GroundedAnswer(
                    question=clean_question,
                    answer=generated,
                    grounding_status="grounded",
                    generation_method=self.generator.method_name,
                    citations=citations,
                )
            except Exception:
                generation_failed = True
        return GroundedAnswer(
            question=clean_question,
            answer=self._local_answer(clean_question, citations, evidence),
            grounding_status="grounded",
            generation_method=(
                "extractive_fallback" if generation_failed else "extractive"
            ),
            citations=citations,
        )

    @staticmethod
    def _clean_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        for message in history[-6:]:
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                cleaned.append({"role": role, "content": content[:3000]})
        return cleaned

    @staticmethod
    def _retrieval_query(question: str, history: list[dict[str, str]]) -> str:
        if not history or not (_FOLLOW_UP.search(question) or len(question) <= 12):
            return question
        previous_users = [item["content"] for item in history if item["role"] == "user"]
        return f"{previous_users[-1]} {question}" if previous_users else question

    @staticmethod
    def _generation_question(question: str, history: list[dict[str, str]]) -> str:
        if not history:
            return question
        transcript = "\n".join(
            f"{'学生' if item['role'] == 'user' else '助手'}：{item['content']}"
            for item in history
        )
        return (
            f"最近对话：\n{transcript}\n\n当前问题：{question}\n"
            "请结合最近对话理解指代，但事实仍只能依据本次提供的课程资料。"
        )

    @staticmethod
    def _local_answer(question: str, citations: list[Citation], evidence: str) -> str:
        from .retrieval import _EXHIBIT_REFERENCE

        reference = _EXHIBIT_REFERENCE.search(question)
        if reference:
            label = f"Exhibit {reference.group(1)}.{reference.group(2)}"
            primary = citations[0]
            return (
                f"我先按编号精确定位到 {label}，对应的是“{primary.section_title}”。\n\n"
                f"这张图的课程原文如下：\n\n{primary.excerpt}\n\n"
                "理解这张图时，可以先确认它要比较或归纳的几个部分，再把每一项与题目中的案例对应起来。"
                "当前处于本地资料模式，因此这里只做基于原文的整理，不补充课程资料之外的解释。"
            )
        return f"根据当前课程资料，找到以下直接相关内容：\n\n{evidence}"

    @staticmethod
    def _citation(number: int, result: SearchResult) -> Citation:
        return Citation(
            number=number,
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            filename=result.filename,
            section_title=result.section_title,
            sequence=result.sequence,
            excerpt=result.content,
        )
