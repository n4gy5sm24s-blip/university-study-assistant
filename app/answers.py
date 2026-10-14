from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .generation import AnswerGenerator, generator_from_environment
from .retrieval import RetrievalRepository, SearchResult


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

    def answer(self, course_id: int, question: str) -> GroundedAnswer:
        clean_question = question.strip()
        if len(clean_question) < 3:
            raise QuestionValidationError("问题至少需要 3 个字符")
        results = self.retrieval.search(course_id, clean_question, limit=3)
        if not results:
            return GroundedAnswer(
                question=clean_question,
                answer="当前课程资料中没有找到足够依据。我不能把课程资料没有支持的内容当成答案。",
                grounding_status="no_evidence",
                generation_method="none",
                citations=[],
            )

        citations = [self._citation(index, result) for index, result in enumerate(results, 1)]
        evidence = "\n\n".join(
            f"[{citation.number}] {citation.excerpt}" for citation in citations
        )
        generation_failed = False
        if self.generator is not None:
            try:
                generated = self.generator.generate(
                    clean_question,
                    [citation.excerpt for citation in citations],
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
            answer=f"根据当前课程资料，找到以下直接相关内容：\n\n{evidence}",
            grounding_status="grounded",
            generation_method=(
                "extractive_fallback" if generation_failed else "extractive"
            ),
            citations=citations,
        )

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
