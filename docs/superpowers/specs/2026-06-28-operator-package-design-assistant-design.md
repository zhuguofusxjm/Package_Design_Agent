# 运营商套餐设计辅助智能体 — 设计文档

**日期**：2026-06-28
**作者**：brainstorming session
**状态**：草案，待评审

---

## 1. 项目目标

为运营商 MKT 人员提供一个对话式套餐设计辅助智能体。用户用一句话描述设计意图（例："帮我设计一个世界杯套餐"），系统通过苏格拉底式问询澄清需求，再调度多个 Skill 串行产出一份完整设计报告：设计标签建议、匹配案例、LLM 通用建议、看自己（运营商自身画像）、看对手（竞品画像）、Summary。

报告生成后用户可继续追问；系统按 ReAct 模式判断要刷新哪些 Skill，做增量重跑，最小化重复劳动。

## 2. 范围与非目标

**在范围内**：
- 单会话对话式交互（Manus/Gemini 风格分栏 UI）
- 7 个 Skill 的串行编排与增量调度
- 预置标签库、案例库、运营商档案的 JSON 静态数据
- DeepSeek 流式 LLM 调用

**不在范围内（原型阶段）**：
- 多用户/鉴权
- 会话持久化（重启即丢）
- 真实运营商数据接入
- 双语切换（仅中文）
- 多步 Agent 自循环（仅单步 ReAct）

## 3. 技术栈

- **后端**：Python 3.11 + FastAPI + SSE 流式推送
- **前端**：单页 HTML + Tailwind CSS + Alpine.js
- **LLM**：DeepSeek（环境变量 `DEEPSEEK_API_KEY`）
- **数据**：JSON 文件静态预置，启动时加载到内存
- **会话**：进程内字典，`session_id` 存于浏览器 localStorage

## 4. 架构总览

### 4.1 后端目录结构

```
app/
  main.py                       FastAPI 入口
  api/
    chat.py                     POST /api/chat, GET /api/stream/{sid}
    cases.py                    GET /api/cases/{case_id}
  services/
    orchestrator.py             SkillRunner，统一执行入口
    dispatcher.py               ReAct 调度器（决定增量重跑哪些 skill）
    deepseek_client.py          DeepSeek 流式封装
    session_store.py            进程内会话字典
    data_loader.py              启动时加载 tags/cases/operator_profile
  skills/
    __init__.py                 启动时扫描 skills/* 注册
    base.py                     Skill 抽象基类、SkillContext、SkillEvent
    registry.py                 SkillRegistry，DAG 构造与拓扑排序
    socratic/{skill.yaml,prompt.md,handler.py}
    tag_inference/{skill.yaml,prompt.md,handler.py}
    case_match/{skill.yaml,handler.py}         # 无 LLM，无 prompt
    llm_supplement/{skill.yaml,prompt.md,handler.py}
    self_analysis/{skill.yaml,prompt.md,handler.py}
    competitor_analysis/{skill.yaml,prompt.md,handler.py}
    summary/{skill.yaml,prompt.md,handler.py}
    dispatcher/{skill.yaml,prompt.md,handler.py}   # ReAct 决策器，不在 DAG 中
  data/
    tags.json                   预置设计标签
    cases.json                  预置全球案例（含 tag_ids 关联）
    operator_profile.json       虚拟运营商档案（含 self + competitors）
  models/
    session.py                  Session, Message, Artifact, RequirementSummary
    skill_meta.py               SkillMeta（从 skill.yaml 解析）
static/
  index.html
  app.js
  style.css
```

### 4.2 前端布局

```
┌──────────────────────────────────────────────────────────────┐
│  左侧：聊天流（≈55%）         │  右侧：分栏（≈45%，可折叠）  │
│  ─ 用户消息                   │  Tab: [思考过程][设计标签]   │
│  ─ Assistant 消息             │       [LLM补充][看自己]      │
│  ─ "看对手已更新（v2）        │       [看对手][Summary]      │
│    → 查看正文" 卡片           │       [匹配案例]             │
│                               │  ─ 当前 tab 渲染对应 artifact│
└──────────────────────────────────────────────────────────────┘
```

- 默认右侧折叠，首次产出 artifact 时自动展开并定位到对应 tab
- 用户可手动折叠/展开；聊天流里点"查看正文"再次打开
- 案例 tab 内为卡片网格，点单张卡片打开案例详情抽屉

## 5. 核心概念

### 5.1 Skill

每个关键步骤是一个独立 Skill 模块。Skill 是自描述、可独立测试、可独立调优的最小调度单元。

**目录约定**：每个 Skill 一个文件夹，包含：

- `skill.yaml` — 元数据（id、name、依赖、是否传染、是否调 LLM）
- `prompt.md` — 提示词模板（若调用 LLM）
- `handler.py` — `Skill` 子类，实现 `async run(ctx) -> AsyncIterator[SkillEvent]`

**skill.yaml 示例**（`tag_inference/skill.yaml`）：

```yaml
id: tag_inference
name: 设计标签推理
description: 基于需求分析结论推理 1-3 个最适合的设计标签
artifact_type: tag_list
artifact_title: 设计标签建议
depends_on: [socratic]
inputs: [requirement_summary]
outputs: [selected_tags, reasoning]
uses_llm: true
streaming: true
propagate_downstream: true   # 上游变化时本 skill 是否自动重跑
```

**Skill 基类**：

```python
class Skill(ABC):
    meta: SkillMeta

    @abstractmethod
    async def run(self, ctx: SkillContext) -> AsyncIterator[SkillEvent]:
        ...
```

`SkillContext` 提供：会话历史、`artifacts: dict[skill_id, Artifact]`、预置数据访问器、DeepSeek 客户端、可选的 `hint`（dispatcher 重跑时附带的额外提示）。

### 5.2 Artifact

Artifact 是 Skill 的可视化产出物。右侧分栏的每个 tab = 一个 Artifact。

```python
class Artifact:
    skill_id: str
    type: Literal["markdown", "tag_list", "case_cards"]
    title: str
    content: Any              # markdown 字符串 / 结构化 JSON
    version: int              # 每次重跑 +1
    status: Literal["pending", "streaming", "done", "error"]
    created_at: datetime
```

**七个 Skill 与 Artifact 映射**：

| skill_id | title | type | content |
|---|---|---|---|
| socratic | 思考过程 | markdown | 苏格拉底问询记录 + 需求摘要 |
| tag_inference | 设计标签建议 | tag_list | `[{tag_id, name, reason}, ...]` |
| case_match | 匹配案例 | case_cards | `[{case_id, name, score, summary}, ...]` |
| llm_supplement | LLM 补充建议 | markdown | LLM 通用推理结论 |
| self_analysis | 看自己 | markdown | 基于运营商画像的补充推理 |
| competitor_analysis | 看对手 | markdown | 基于竞品画像的对比建议 |
| summary | Summary | markdown | 整合全部上游的最终报告 |

**Artifact 的角色**：

1. 前端渲染源：每个 tab 按 `type` 选渲染组件
2. Skill 间数据通道：下游 Skill 从 `ctx.artifacts[upstream_id].content` 读上游产出
3. 增量重跑最小单元：重跑某个 Skill = 重新生成其 Artifact，`version += 1`
4. 会话状态具象化：`session.artifacts` 序列化即可还原报告全貌

### 5.3 Message vs Artifact

- **Message** — 聊天流里的对话气泡，按时间顺序，用户和 assistant 交替产生
- **Artifact** — 右侧分栏的工件，按 skill_id 索引，同一 Skill 永远占用同一 tab

聊天流出现的"看对手已更新（v2）→ 查看正文"卡片是一条 Message，通过 `skill_id` 指向 Artifact，点击切换右侧 tab。

## 6. 会话状态机

```python
class Session:
    session_id: str
    messages: list[Message]
    requirement: RequirementSummary | None
    artifacts: dict[str, Artifact]            # skill_id → 当前版本
    artifact_versions: dict[str, list[Artifact]]  # skill_id → 历史版本
    phase: Literal["socratic", "ready", "running", "idle"]
    socratic_round: int                       # 当前问询轮数
```

**phase 状态机**：

```
       用户首次输入需求
              │
              ▼
        ┌─ socratic ─┐
        │            │  最多 5 轮问询，用户可随时跳过
        │   生成摘要  │
        ▼            │
       ready  ←──────┘
        │
        │ 用户确认需求摘要
        ▼
      running  ── Full Run 执行 ──┐
        │                          │
        │ 全部 skill 完成           │
        ▼                          │
       idle  ←──────────────────  │
        │                          │
        │ 用户追加问题              │
        ▼                          │
     dispatcher 决策                │
        ├─ action: chat             │
        │   └─→ idle（仅回复，不跑 skill）
        ├─ action: revise_requirement
        │   └─→ ready（用户再确认）
        └─ action: rerun
            └─→ running ── Incremental Run ──┘
```

**关键状态字段**：
- `phase` 决定当前能接受什么操作：socratic 阶段只能回答问询；ready 阶段只能确认或修改需求；idle 阶段才能追加问题
- `socratic_round` 防止苏格拉底环节无限提问，超过 5 轮强制总结
- `artifact_versions` 保留历史版本，便于 UI 提供"回到 v1"和差异对比（v1 实现可不暴露，先保存）

## 7. Skill DAG

```
socratic
   ↓
tag_inference
   ↓
   ├──→ case_match ─────────────┐
   ├──→ llm_supplement ─────────┤
   ├──→ self_analysis ──────────┤
   └──→ competitor_analysis ────┤
                                ↓
                             summary
```

case_match / llm_supplement / self_analysis / competitor_analysis **彼此独立**，并列消费 tag_inference 产物。summary 依赖前面全部。

## 8. 执行模式

### 8.1 Full Run（首次执行）

触发：用户在 `ready` 阶段确认需求摘要。

注：`socratic` Skill 在 phase=`socratic` 阶段已单独执行（多轮问询），产出 `requirement_summary`。Full Run 从 `tag_inference` 开始执行链路上其余 6 个 Skill。

```
phase = running
runner.run_all(ctx)
  ├─ 拓扑排序得到执行顺序：
  │   [tag_inference, case_match, llm_supplement,
  │    self_analysis, competitor_analysis, summary]
  ├─ for skill in order:
  │     emit ArtifactStarted(skill.id, version=1)
  │     async for delta in skill.run(ctx):
  │         累积 delta 到 ctx.artifacts[skill.id].content
  │         emit ArtifactDelta(skill.id, delta)
  │     emit ArtifactCompleted(skill.id, version=1)
  └─ phase = idle
```

严格串行执行：第 N 个 Skill 启动时，前 N-1 个的 Artifact 已写入 `ctx.artifacts`，自然可读。

### 8.2 Incremental Run（增量重跑）

触发：用户在 `idle` 阶段发送追问消息。

流程：

```
1. dispatcher.decide(user_message, session) → DispatchDecision
2. 根据 decision.action 分支：
   - chat              → 直接回复，phase 保持 idle
   - revise_requirement → 更新 requirement，phase = ready
   - rerun(skills)     → runner.run_partial(skills, ctx)
```

`run_partial` 执行步骤：

```
runner.run_partial(seed_skills: list[str], ctx, hint: str | None)
  ├─ 计算最终重跑集 = compute_rerun_set(seed_skills)
  │   （传染规则见 §9）
  ├─ 按 DAG 拓扑排序
  ├─ 对每个 skill：
  │     旧 artifact 入 ctx.artifact_versions[skill.id]
  │     新 version = 旧 version + 1
  │     执行 skill.run(ctx, hint=hint)
  │     发 SSE 事件
  └─ phase = idle
```

## 9. 传染设计（核心规则）

### 9.1 设计原则

**默认不传染，按 skill 显式声明决定是否随上游变化自动重跑**。这条规则覆盖朴素的"DAG 下游闭包"。

每个 Skill 在 `skill.yaml` 中声明 `propagate_downstream: bool`：
- `true` — 当上游 artifact 变化时，本 Skill 应被自动加入重跑集
- `false` — 即便上游变化，本 Skill 不自动重跑（保留旧版，用户可手动追问）

### 9.2 各 Skill 的 propagate 声明

| Skill | propagate_downstream | 理由 |
|---|---|---|
| socratic | n/a（根节点） | — |
| tag_inference | true | 需求变 → 标签必须重新推理 |
| case_match | false | 标签是弱信号，旧匹配仍有参考价值，用户可主动要求换 |
| llm_supplement | false | 通用推理变化空间小，避免不必要的 LLM 调用 |
| self_analysis | false | 看自己结论变化空间小 |
| competitor_analysis | false | 看对手结论变化空间小 |
| summary | true | 任何上游变化都必须刷新汇总 |

### 9.3 传染集计算算法

```python
def compute_rerun_set(seed_skills: list[str], dag: SkillDAG) -> list[str]:
    """
    输入：用户/dispatcher 指定要重跑的 skill 集合
    输出：最终要重跑的 skill 集合（按拓扑序）

    规则：propagate_downstream=true 的 skill，只要它的"任一传递闭包祖先"
    出现在 rerun 集合中，就把自己加入。反复扫描直到稳定。
    """
    rerun = set(seed_skills)
    changed = True
    while changed:
        changed = False
        for s in dag.all_skills():
            if s.id in rerun:
                continue
            if not s.propagate_downstream:
                continue
            if dag.has_ancestor_in(s.id, rerun):  # 传递闭包检查
                rerun.add(s.id)
                changed = True
    return dag.topological_sort(rerun)
```

要点：
- 传染基于**传递闭包**而非直接 downstream，因此 `summary` 即使不直接依赖 `tag_inference`，只要其链路上游 `case_match` 等之上是 `tag_inference`，标签变化也会触发 summary
- 只有 `propagate_downstream=true` 的 skill 才会被卷入
- 传染是可传递的：A → B → C，若 B 和 C 都标记 propagate，A 变会同时拉到 B 和 C
- summary 因为标 true，几乎所有重跑都会带上它

### 9.4 常见场景的实际重跑集

| 用户操作 | seed_skills | 最终重跑集 |
|---|---|---|
| 改需求摘要（phase 回到 ready 后再次确认） | 走 Full Run，非 run_partial | 全部 6 个（tag_inference → summary） |
| 换设计标签 | [tag_inference] | [tag_inference, summary] |
| 只补充看对手 | [competitor_analysis] | [competitor_analysis, summary] |
| 只换案例匹配口径 | [case_match] | [case_match, summary] |
| 追问 summary 措辞 | [summary] | [summary] |
| 同时要求换标签+刷新看对手 | [tag_inference, competitor_analysis] | [tag_inference, competitor_analysis, summary] |

**关于"换设计标签"的特别说明**：DAG 上 case_match / llm_supplement / self_analysis / competitor_analysis 确实消费 tag_inference 的产物，但它们的 `propagate_downstream=false`，所以标签换了之后它们保留旧版本。用户若想让其中某个跟着新标签更新，需要明确追问（dispatcher 会路由到对应 Skill）。这把控制权留给用户，避免一次小调整引发全量 LLM 调用。

## 10. ReAct Dispatcher

### 10.1 Dispatcher 本身是一个 Skill

`app/skills/dispatcher/` 与其他 Skill 同构。它在 `idle` 阶段被调用，输入用户消息和当前会话状态，输出结构化决策 JSON。

### 10.2 Prompt 大意

```
你是套餐设计 Agent 的调度器。

当前会话已有 artifacts：
{artifact_index}  // skill_id + title + 摘要

用户新消息：
{user_message}

请输出 JSON 决策：
  {"action": "chat", "reply": "..."}                  // 闲聊/澄清
  {"action": "revise_requirement", "patch": {...}}    // 改需求
  {"action": "rerun", "skills": [...], "hint": "..."} // 重跑 skill

仅输出 JSON，不要其他文字。
```

### 10.3 ReAct 阶段映射

| ReAct 阶段 | 对应实现 |
|---|---|
| Reason | dispatcher 用 LLM 输出 action JSON |
| Act | SkillRunner 执行决策中的 skills |
| Observe | 执行结果写入 ctx.artifacts，下次 dispatcher 调用时读到 |

**单步 ReAct**：一次决策 → 一次执行 → 等用户。不引入多步自循环。后续若需要"自主迭代"，再挂 critic skill 反馈即可。

## 11. 数据预置

### 11.1 tags.json

```json
[
  {
    "id": "try_and_buy",
    "name": "TryAndBuy",
    "description": "用户先免费试用一段时间，期满后按使用情况转付费",
    "applicable_audience": ["新用户", "价格敏感型"],
    "applicable_scenarios": ["新业务推广", "高端服务试水"]
  },
  { "id": "user_get_user", "name": "UserGetUser", ... },
  { "id": "tiered_billing", "name": "分档计费", ... }
]
```

### 11.2 cases.json

```json
[
  {
    "id": "case_001",
    "name": "T-Mobile 5G Home Internet 试用计划",
    "operator": "T-Mobile",
    "region": "US",
    "tag_ids": ["try_and_buy", "tiered_billing"],
    "summary": "...",
    "detail_md": "..."
  }
]
```

### 11.3 operator_profile.json

```json
{
  "self": {
    "name": "Acme Mobile",
    "user_segments": [...],
    "current_packages": [...]
  },
  "competitors": [
    { "name": "Beta Telecom", "packages": [...] },
    { "name": "Gamma Wireless", "packages": [...] }
  ]
}
```

## 12. 案例匹配算法

`case_match` Skill 不调 LLM，纯标签交集打分：

```python
def match(selected_tag_ids: set[str], cases: list[Case]) -> list[ScoredCase]:
    scored = []
    for case in cases:
        intersection = set(case.tag_ids) & selected_tag_ids
        if not intersection:
            continue
        score = len(intersection) / len(selected_tag_ids | set(case.tag_ids))  # Jaccard
        scored.append(ScoredCase(case, score, list(intersection)))
    scored.sort(key=lambda x: -x.score)
    return scored[:10]
```

返回 ≤10 个案例。不足 10 个则全部返回。

## 13. API 接口

### 13.1 POST /api/chat

```
Request:  { session_id: str, message: str }
Response: { ok: true, stream_url: "/api/stream/{session_id}" }
```

服务端接收消息后入队，立即返回；前端打开 SSE 连接接收事件。

### 13.2 GET /api/stream/{session_id}

SSE 事件流，事件类型：

```json
{"type": "chat_message", "role": "assistant", "content": "..."}
{"type": "phase_change", "phase": "running"}
{"type": "artifact_started", "skill_id": "...", "title": "...", "version": 2}
{"type": "artifact_delta", "skill_id": "...", "chunk": "..."}
{"type": "artifact_completed", "skill_id": "...", "version": 2}
{"type": "run_completed"}
{"type": "error", "message": "..."}
```

### 13.3 GET /api/cases/{case_id}

返回单个案例的完整 detail_md，用于案例详情抽屉。

## 14. 错误处理

- **DeepSeek 调用失败**：重试 2 次（指数退避 1s/3s），仍失败则发 `error` 事件，对应 Artifact 状态置 `error`，前端 tab 显示"生成失败 - 重试"按钮
- **JSON 解析失败（dispatcher 输出非合法 JSON）**：fallback 到 `action: chat`，把原始输出作为 reply 返回
- **Skill 内部异常**：捕获后转为 `error` 事件，不中断整条任务链；后续 Skill 若依赖失败 Skill 的 artifact，跳过自身并标 error
- **会话不存在**：返回 404，前端清空 localStorage 中的 session_id 并重新初始化

## 15. 测试策略

原型阶段最小测试集：

- **单元测试**：每个 Skill 的 handler 用 mock DeepSeek 客户端测一遍输入输出契约；`compute_rerun_set` 用 6 个传染场景表驱动测试
- **集成测试**：一条端到端"世界杯套餐"用例，验证从用户输入到 summary 产出的完整事件流
- **手动验收**：浏览器实操苏格拉底问询、Full Run、三种增量重跑场景（换标签、补看对手、追问 summary 措辞）

不引入 e2e 浏览器自动化测试（原型阶段成本过高）。

## 16. 一些明确的取舍

- **不做用户鉴权与持久化** — 原型重点是 Skill 调度与 ReAct，不是工程化
- **不做并发执行** — 严格串行更易调试和流式展示，原型 7 个 Skill 串行延迟可接受
- **不做案例向量化** — 标签交集已足够展示思路；向量检索是优化点不是核心
- **不做多步 Agent 自循环** — 单步 ReAct 已覆盖原型场景，避免失控
- **dispatcher 输出非法 JSON 时不自我修复** — fallback 到 chat 模式，等用户重述
