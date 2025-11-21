# AISec-StrikeEval 

## 项目简介

AISec-StrikeEval 用于评估大语言模型在网络安全与渗透测试题库上的表现，支持 Ollama、vLLM 两种 API 接口。可实时显示进度与准确率并生成 HTML 报告；对不含标准答案的题库支持输出模型答案 JSON。

## 功能特性

- 支持 `ollama` / `vllm` 两类接口
- 实时进度与准确率统计，终端动态提示
- 生成概览型 HTML 报告（准确率、答对/总数、错误数），不含逐题表
- 自动为无答案题库输出模型答案 JSON（`cs-eval.json`）
- 多线程并发、范围限制、UTF-8/BOM 兼容

## 使用方法

### 脚本入口
```bash
python AISec-StrikeEval.py [参数]
```

### 关键参数（简化）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model` | 模型名称（需与服务加载一致） | `llama3` |
| `--api-type` | 接口类型：`ollama` / `vllm` | `ollama` |
| `--base-url` | API 服务地址 | 见上文默认值 |
| `--api-key` | API 密钥（vLLM 按需） | 无 |
| `--threads` | 并发线程数 | `4` |
| `--temperature` | 采样温度 | `0.7` |
| `--start` / `--limit` | 起始索引 / 限制数量 | `0` / `0` |
| `--show-think` | 终端打印模型推理过程（输出 `<think>...</think>` 或正文前的推理） | 关闭 |
| `--think-max-tokens` | 推理模式下生成长度上限 | `68000` |

题库固定在 `data` 目录：`StrikeEval.json`、`cissp.json`（含答案）、`cs-eval.json`（无答案）。运行时自动处理，无需传入题库或输出路径参数；报告与答案文件默认生成在当前目录。

### 一键运行（示例使用 vLLM）
```bash
# 基本运行
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8

# 显示推理（不限制推理长度）
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen3-4B-Thinking-2507 --threads 8 --dataset strike --show-think --think-max-tokens 68000
```

### 数据集选择（--dataset）

按需选择评测数据集：

- 仅 StrikeEval：
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset strike`
- 仅 cissp：
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset cissp`
- 仅 cs-eval：
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset cs_eval`
- 全部数据集：
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset all`

### 输出文件

- 概览报告：
  - `report_StrikeEval_YYYYMMDD_HHMMSS.html`
  - `report_cissp_YYYYMMDD_HHMMSS.html`
- `cs-eval.json` 答案：
  - `answers_cs_eval_YYYYMMDD_HHMMSS.json`

`cs-eval.json` 答案格式示例：
```json
[
  { "question_id": "1",    "answer": "A" },
  { "question_id": "123",  "answer": "对" },
  { "question_id": "1234", "answer": "是否涉及漏洞：是\n漏洞号：CVE-2024-22891\n影响的产品及版本：Nteract v.0.28.0" }
]
```

### 思考与答案显示

- 单选题强制输出：提示词要求仅输出一行 `Final Answer: <A/B/C/D>`，判分优先匹配该行字母。
- 推理打印：开启 `--show-think` 时，终端展示模型的完整推理；未使用 `<think>` 标签时，将打印最终答案之前的正文作为推理；长度由 `--think-max-tokens` 控制，默认不设限（68000，受服务端与模型上限约束）。

### 分批运行
```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8 --limit 50
```

## 题库格式

- 含答案题库（用于 `mcq`）：每题需包含 `id`、`question`、`options`(含 A/B/C/D)、`answer`
- 无答案题库（用于 `freeform`）：每题需包含 `id`，题目文本可在 `question` 或 `prompt` 字段；可选 `options`

## 数据来源与特别说明

- cissp 数据集来源：`https://github.com/Clouditera/SecGPT/tree/main/evaltion/cissp_eval` 🔗
- cs-eval 数据集来源：`https://github.com/CS-EVAL/CS-Eval`，提交网站：`https://cs-eval.com/#/app/home` 🔗
- StrikeEval 数据集由 @Bouquets收集整理网络安全领域纯中文测试数据集，涵盖十多个安全领域，是对大模型中文安全能力的一次全面检测
- 特别说明：`cissp` 与 `StrikeEval` 两个数据集均自带标准答案，仅适合流程演示与工具验证，无法作为严肃参考；如需正式评测与提交，请使用 `cs-eval` 数据集并按平台规范提交。

## 注意事项

- vLLM 模型名需与服务实际加载一致（如 `Qwen2.5-7B-Instruct`）
- 请确认 `--base-url` 指向正确的服务地址
- 大题库建议使用 `--threads` 与 `--limit` 分批执行

## 贡献指南

欢迎提交 Issue 和 Pull Request 改进项目，感谢 ⭐ Star！
1. 遵循 PEP 8 风格
2. 补充必要文档
3. 基本自测通过

## 许可证

本项目采用 MIT 许可证。

## 推理模型请注意

判断答案截取是否精准，需要进行多次调试，受正则、模型、输出长度、温度、部署方式等的影响。可先把错误问题截取出来，随机选几道错题在 UI 界面（例如 Cherry Studio）进行提问；如果获取到的结果绝大部分和截取到的答案相符，则证明该次测试有效 7/10，或者三次测试取平均，看波动如何一般控制在 ±2 内都比较正常。对于思考模型，核心是改变输出长度等问题；在功能界面已经开通了推理显示、温度控制及错误问题输出，可方便大家调试到最佳状态。当前的配置已经在作者多次尝试之下为较稳妥的解决方案，请勿轻易修改。对于 CS-Eval 数据集，有 12 道题被标记为未知类型，其实就是开放类问题，有 0.27 分，这里不写进脚本以便模型更好的获取答案。

## 使用方法（cs-eval）

要评测 CS-Eval 数据集，可直接运行：

```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://10.4.3.190:8001 --model Qwen3-Next-80B-A3B-Instruct-FP8 --threads 50 --dataset cs_eval
```

运行结束后将在当前目录生成答案文件：`answers_cs_eval_YYYYMMDD_HHMMSS.json`。

## 架构与流程

- 入口：命令行参数解析后，按数据集类型分发到评测或答案生成。
- MCQ 流程：加载/校验题目，线程池并发执行，构造提示词，调用 API，提取选项字母，统计正确率，生成概览 HTML，并可追加错题到 JSON。
- Freeform 流程：加载题目，分级提示词（通用 → 严格 → 更严格），调用 API，基于正则与规则抽取判断（对/错）、单/多选字母或简短文本，生成 `answers_cs_eval_*.json`；为空/未匹配项生成诊断文件。
- 进度：线程安全进度管理器在终端显示动态准确率进度条与逐题结果。

## 参数扩展

- `--summary-only`：生成紧凑型概览 HTML，隐藏逐题表（内部使用）。
- `--show-full`：终端打印模型完整回答，便于调试。
- `--wrong-out <path>`：将评测中的错题追加到指定 JSON 文件。
- `--mcq-file <path>`：评测一个自定义、含答案的 MCQ 题库。
- `--shuffle`：当设置了 `--limit` 时随机抽样。
- `--think-max-tokens`：在启用 `--show-think` 时的最大生成长度（默认 `8192`；思考模型通常建议更大，如 `68000`）。

## 提示与答案抽取

- MCQ：提示词强制单行 `Final Answer: <A/B/C/D>`；提取优先匹配该行，回退到正文中的最后字母。
- Freeform：多阶段提示与正则解析，识别判断（对/错）、单/多选字母或短文本；解析前移除 `<think>` 内容。
- vLLM 同时使用 completion 与 chat 接口；针对 instruct 模型会设置 `stop` 序列（如停在 `你的答案：`）以保持输出简洁。

## 报告与诊断

- 概览报告：包含正确率、答对/总数、错误数等摘要卡片。
- 错题输出：`--wrong-out` 写入数据集、题目 id、题干、选项、标准答案、模型答案等信息。
- 诊断文件：在自由题运行中为空/未匹配项生成 `answers_cs_eval_diagnostics_*.json` 便于排查。

## 特殊处理

- CS‑Eval 的以下题目被设定为输出空答案，以支持开放/未知类型：
  - `1751, 1761, 1762, 1763, 1764, 1766, 1767, 1769, 1770, 2852, 3127, 3129`
  - 在自由题处理阶段于调用模型前直接返回空答案，最终 JSON 中对应 `answer` 为空字符串。

