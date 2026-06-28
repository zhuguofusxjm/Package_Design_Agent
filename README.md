# 运营商套餐设计辅助智能体（原型）

## 启动

1. 安装依赖: `pip install -e ".[dev]"`
2. 复制 `.env.example` 为 `.env` 并填入 `DEEPSEEK_API_KEY`
3. 运行: `uvicorn app.main:app --reload --port 8000`
4. 浏览器打开 http://localhost:8000

## 测试

`pytest -v`

## 目录速览

- `app/skills/*` — 每个文件夹一个 Skill，含 yaml + prompt + handler
- `app/services/orchestrator.py` — Full Run 与 Partial Run
- `app/data/*.json` — 预置标签 / 案例 / 运营商档案
- `static/` — 单页前端
