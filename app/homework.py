from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .answers import Citation
from .generation import AnswerGenerator, generator_from_environment
from .retrieval import RetrievalRepository, SearchResult


GUIDANCE_INSTRUCTIONS = {
    "draft": "根据课程资料生成一份完整、可编辑的作业草稿。直接回应题目，给出清晰结构和论证，并用 [n] 标注依据。明确资料没有支持的假设，不伪造事实或引用。",
    "hint": "只给解题方向、相关概念和第一步，不直接给出可提交的完整答案。",
    "steps": "把思考过程拆成清楚步骤，解释每一步应做什么，但提醒学生按自己的课程要求完成表达。",
    "review": "检查学生已有尝试：指出正确之处、遗漏、逻辑问题和下一步修改建议，不冒充学生重写整份作业。",
}


@dataclass(frozen=True)
class HomeworkGuidance:
    question: str
    mode: str
    guidance: str
    grounding_status: str
    generation_method: str
    citations: list[Citation]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["citations"] = [citation.to_dict() for citation in self.citations]
        return result


class HomeworkValidationError(ValueError):
    pass


class HomeworkService:
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

    def guide(
        self,
        course_id: int,
        question: str,
        mode: str = "draft",
        student_attempt: str = "",
    ) -> HomeworkGuidance:
        clean_question = question.strip()
        clean_attempt = student_attempt.strip()
        if len(clean_question) < 3:
            raise HomeworkValidationError("作业题目至少需要 3 个字符")
        if mode not in GUIDANCE_INSTRUCTIONS:
            raise HomeworkValidationError("未知的辅导模式")
        if mode == "review" and not clean_attempt:
            raise HomeworkValidationError("检查模式需要先填写你的尝试")

        results = self.retrieval.search(course_id, clean_question, limit=3)
        if not results:
            return HomeworkGuidance(
                question=clean_question,
                mode=mode,
                guidance="当前课程资料中没有找到足够依据，暂时不能可靠地辅导这道题。",
                grounding_status="no_evidence",
                generation_method="none",
                citations=[],
            )

        citations = [self._citation(index, result) for index, result in enumerate(results, 1)]
        prompt_question = clean_question
        if clean_attempt:
            prompt_question += f"\n\n学生已有尝试：\n{clean_attempt}"
        generation_failed = False
        if self.generator is not None:
            try:
                guidance = self.generator.generate(
                    prompt_question,
                    [citation.excerpt for citation in citations],
                    GUIDANCE_INSTRUCTIONS[mode],
                )
                return HomeworkGuidance(
                    clean_question,
                    mode,
                    guidance,
                    "grounded",
                    self.generator.method_name,
                    citations,
                )
            except Exception:
                generation_failed = True

        return HomeworkGuidance(
            clean_question,
            mode,
            self._local_guidance(mode, citations),
            "grounded",
            "extractive_fallback" if generation_failed else "extractive",
            citations,
        )

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

    @staticmethod
    def _local_guidance(mode: str, citations: list[Citation]) -> str:
        first = citations[0]
        if mode == "draft":
            return (
                "当前没有启用生成模型，因此无法可靠生成完整作业草稿。"
                "你可以先根据下面的课程依据组织答案，或配置生成模型："
                f"\n\n[1] {first.excerpt}\n\n"
                "建议结构：概念界定 → 结合题目分析 → 得出结论 → 核对引用。"
            )
        if mode == "hint":
            return (
                "先判断题目要求你解释、比较还是应用概念。第一步可以从资料中的这条依据开始："
                f"\n\n[1] {first.excerpt}\n\n然后用自己的话说明它与题目的关系。"
            )
        if mode == "steps":
            return (
                "可以按以下步骤完成：\n"
                "1. 圈出题目中的核心对象和动作要求。\n"
                f"2. 用课程依据界定核心概念：[1] {first.excerpt}\n"
                "3. 把概念应用到题目给出的情境。\n"
                "4. 检查结论是否回答了题目，并按课程要求改写。"
            )
        return (
            "请先用资料依据检查你的尝试是否准确覆盖核心概念："
            f"\n\n[1] {first.excerpt}\n\n"
            "再检查你的结论是否有理由支持、是否遗漏题目要求。当前未启用生成模型，因此只提供检查依据。"
        )
