# AISec-StrikeEval 

## 项目简介

AISec-StrikeEval 用于评估大语言模型在网络安全与渗透测试题库上的表现，支持 Ollama、vLLM、DeepSeek 三种 API 接口。可实时显示进度与准确率并生成 HTML 报告；对不含标准答案的题库支持输出模型答案 JSON。

## 功能特性

- 支持 `ollama` / `vllm` / `deepseek` 三类接口
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
| `--api-type` | 接口类型：`ollama` / `vllm` / `deepseek` | `ollama` |
| `--base-url` | API 服务地址 | 见上文默认值 |
| `--api-key` | API 密钥（DeepSeek 必填，vLLM按需） | 无 |
| `--threads` | 并发线程数 | `4` |
| `--temperature` | 采样温度 | `0.2` |
| `--start` / `--limit` | 起始索引 / 限制数量 | `0` / `0` |

题库固定在 `data` 目录：`StrikeEval.json`、`cissp.json`（含答案）、`cs-eval.json`（无答案）。运行时自动处理，无需传入题库或输出路径参数；报告与答案文件默认生成在当前目录。

### 一键运行（示例使用 vLLM）
```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8
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
- StrikeEval 数据集由 @Bouquets 收集整理 📚
- 特别说明：`cissp` 与 `StrikeEval` 两个数据集均自带标准答案，仅适合流程演示与工具验证，无法作为严肃参考；如需正式评测与提交，请使用 `cs-eval` 数据集并按平台规范提交。

## 注意事项

- 选择 `deepseek` 时必须提供 `--api-key`
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