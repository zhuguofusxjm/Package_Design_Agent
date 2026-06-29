from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, RequirementSummary, Message

class SocraticSkill(Skill):
    MAX_ROUNDS = 5

    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        session = ctx.session
        session.socratic_round += 1
        round_no = session.socratic_round

        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        history = "\n".join(f"{m.role}: {m.content}" for m in session.messages[-10:])
        user_message = session.messages[-1].content if session.messages else ""

        force_done = round_no >= self.MAX_ROUNDS
        from app.skills.prompt_utils import render
        instructions = render(
            template, round=round_no, history=history, user_message=user_message,
        )
        if force_done:
            instructions += "\n\n注意：已达上限，必须输出 done:true 的 JSON 摘要。"

        buf = ""
        async for chunk in ctx.deepseek.chat_stream(
            [{"role": "system", "content": "你只输出问题文字或单一 JSON 对象。"},
             {"role": "user", "content": instructions}]
        ):
            buf += chunk

        parsed = self._try_parse_done(buf)
        if parsed is not None:
            session.requirement = RequirementSummary(**parsed["summary"])
            session.phase = "ready"
            req = session.requirement
            summary_md = (
                "**需求摘要**\n\n"
                f"- 目标人群: {req.target_audience or '（未指定）'}\n"
                f"- 场景: {req.scenario or '（未指定）'}\n"
                f"- 特殊需求: {', '.join(req.special_needs) or '无'}\n"
                f"- 备注: {req.notes or '无'}\n\n"
                "如果以上摘要符合预期，请回复\"确认\"以继续生成设计报告；"
                "需要修改请直接说明。"
            )
            session.messages.append(Message(role="assistant", content=summary_md))
            yield SkillEvent(type="chat_message", role="assistant", content=summary_md)
        else:
            question = buf.strip()
            session.messages.append(Message(role="assistant", content=question))
            yield SkillEvent(type="chat_message", role="assistant", content=question)

    @staticmethod
    def _try_parse_done(text: str) -> dict | None:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            obj = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
        if obj.get("done") and "summary" in obj:
            return obj
        return None

def load() -> SocraticSkill:
    yaml_path = os.path.join(os.path.dirname(__file__), "skill.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        meta = SkillMeta(**yaml.safe_load(f))
    return SocraticSkill(meta)
