from __future__ import annotations

import re
from typing import Protocol

from openai import OpenAI

from ..config import Settings
from ..models import TranscriptSegment


DOCUMENT_TITLE = "# 面试记录（整理版）"

CHUNK_PROMPT_TEMPLATE = """你是一名专业的中文计算机技术面试记录整理助手。
现在需要把 ASR 转写结果整理成适合复盘和归档的 Markdown 面试稿。

你的目标：
1. 将对话合理区分为“面试官”和“候选人”
2. 修正明显错别字、口误和 ASR 误识别
3. 进行中度整理，让内容更易读，但不能改变原意，不能补造没有说过的信息
4. 保留计算机面试中的技术表达、术语、缩写、框架名、语言名、工具名、比赛名、公司名、项目名
5. 输出规整、稳定、可直接阅读的 Markdown

请严格遵守以下规则：

一、角色判断规则
- 只能输出两种身份：`面试官`、`候选人`
- 面试官通常负责提问、追问、要求解释、要求举例、评价回答
- 候选人通常负责自我介绍、回答问题、解释项目、说明思路、介绍经历
- 如果一句话很短，例如“对”“嗯”“可以”“然后呢”，要结合上下文判断角色

二、技术内容整理规则
- 对计算机术语优先做“保真”而不是“润色”
- 英文缩写、命令、框架名、语言名、技术名词尽量保留原样
- 如果 ASR 把术语识别成近音错词，应尽量纠正到最合理的技术表达
- 如果无法确定某个术语的准确写法，不要凭空编造

三、纠错与润色规则
- 只修正明显错误
- 去掉明显口头禅、重复词、断裂词，使语句更通顺
- 不要扩写原话，不要新增原文没有表达的内容
- 如果信息本身不完整，就保持不完整，不要脑补

四、输出格式规则
- 必须输出 Markdown
- 必须以 `# 面试记录（整理版）` 开头
- 按主题分节，例如：`## 一、项目经历`、`## 二、数据库`
- 每个主题下使用 `### 面试官` 和 `### 候选人`
- 同一主题下允许多次出现 “面试官 / 候选人” 问答块
- 主题之间使用一行 `------` 分隔
- 只输出整理后的正文，不要输出额外解释

以下是当前片段的原始转写内容：
{transcript}
"""


SUMMARY_PROMPT_TEMPLATE = """你是一名专业的中文计算机技术面试分析助手。

下面是一份已经整理好的技术面试 Markdown 记录，请基于记录内容补充两个部分：

1. `## 面试总结`
要求：
- 用 3 到 5 条要点概括本次面试涉及的核心内容
- 重点覆盖技术主题、项目经历、表达表现、回答风格
- 必须基于原文，不要杜撰

2. `## 可提升点`
要求：
- 用 3 到 5 条给出候选人后续可提升的方向
- 优先从表达清晰度、回答结构、技术深度、项目细节、问题展开方式等角度给建议
- 建议要具体、克制、可执行，不要空泛
- 不要做攻击性评价

输出格式要求：
- 只输出这两个二级标题及其内容
- 每条内容使用 `- ` 开头
- 不要重复输出正文
- 不要添加代码块

以下是面试记录：
{markdown}
"""


class Formatter(Protocol):
    def format(self, segments: list[TranscriptSegment]) -> str: ...


class OpenAICompatibleFormatter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tokens: int,
        chunk_target_chars: int,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.chunk_target_chars = chunk_target_chars
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def format(self, segments: list[TranscriptSegment]) -> str:
        if not segments:
            raise ValueError("转写结果为空，无法整理成 Markdown。")

        chunks = _chunk_segments(segments, self.chunk_target_chars)
        markdown_bodies = [self._format_chunk(chunk, idx, len(chunks)) for idx, chunk in enumerate(chunks)]
        merged_markdown = _merge_markdown_bodies(markdown_bodies)
        summary_markdown = self._build_summary(merged_markdown)
        return _append_summary_sections(merged_markdown, summary_markdown)

    def _format_chunk(
        self,
        segments: list[TranscriptSegment],
        chunk_index: int,
        chunk_count: int,
    ) -> str:
        transcript = _segments_to_plain_text(segments)
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": _build_chunk_prompt(
                        transcript=transcript,
                        chunk_index=chunk_index,
                        chunk_count=chunk_count,
                    ),
                }
            ],
        )
        choice = response.choices[0]
        finish_reason = choice.finish_reason or ""
        if finish_reason == "length":
            raise ValueError("LLM 输出被截断，请减小分块大小或增大 max_tokens。")
        markdown = (choice.message.content or "").strip()
        if not markdown.startswith("# "):
            raise ValueError("LLM 未返回有效 Markdown。")
        return markdown

    def _build_summary(self, markdown: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max(1024, min(self.max_tokens, 4096)),
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_PROMPT_TEMPLATE.format(markdown=markdown),
                }
            ],
        )
        choice = response.choices[0]
        finish_reason = choice.finish_reason or ""
        if finish_reason == "length":
            raise ValueError("LLM 总结输出被截断，请增大 max_tokens。")
        summary = (choice.message.content or "").strip()
        if "## 面试总结" not in summary or "## 可提升点" not in summary:
            raise ValueError("LLM 未返回有效的总结与提升内容。")
        return summary


class MockFormatter:
    def format(self, segments: list[TranscriptSegment]) -> str:
        if not segments:
            raise ValueError("转写结果为空，无法整理成 Markdown。")

        grouped_blocks = _group_mock_blocks(segments)
        sections = []
        for index, block in enumerate(grouped_blocks, start=1):
            title = _infer_mock_section_title(block["texts"], index)
            section_lines = [f"## {title}"]
            for role, text in zip(block["roles"], block["texts"]):
                section_lines.append(f"### {role}")
                section_lines.append(text)
                section_lines.append("")
            sections.append("\n".join(section_lines).strip())

        document = "\n\n".join([DOCUMENT_TITLE, "------", "\n\n------\n\n".join(sections)])
        summary = _build_mock_summary(grouped_blocks)
        return _append_summary_sections(document, summary)


def build_formatter(settings: Settings) -> Formatter:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("缺少 OPENAI_API_KEY，无法使用 OpenAI 格式化。")
        return OpenAICompatibleFormatter(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            chunk_target_chars=settings.llm_chunk_target_chars,
        )
    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("缺少 DEEPSEEK_API_KEY，无法使用 DeepSeek 格式化。")
        return OpenAICompatibleFormatter(
            api_key=settings.deepseek_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            chunk_target_chars=settings.llm_chunk_target_chars,
            base_url=settings.deepseek_base_url,
        )
    return MockFormatter()


def _segments_to_plain_text(segments: list[TranscriptSegment]) -> str:
    rows = []
    for idx, segment in enumerate(segments, start=1):
        rows.append(f"[{idx}] {segment.text}")
    return "\n".join(rows)


def _guess_role(text: str, index: int) -> str:
    normalized = text.lower()
    interviewer_signals = [
        "请你",
        "你先",
        "介绍一下",
        "为什么",
        "怎么做",
        "你觉得",
        "如果让你",
        "?",
        "？",
    ]
    candidate_signals = [
        "我觉得",
        "我之前",
        "我的理解",
        "我会",
        "我负责",
        "我做过",
        "我们当时",
        "我这边",
        "我在项目里",
    ]
    if any(signal in normalized for signal in candidate_signals):
        return "候选人"
    if any(signal in normalized for signal in interviewer_signals):
        return "面试官"
    return "面试官" if index % 2 == 1 else "候选人"


def _clean_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    collapsed = re.sub(r"(嗯|呃|啊|那个|就是)(\s*\1)+", r"\1", collapsed)
    collapsed = re.sub(r"(然后)(\s*\1)+", r"\1", collapsed)

    replacements = {
        "微服务架狗": "微服务架构",
        "卡夫卡": "Kafka",
        "卡发卡": "Kafka",
        "瑞迪斯": "Redis",
        "妈一丝亏": "MySQL",
        "买sql": "MySQL",
        "斯普林": "Spring",
        "斯普林布特": "Spring Boot",
        "多克尔": "Docker",
        "库伯内提斯": "Kubernetes",
        "微叉": "Vue",
        "瑞爱可特": "React",
        "发斯特api": "FastAPI",
        "雷特扣": "LeetCode",
    }
    for source, target in replacements.items():
        collapsed = collapsed.replace(source, target)
    return collapsed.strip("，。；、 ")


def _chunk_segments(segments: list[TranscriptSegment], target_chars: int) -> list[list[TranscriptSegment]]:
    if target_chars <= 0:
        return [segments]

    chunks: list[list[TranscriptSegment]] = []
    current_chunk: list[TranscriptSegment] = []
    current_length = 0

    for segment in segments:
        segment_length = len(segment.text) + 8
        if current_chunk and current_length + segment_length > target_chars:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        current_chunk.append(segment)
        current_length += segment_length

    if current_chunk:
        chunks.append(current_chunk)
    return chunks or [segments]


def _build_chunk_prompt(*, transcript: str, chunk_index: int, chunk_count: int) -> str:
    prompt = CHUNK_PROMPT_TEMPLATE.format(transcript=transcript)
    if chunk_count == 1:
        return prompt
    return (
        f"{prompt}\n\n"
        f"补充要求：这是整场面试的第 {chunk_index + 1}/{chunk_count} 个片段。\n"
        "请只整理当前片段，不要假设前后文，不要补写缺失内容。"
    )


def _merge_markdown_bodies(markdowns: list[str]) -> str:
    if len(markdowns) == 1:
        return _strip_summary_sections(markdowns[0])

    merged_sections: list[str] = []
    for markdown in markdowns:
        body = _extract_dialogue_body(_strip_summary_sections(markdown))
        merged_sections.append(body.strip())

    cleaned_sections = [section.strip().strip("-").strip() for section in merged_sections if section.strip()]
    if not cleaned_sections:
        raise ValueError("LLM 分块整理结果为空。")

    return "\n\n".join(
        [
            DOCUMENT_TITLE,
            "------",
            "\n\n------\n\n".join(cleaned_sections),
        ]
    )


def _extract_dialogue_body(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("LLM 返回结果缺少顶层标题。")

    body = "\n".join(lines[1:]).strip()
    body = body.lstrip("-").strip()
    if "## " not in body:
        raise ValueError("LLM 返回结果缺少主题小节。")
    return body


def _strip_summary_sections(markdown: str) -> str:
    pattern = re.compile(r"\n## 面试总结[\s\S]*$", re.MULTILINE)
    return re.sub(pattern, "", markdown).strip()


def _append_summary_sections(markdown: str, summary_markdown: str) -> str:
    cleaned_summary = summary_markdown.strip()
    if not cleaned_summary:
        return markdown
    return f"{markdown.strip()}\n\n------\n\n{cleaned_summary}\n"


def _group_mock_blocks(segments: list[TranscriptSegment]) -> list[dict[str, list[str]]]:
    grouped: list[dict[str, list[str]]] = []
    current_roles: list[str] = []
    current_texts: list[str] = []
    last_role = ""

    for index, segment in enumerate(segments, start=1):
        role = _guess_role(segment.text, index)
        text = _clean_text(segment.text)
        if not text:
            continue

        if role == last_role and current_texts:
            current_texts[-1] = _merge_adjacent_text(current_texts[-1], text)
            continue

        if len(current_roles) >= 4:
            grouped.append({"roles": current_roles, "texts": current_texts})
            current_roles = []
            current_texts = []

        current_roles.append(role)
        current_texts.append(text)
        last_role = role

    if current_roles:
        grouped.append({"roles": current_roles, "texts": current_texts})

    return grouped


def _merge_adjacent_text(previous: str, current: str) -> str:
    if previous.endswith(("。", "？", "！")):
        return f"{previous} {current}"
    return f"{previous}，{current}"


def _infer_mock_section_title(texts: list[str], index: int) -> str:
    combined = " ".join(texts)
    keyword_titles = [
        (["自我介绍", "介绍一下", "介绍自己"], "一、自我介绍"),
        (["项目", "系统", "业务", "上线"], "二、项目经历"),
        (["mysql", "sql", "索引", "事务", "redis"], "三、数据库与缓存"),
        (["java", "python", "c++", "go", "spring", "vue", "react"], "四、技术栈与实现"),
        (["算法", "复杂度", "链表", "二叉树", "动态规划", "leetcode"], "五、算法与基础"),
    ]
    lowered = combined.lower()
    for keywords, title in keyword_titles:
        if any(keyword in lowered for keyword in keywords):
            return title
    return f"{_to_chinese_index(index)}、面试交流"


def _to_chinese_index(index: int) -> str:
    mapping = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
    }
    return mapping.get(index, str(index))


def _build_mock_summary(grouped_blocks: list[dict[str, list[str]]]) -> str:
    section_titles = [_infer_mock_section_title(block["texts"], idx) for idx, block in enumerate(grouped_blocks, start=1)]
    summary_points = []
    if section_titles:
        summary_points.append(f"- 本次面试主要围绕 {', '.join(section_titles[:3])} 等内容展开。")
    summary_points.append("- 候选人能够围绕问题进行回答，但部分表述仍保留转写口语特征。")
    summary_points.append("- 当前结果为 mock 整理版本，适合预览整体结构与对话脉络。")

    improvement_points = [
        "- 回答技术问题时可优先给出结论，再补充原理、场景和实现细节。",
        "- 介绍项目经历时可强调个人职责、关键难点、方案取舍与最终效果。",
        "- 对数据库、缓存、并发或算法问题，可增加更具体的例子来增强说服力。",
    ]

    return "\n".join(
        [
            "## 面试总结",
            *summary_points,
            "",
            "## 可提升点",
            *improvement_points,
        ]
    )
