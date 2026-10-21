from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .retrieval import SearchResult


@dataclass(frozen=True)
class EvidenceAssessment:
    coverage_percent: int
    level: str
    summary: str
    available: list[str]
    missing: list[str]
    capture_suggestions: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_evidence(question: str, results: list[SearchResult]) -> EvidenceAssessment:
    requirements = _requirements(question)
    available = [
        f"{result.filename}"
        + (f" · {result.section_title}" if result.section_title else "")
        for result in results
    ]
    available = list(dict.fromkeys(available))

    if not results:
        missing = requirements
        return EvidenceAssessment(
            0,
            "critical",
            "现有课程资料没有命中这道题的核心内容，建议先补充资料再生成。",
            [],
            missing,
            _capture_suggestions(question, missing),
        )

    evidence_units = min(len(results), len(requirements))
    coverage = round(evidence_units / len(requirements) * 100)
    missing = requirements[evidence_units:]
    if not missing:
        return EvidenceAssessment(
            100,
            "sufficient",
            "现有资料能够覆盖这道题的主要要求。",
            available,
            [],
            [],
        )
    level = "partial" if coverage >= 50 else "critical"
    summary = (
        "可以先生成初稿，但部分论证缺少课程资料支持。"
        if level == "partial"
        else "只有少量相关依据，直接生成的答案会比较薄弱。"
    )
    return EvidenceAssessment(
        coverage,
        level,
        summary,
        available,
        missing,
        _capture_suggestions(question, missing),
    )


def _requirements(question: str) -> list[str]:
    requirements = ["核心概念或理论依据"]
    if re.search(r"分析|为什么|影响|作用|原因|机制|关系", question):
        requirements.append("原因、影响或作用机制")
    if re.search(r"比较|区别|异同|优缺点", question):
        requirements.append("比较维度及双方证据")
    if re.search(r"案例|结合|情境|实际|举例", question):
        requirements.append("课程案例或应用材料")
    if re.search(r"建议|措施|方案|如何|改进|解决", question):
        requirements.append("可执行的建议或管理措施")
    if re.search(r"评价|讨论|论证|批判", question):
        requirements.append("支持与反对观点或评价标准")
    if re.search(r"计算|求|公式|数据", question):
        requirements.append("公式、计算步骤和题目所需数据")
    if len(requirements) == 1 and len(question) > 24:
        requirements.append("支持结论的课程证据")
    return requirements


def _capture_suggestions(question: str, missing: list[str]) -> list[str]:
    suggestions = []
    for item in missing[:3]:
        if "案例" in item:
            suggestions.append("教材中对应章节的案例框、课堂案例或章末案例，连续拍摄约 2–4 页。")
        elif "建议" in item or "措施" in item:
            suggestions.append("教材中“管理启示、实践建议、改进措施”相关小节，连续拍摄约 2–3 页。")
        elif "机制" in item or "原因" in item or "影响" in item:
            suggestions.append("教材中解释原因、影响路径或理论模型的小节，连同模型图拍摄约 3–5 页。")
        elif "比较" in item:
            suggestions.append("教材中的对比表、分类框架和两个概念各自的说明页，拍摄约 3–5 页。")
        elif "公式" in item:
            suggestions.append("教材中的公式定义、例题和解题步骤，连同符号说明拍摄约 2–4 页。")
        else:
            topic = re.sub(r"\s+", "", question)[:24]
            suggestions.append(f"在教材目录或索引中查找与“{topic}”对应的小节，从小节标题开始连续拍摄约 3–5 页。")
    return list(dict.fromkeys(suggestions))
