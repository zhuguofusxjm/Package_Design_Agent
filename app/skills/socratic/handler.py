from __future__ import annotations
import json
import os
import yaml
from typing import AsyncIterator
from app.skills.base import Skill, SkillContext, SkillEvent
from app.models import SkillMeta, Artifact, RequirementSummary, Message

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

        yield SkillEvent(
            type="artifact_started", skill_id=self.meta.id,
            title=self.meta.artifact_title, version=1,
        )

        buf = ""
        async for chunk in ctx.deepseek.chat_stream(
            [{"role": "system", "content": "你只输出问题文字或单一 JSON 对象。"},
             {"role": "user", "content": instructions}]
        ):
            buf += chunk
            yield SkillEvent(type="artifact_delta", skill_id=self.meta.id, chunk=chunk)

        parsed = self._try_parse_done(buf)
        if parsed is not None:
            session.requirement = RequirementSummary(**parsed["summary"])
            session.phase = "ready"
            content = f"### 需求摘要\n- 目标人群: {session.requirement.target_audience}\n- 场景: {session.requirement.scenario}\n- 特殊需求: {', '.join(session.requirement.special_needs) or '无'}\n- 备注: {session.requirement.notes}"
        else:
            session.messages.append(Message(role="assistant", content=buf.strip()))
            content = f"### 第 {round_no} 轮问询\n{buf.strip()}"

        session.artifacts[self.meta.id] = Artifact(
            skill_id=self.meta.id, type="markdown",
            title=self.meta.artifact_title, content=content,
            version=1, status="done",
        )
        yield SkillEvent(
            type="artifact_completed", skill_id=self.meta.id, version=1,
            payload={"phase": session.phase},
        )

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
