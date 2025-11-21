# AISec-StrikeEval 

[`中文文档`](README_zh.md)

## Project Overview

 AISec-StrikeEval evaluates LLMs on cybersecurity and pentest question sets. It supports Ollama and vLLM APIs, shows real-time progress and accuracy, generates HTML summary reports, and outputs model answers JSON for datasets without ground-truth answers.

## Features

- Supports `ollama` / `vllm`
- Real-time progress and accuracy statistics
- Generates concise HTML summary (accuracy, correct/total, errors)
- Produces model answers JSON for datasets without answers (`cs-eval.json`)
- Multithreading, range limiting, UTF-8/BOM compatibility

## Installation

- Python 3.7+
- No third-party dependencies (uses Python standard library)
- API services:
  - Ollama: `http://localhost:11434`
  - vLLM: `http://localhost:8000`
  

## Usage

### Entry
```bash
python AISec-StrikeEval.py [args]
```

### Key Arguments (simplified)

| Arg | Description | Default |
|------|------|--------|
| `--model` | Model name (must match deployed) | `llama3` |
| `--api-type` | API type: `ollama` / `vllm` | `ollama` |
| `--base-url` | API base URL | varies |
| `--api-key` | API key (vLLM optional) | None |
| `--threads` | Concurrency | `4` |
| `--temperature` | Sampling temperature | `0.7` |
| `--start` / `--limit` | Start index / limit count | `0` / `0` |
| `--show-think` | Print model thinking in terminal | off |
| `--think-max-tokens` | Max generation length when `--show-think` | `68000` |

Datasets are under `data`: `StrikeEval.json`, `cissp.json` (with answers), `cs-eval.json` (without answers). Outputs are written to the current directory.

### One-Line Run (vLLM example)
```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8

# Show full thinking in terminal
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen3-4B-Thinking-2507 --threads 8 --dataset strike --show-think --think-max-tokens 68000
```

### Outputs
- Summary reports:
  - `report_StrikeEval_YYYYMMDD_HHMMSS.html`
  - `report_cissp_YYYYMMDD_HHMMSS.html`
- `cs-eval.json` answers:
  - `answers_cs_eval_YYYYMMDD_HHMMSS.json`

`cs-eval.json` answer format example:
```json
[
  { "question_id": "1",    "answer": "A" },
  { "question_id": "123",  "answer": "True" },
  { "question_id": "1234", "answer": "Vulnerability involved: Yes\nCVE: CVE-2024-22891\nAffected products and versions: Nteract v0.28.0" }
]
```

### Batch Run
```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8 --limit 50
```

## Dataset Format

- With answers (for `mcq`): each item must include `id`, `question`, `options` (A/B/C/D), and `answer`
- Without answers (for `freeform`): must include `id`, text in `question` or `prompt`, optional `options`

## Output Description

Terminal: real-time progress, results, final statistics, elapsed time
HTML: summary report (accuracy, correct/total, errors), no per-question table
JSON: model answers for `cs-eval.json` as shown above

### Thinking & Answers

- MCQ prompt enforces a single-line `Final Answer: <A/B/C/D>`; extraction prefers this line.
- With `--show-think`, terminal prints the full reasoning (`<think>` or the pre-answer body). Length controlled by `--think-max-tokens` (default 68000; actual limits depend on server/model).

## Data Sources & Notes

- cissp dataset: `https://github.com/Clouditera/SecGPT/tree/main/evaltion/cissp_eval`
- cs-eval dataset: `https://github.com/CS-EVAL/CS-Eval`, submission site: `https://cs-eval.com/#/app/home`
- StrikeEval curated by @Bouquets
- Important: `cissp` and `StrikeEval` include ground-truth answers and are suitable for workflow demonstration and tool validation only; not for rigorous benchmarking. For formal evaluation/submission, use `cs-eval`.

## Notes

- vLLM model name must match the deployed model (e.g., `Qwen2.5-7B-Instruct`)
- Ensure `--base-url` is reachable
- Use `--threads` and `--limit` for large datasets

## Project Files

- `AISec-StrikeEval.py`: main evaluation script and entry
- `data/`: datasets (`StrikeEval.json`, `cissp.json`, `cs-eval.json`)

## Contribution

PRs and Issues are welcome — and ⭐ Stars appreciated!
1. Follow PEP 8
2. Update docs where needed
3. Add basic self-tests

## License

MIT License.
### Dataset Selection (`--dataset`)

- StrikeEval only:
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset strike`
- cissp only:
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset cissp`
- cs-eval only:
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset cs_eval`
- All datasets:
  - `python AISec-StrikeEval.py --api-type vllm --base-url <URL> --api-key <KEY> --model <MODEL> --threads 8 --dataset all`

## 使用方法（cs-eval）

要评测 CS-Eval 数据集，可直接运行：

```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://10.4.3.190:8001 --model Qwen3-Next-80B-A3B-Instruct-FP8 --threads 50 --dataset cs_eval
```

运行结束后将在当前目录生成答案文件：`answers_cs_eval_YYYYMMDD_HHMMSS.json`。

## Architecture & Flow

- Entry: CLI parses args and dispatches to evaluation or answer generation.
- MCQ flow: loads/validates questions, runs with thread pool, builds prompts, calls API, extracts choice, tracks correctness, renders summary HTML, optionally appends wrong items.
- Freeform flow: loads questions, builds tiered prompts, calls API, extracts text/judgement/multi‑select letters via heuristics, writes `answers_cs_eval_*.json`, produces diagnostics for empty/unmatched cases.
- Progress: thread‑safe progress manager outputs dynamic accuracy bar and per‑item summary in terminal.

## Additional Arguments

- `--summary-only`: render compact HTML overview without per‑question table (used internally).
- `--show-full`: print full model responses in terminal for debugging.
- `--wrong-out <path>`: append wrong answers to a JSON file for later review.
- `--mcq-file <path>`: evaluate a custom MCQ JSON with answers.
- `--shuffle`: randomize selection when `--limit` is set.
- `--think-max-tokens`: max generation when `--show-think` (default `8192`; thinking models often benefit from larger values such as `68000`).

## Answer Extraction & Prompting

- MCQ: prompts enforce a single line `Final Answer: <A/B/C/D>`; extraction prefers this line and falls back to last letter in body.
- Freeform: multi‑stage prompts (generic → strict → stricter) and regex‑based parsing to detect judgement (对/错), single/multi‑select letters, or short text answers. `<think>` blocks are removed for parsing.
- vLLM uses both completion and chat endpoints; `stop` sequences are applied to keep outputs concise (e.g., stopping at `你的答案：`).

## Reports & Diagnostics

- HTML overview: accuracy, correct/total, errors, summary cards.
- Wrong‑items output: `--wrong-out` writes dataset, id, question, options, standard answer, model answer.
- Diagnostics: freeform run emits `answers_cs_eval_diagnostics_*.json` with empty/unmatched cases for inspection.

## Special Handling

- Blank answers for specific CS‑Eval questions are returned intentionally to support open or unknown types:
  - IDs: `1751, 1761, 1762, 1763, 1764, 1766, 1767, 1769, 1770, 2852, 3127, 3129`
  - Implemented in the freeform pipeline before API calls, so these entries appear with empty `answer` in the output.

## Inference Model Notes

Determining whether answer extraction is accurate requires repeated tuning; it is affected by regex patterns, the model itself, output length, temperature, and deployment mode. A practical workflow is to first collect wrongly extracted items, then randomly pick several of these and ask the same questions in a UI (e.g., Cherry Studio). If the results largely match the extracted answers, you can consider the run effective (e.g., 7/10). Alternatively, run three tests and take the average; typical fluctuation within ±2 is normal. For thinking-style models, the core lever is output length. The UI already enables showing reasoning, temperature control, and exporting wrong-question items, which helps you tune to a stable state. The current configuration reflects many iterations by the author and is a relatively stable solution—please avoid changing it lightly. For the CS‑Eval dataset, 12 questions are tagged as “unknown type” (open-ended) worth 0.27 points; we do not hard-code these in the script so the model can better obtain answers.

## Dataset Overview

- CS‑EVAL: Curated by @CS‑EVAL, a comprehensive evaluation suite for cybersecurity foundation models or LLMs. Covers 11 major domains and 42 subdomains with 4,369 multiple‑choice, true/false, and knowledge‑extraction questions, providing both knowledge‑oriented and practice‑oriented tasks.
- StrikeEval: Curated by @Bouquets, a pure Chinese cybersecurity test set spanning more than ten security domains, used to comprehensively assess Chinese security capability in LLMs.
- cissp: Curated by @Clouditera, aligned with the authoritative CISSP certification system. Evaluates knowledge coverage and answer accuracy across security management, access control, risk governance, etc., suitable for gauging general InfoSec mastery.
