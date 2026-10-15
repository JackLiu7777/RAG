"""
Prompt 模板。
"""
from app.core.schemas import Chunk


# RAG 模式：严格按参考资料回答
SYSTEM_PROMPT = """你是一个严谨的企业文档问答助手。请严格遵守以下规则：

1. 【只看材料】回答只能基于下方"参考资料"中的内容，绝不编造
2. 【没有就说没有】参考资料里找不到答案时，直接回答"根据现有资料，没有找到相关信息"
3. 【标注来源】在关键结论后面标注来源编号，如 [1][2]
4. 【简洁】直接回答问题，不要复述问题
"""

# 闲聊模式：没有参考资料，自然对话
CHAT_SYSTEM_PROMPT = """你是一个友好的 AI 助手。用户在和你闲聊或问一些与企业文档无关的问题。
请自然、简洁地回答。不知道的事情就老实说不知道，不要编造。
"""


FEW_SHOT_BLOCK = """【示例】

问题：公司几点上班？
回答：根据资料[1]，公司标准工作时间为上午九点至下午六点，午休时间为十二点至十三点。

问题：公司有没有员工食堂？
回答：根据现有资料，没有找到关于员工食堂的相关信息。
"""


def build_context(chunks: list[Chunk]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[{i}] 来源：{c.source}（第{c.chunk_index}块）")
        lines.append(f"内容：{c.text.strip()}")
        lines.append("")
    return "\n".join(lines)


def build_history(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines = ["【对话历史】"]
    for turn in history[-6:]:
        role = "用户" if turn.get("role") == "user" else "助手"
        text = turn.get("text", "")[:200]
        lines.append(f"{role}：{text}")
    lines.append("")
    return "\n".join(lines)


def build_user_prompt(question: str, chunks: list[Chunk], history: list[dict] | None = None) -> str:
    """RAG 模式：带参考资料。"""
    context = build_context(chunks)
    history_block = build_history(history)
    return f"""【参考资料】
{context}
{history_block}
{FEW_SHOT_BLOCK}
【当前问题】
{question}

回答："""


def build_chat_prompt(question: str, history: list[dict] | None = None) -> str:
    """闲聊模式：不带参考资料，只带对话历史。"""
    history_block = build_history(history)
    return f"""{history_block}【当前问题】
{question}

回答："""
