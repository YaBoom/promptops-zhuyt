# PromptOps CLI 🐍

> Python 实现的轻量级提示词工程运营工具 - 让提示词具备"可协作、可审查、可回滚、可监控"能力

## 为什么选择 Python？

PromptOps 的核心场景是**提示词测试与评估**，Python 在这方面有天然优势：

- ✅ **LLM 生态最强**：LangChain、DSPy、Langfuse SDK 均以 Python 为主
- ✅ **AI 评估工具链**：promptlayer、humanloop、deepeval 等
- ✅ **数据分析能力**：pandas、numpy 处理测试数据
- ✅ **Jupyter 集成**：交互式开发和调试

## 核心能力

### 1️⃣ 版本管理（Git for Prompts）
```bash
# 初始化项目
promptops init my-project

# 创建新提示词
promptops new code-review --model deepseek-chat --author jack.zhu

# 查看版本历史
promptops history code-review

# 回滚版本
promptops rollback code-review v1.2.0
```

### 2️⃣ 真实 LLM 测试（集成 OpenAI / DeepSeek / Anthropic SDK）
```bash
# 运行测试套件（真实调用 API）
promptops test code-review --live

# 生成质量报告
promptops report code-review --output metrics.json
```

### 3️⃣ DSPy 风格评估
```python
from promptops import Evaluator

evaluator = Evaluator()
result = evaluator.evaluate(
    prompt_name="code-review",
    test_cases=[...],
    metrics=["accuracy", "latency", "cost"]
)
print(result.accuracy)  # 0.97
print(result.latency_p95)  # 340ms
```

### 4️⃣ 部署控制
```bash
# 推送到 staging
promptops deploy code-review --env staging

# 灰度发布
promptops rollout code-review --percentage 10
```

## 提示词结构规范

```yaml
# prompts/code-review.yaml
name: code-review
version: 2.0.0
model: deepseek-chat
author: jack.zhu
created_at: 2026-05-25T12:00:00
tags: [production, security]

content: |
  你是一位资深代码审查专家...

tests:
  - input: "function foo() { return eval(userInput); }"
    expected:
      security: high
      type: code-injection
  
  - input: "const data = []; ..."
    expected:
      performance: medium

thresholds:
  accuracy: 0.95
  latency_ms: 500
  cost_per_request: 0.01
```

## 技术架构

```
PromptOps CLI (Python)
│
├── Version Manager (Git-based)
│   ├── Semantic versioning (v1.0.0)
│   ├── Rollback mechanism
│   └── Diff visualization
│
├── LLM Tester (真实 API 调用)
│   ├── OpenAI SDK 集成
│   ├── DeepSeek SDK 集成 (OpenAI 兼容 API)
│   ├── Anthropic SDK 集成
│   └── Cost tracking
│
├── Evaluator (DSPy 风格)
│   ├── LLM-as-judge
│   ├── Heuristic evaluators
│   └── Custom metrics
│
└── Deployment System
    ├── Environment progression
    ├── Traffic shifting
    └── A/B testing
```

## 快速开始

```bash
# 安装
pip install promptops-zhuyt

# 初始化
promptops init your-project

# 创建提示词
promptops new code-review --author jack.zhu

# 配置 API Key（按需选择）
export DEEPSEEK_API_KEY=sk-xxx        # DeepSeek（默认模型）
export OPENAI_API_KEY=sk-xxx           # OpenAI
export ANTHROPIC_API_KEY=sk-ant-xxx    # Anthropic

# 运行测试
promptops test code-review --live

# 查看帮助
promptops --help
```

## 实战案例

```bash
# 电商推荐系统迭代

# 1. 创建初始版本
promptops init ecommerce-recommendation
promptops new product-suggest --model claude-3.7-opus

# 2. 编辑提示词
vim prompts/product-suggest.yaml

# 3. 运行真实 LLM 测试
promptops test product-suggest --live --sample 100
# ✅ 150/150 通过，准确率 97.3%
# 💰 总成本: $2.34

# 4. 审批变更
promptops approve product-suggest v2.0.0 --reviewer alice

# 5. 灰度发布
promptops rollout product-suggest --percentage 10 --monitor

# 6. 监控指标
promptops metrics product-suggest --watch
# 📊 转化率: +15%
#    响应时间: 320ms (p95)
#    用户满意度: 4.3/5

# 7. 全量发布
promptops deploy product-suggest --env production
```

## 与现有工具对比

| 特性 | promptops-zhuyt | Langfuse | PromptLayer | DSPy |
|------|-----------------|----------|-------------|------|
| 语言 | Python ✅ | Python/TS | Python/JS | Python ✅ |
| 真实 LLM 测试 | ✅ | ✅ | ❌ | ✅ |
| DSPy 风格评估 | ✅ | ❌ | ❌ | ✅ |
| 数据分析 | ✅ pandas | ❌ | ❌ | ❌ |
| CLI 体验 | ✅ | ❌ Web | ❌ | ❌ |
| 开源 | ✅ MIT | ✅ Apache | ❌ | ✅ MIT |

## 适用场景

- ✅ 小团队（2-10人）快速落地 PromptOps
- ✅ 需要真实 LLM API 测试
- ✅ 数据驱动的提示词优化
- ✅ Jupyter 交互式开发

## 贡献指南

欢迎提交 PR！

```bash
git clone https://github.com/YaBoom/promptops-zhuyt.git
cd promptops-zhuyt
pip install -e ".[dev]"
pytest tests/
```

## License

MIT © 2026 jack.zhu

---

**让提示词成为可追踪、可验证的工程资产** 🚀