from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .answers import Citation
from .course_preferences import CoursePreferencesRepository
from .evidence import EvidenceAssessment, assess_evidence
from .generation import AnswerGenerator, generator_from_environment
from .retrieval import RetrievalRepository, SearchResult


GUIDANCE_INSTRUCTIONS = {
    "draft": "根据课程资料生成一份完整、可编辑的作业草稿。直接回应题目，给出清晰结构和论证，并用 [n] 标注依据。明确资料没有支持的假设，不伪造事实或引用。",
    "hint": "只给解题方向、相关概念和第一步，不直接给出可提交的完整答案。",
    "steps": "把思考过程拆成清楚步骤，解释每一步应做什么，但提醒学生按自己的课程要求完成表达。",
    "review": "检查学生已有尝试：指出正确之处、遗漏、逻辑问题和下一步修改建议，不冒充学生重写整份作业。",
}

GENERAL_KNOWLEDGE_NOTICE = (
    "说明：以下内容未使用课程资料或课程引用，而是基于模型通用知识生成。"
    "请核对题目要求、事实和老师的 AI 使用规则。"
)


@dataclass(frozen=True)
class HomeworkGuidance:
    question: str
    mode: str
    guidance: str
    grounding_status: str
    generation_method: str
    citations: list[Citation]
    evidence_assessment: EvidenceAssessment

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["citations"] = [citation.to_dict() for citation in self.citations]
        result["evidence_assessment"] = self.evidence_assessment.to_dict()
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
        self.preferences = CoursePreferencesRepository(database)
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
        image_data_url: str = "",
        allow_general_knowledge: bool = False,
    ) -> HomeworkGuidance:
        clean_question = question.strip()
        clean_attempt = student_attempt.strip()
        clean_image = image_data_url.strip()
        if clean_image:
            if not clean_image.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
                raise HomeworkValidationError("题目图片只支持 JPG、PNG 或 WebP")
            if self.generator is None or not hasattr(self.generator, "read_image"):
                raise HomeworkValidationError("读取题目图片需要先配置支持图片的生成模型")
            try:
                image_question = self.generator.read_image(clean_image)
            except Exception as error:
                raise HomeworkValidationError("没有成功读取题目图片，请换一张更清晰的图片") from error
            clean_question = f"{clean_question}\n\n图片中的题目：\n{image_question}".strip()
        if len(clean_question) < 3:
            raise HomeworkValidationError("作业题目至少需要 3 个字符")
        if mode not in GUIDANCE_INSTRUCTIONS:
            raise HomeworkValidationError("未知的辅导模式")
        if mode == "review" and not clean_attempt:
            raise HomeworkValidationError("检查模式需要先填写你的尝试")

        results = self.retrieval.search(course_id, clean_question, limit=3)
        assessment = assess_evidence(clean_question, results)
        if not results:
            if allow_general_knowledge and self.generator is not None:
                prompt_question = clean_question
                if clean_attempt:
                    prompt_question += f"\n\n学生已有尝试：\n{clean_attempt}"
                try:
                    preferences = self.preferences.get(course_id)
                    guidance = self.generator.generate(
                        prompt_question,
                        [],
                        (
                            f"{GUIDANCE_INSTRUCTIONS[mode]}\n\n"
                            "允许使用模型通用知识回答；不得生成课程引用、虚构来源或声称使用了课程资料。\n\n"
                            f"本课程长期写作规则：{preferences.generation_instructions()}"
                        ),
                    )
                    return HomeworkGuidance(
                        question=clean_question,
                        mode=mode,
                        guidance=f"{GENERAL_KNOWLEDGE_NOTICE}\n\n{guidance}",
                        grounding_status="general_knowledge",
                        generation_method="openai_general_knowledge",
                        citations=[],
                        evidence_assessment=assessment,
                    )
                except Exception:
                    pass
            return HomeworkGuidance(
                question=clean_question,
                mode=mode,
                guidance=(
                    "当前课程资料中没有找到足够依据。"
                    + (
                        "通用知识生成未成功，请检查 AI 模型配置后重试。"
                        if allow_general_knowledge
                        else "如果这道题不依赖课程资料，可以开启“允许通用知识”后重试；否则请补充相关教材页面。"
                    )
                ),
                grounding_status="no_evidence",
                generation_method="none",
                citations=[],
                evidence_assessment=assessment,
            )

        citations = [self._citation(index, result) for index, result in enumerate(results, 1)]
        prompt_question = clean_question
        if clean_attempt:
            prompt_question += f"\n\n学生已有尝试：\n{clean_attempt}"
        generation_failed = False
        if self.generator is not None:
            try:
                preferences = self.preferences.get(course_id)
                guidance = self.generator.generate(
                    prompt_question,
                    [citation.excerpt for citation in citations],
                    f"{GUIDANCE_INSTRUCTIONS[mode]}\n\n本课程长期写作规则：{preferences.generation_instructions()}",
                )
                return HomeworkGuidance(
                    clean_question,
                    mode,
                    guidance,
                    "grounded",
                    self.generator.method_name,
                    citations,
                    assessment,
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
            assessment,
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
