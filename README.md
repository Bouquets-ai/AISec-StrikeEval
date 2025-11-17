# AISec-StrikeEval 

[`中文文档`](README_zh.md)

## Project Overview

AISec-StrikeEval evaluates LLMs on cybersecurity and pentest question sets. It supports Ollama, vLLM, and DeepSeek APIs, shows real-time progress and accuracy, generates HTML summary reports, and outputs model answers JSON for datasets without ground-truth answers.

## Features

- Supports `ollama` / `vllm` / `deepseek`
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
  - DeepSeek: `https://api.deepseek.com` (requires `--api-key`)

## Usage

### Entry
```bash
python AISec-StrikeEval.py [args]
```

### Key Arguments (simplified)

| Arg | Description | Default |
|------|------|--------|
| `--model` | Model name (must match deployed) | `llama3` |
| `--api-type` | API type: `ollama` / `vllm` / `deepseek` | `ollama` |
| `--base-url` | API base URL | varies |
| `--api-key` | API key (DeepSeek required, vLLM optional) | None |
| `--threads` | Concurrency | `4` |
| `--temperature` | Sampling temperature | `0.2` |
| `--start` / `--limit` | Start index / limit count | `0` / `0` |

Datasets are under `data`: `StrikeEval.json`, `cissp.json` (with answers), `cs-eval.json` (without answers). Outputs are written to the current directory.

### One-Line Run (vLLM example)
```bash
python AISec-StrikeEval.py --api-type vllm --base-url http://127.0.0.1:8001 --api-key <YOUR_KEY> --model Qwen2.5-7B-Instruct --threads 8
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

## Data Sources & Notes

- cissp dataset: `https://github.com/Clouditera/SecGPT/tree/main/evaltion/cissp_eval`
- cs-eval dataset: `https://github.com/CS-EVAL/CS-Eval`, submission site: `https://cs-eval.com/#/app/home`
- StrikeEval curated by @Bouquets
- Important: `cissp` and `StrikeEval` include ground-truth answers and are suitable for workflow demonstration and tool validation only; not for rigorous benchmarking. For formal evaluation/submission, use `cs-eval`.

## Notes

- DeepSeek requires `--api-key`
- vLLM model name must match the deployed model (e.g., `Qwen2.5-7B-Instruct`)
- Ensure `--base-url` is reachable
- Use `--threads` and `--limit` for large datasets

## Project Files

- `AISec-StrikeEval.py`: main evaluation script and entry
- `data/`: datasets (`StrikeEval.json`, `cissp.json`, `cs-eval.json`)
- `remove_duplicates.py`: deduplicate by question signature
- `reorder_ids.py`: reindex `id` to continuous sequence

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
