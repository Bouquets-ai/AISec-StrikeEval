import json
import os
import sys
import time
import random
import argparse
import html
import re
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import request, error


def load_questions(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    questions = []
    for q in data:
        idv = q.get('id') or q.get('question_id')
        question = q.get('question')
        options = q.get('options')
        answer = q.get('answer')
        if idv is None or question is None or options is None or answer is None:
            continue
        questions.append({
            'id': str(idv),
            'question': question,
            'options': options,
            'answer': answer,
        })
    return questions

def analyze_questions_file(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    valid = []
    invalid = []
    for q in data:
        idv = q.get('id') or q.get('question_id')
        question = q.get('question')
        options = q.get('options')
        answer = q.get('answer')
        if idv is None or question is None or options is None or answer is None:
            invalid.append({
                'id': idv,
                'has_question': question is not None,
                'has_options': options is not None,
                'has_answer': answer is not None,
            })
        else:
            valid.append({
                'id': str(idv),
                'question': question,
                'options': options,
                'answer': answer,
            })
    return valid, invalid

def load_questions_freeform(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    questions = []
    for q in data:
        if 'id' in q and ('question' in q or 'prompt' in q):
            nq = {
                'id': q['id'],
                'question': q.get('question') or q.get('prompt') or '',
                'options': q.get('options') or {}
            }
            if nq['question']:
                questions.append(nq)
    return questions


def build_prompt(q):
    instruction = (
        "请直接给出答案，不要解释。\n"
        "若为选择题（出现A-D选项或题干含‘单选题/多选题’），仅输出字母；\n"
        "若为判断题，仅输出‘对’或‘错’；\n"
        "最后一行使用 ‘Final Answer: <答案>’ 标注最终答案。\n"
    )
    options = q.get('options', {})
    opt_lines = [
        f"A. {options.get('A', '')}",
        f"B. {options.get('B', '')}",
        f"C. {options.get('C', '')}",
        f"D. {options.get('D', '')}",
    ]
    prompt = f"{instruction}\n题目：{q.get('question','')}\n选项：\n" + "\n".join(opt_lines) + "\n你的答案："
    return prompt

def build_prompt_freeform(q):
    instruction_selective = (
        "请直接给出答案，不要解释。\n"
        "若为选择题（出现A-D选项或题干含‘单选题/多选题’），仅输出字母；若为多选题，输出所有符合的选项字母，并用逗号分隔（例如 A,B,D）；\n"
        "若为判断题，仅输出‘对’或‘错’；\n"
        "最后一行使用 ‘Final Answer: <答案>’ 标注最终答案。\n"
    )
    instruction_generic = (
        "请直接给出答案，不要解释。\n"
        "若为判断题，仅输出‘对’或‘错’；\n"
        "其它题型请输出简洁文本答案。\n"
        "最后一行使用 ‘Final Answer: <答案>’ 标注最终答案。\n"
    )
    options = q.get('options', {})
    opt_lines = []
    if options:
        opt_lines = [
            f"A. {options.get('A', '')}",
            f"B. {options.get('B', '')}",
            f"C. {options.get('C', '')}",
            f"D. {options.get('D', '')}",
        ]
    opt_block = ("\n选项：\n" + "\n".join(opt_lines)) if opt_lines else ""
    qtext = q.get('question') or q.get('prompt') or ''
    lt = str(qtext).lower()
    detected = None
    if ("多选题" in str(qtext)) or ("multiple-choice" in lt) or ("multiple choice" in lt):
        detected = "多选题"
    elif ("单选题" in str(qtext)) or ("single-choice" in lt) or ("single choice" in lt):
        detected = "单选题"
    elif ("判断题" in str(qtext)) or ("true/false" in lt) or ("true or false" in lt) or ("判断" in str(qtext)):
        detected = "判断题"
    elif options:
        detected = "单选题"
    type_line = f"当前题型：{detected}\n" if detected else ""
    use_selective = bool(detected in ("单选题","多选题")) or bool(options)
    instruction = instruction_selective if use_selective else instruction_generic
    prompt = f"{instruction}\n{type_line}题目：{q.get('question','')}" + opt_block + "\n你的答案："
    return prompt

def build_prompt_freeform_strict(q):
    options = q.get('options', {})
    opt_lines = []
    if options:
        opt_lines = [
            f"A. {options.get('A', '')}",
            f"B. {options.get('B', '')}",
            f"C. {options.get('C', '')}",
            f"D. {options.get('D', '')}",
        ]
    opt_block = ("\n选项：\n" + "\n".join(opt_lines)) if opt_lines else ""
    qtext = q.get('question') or q.get('prompt') or ''
    lt = str(qtext).lower()
    detected = None
    if ("多选题" in str(qtext)) or ("multiple-choice" in lt) or ("multiple choice" in lt):
        detected = "多选题"
    elif ("单选题" in str(qtext)) or ("single-choice" in lt) or ("single choice" in lt):
        detected = "单选题"
    elif ("判断题" in str(qtext)) or ("true/false" in lt) or ("true or false" in lt) or ("判断" in str(qtext)):
        detected = "判断题"
    elif options:
        detected = "单选题"
    type_line = f"当前题型：{detected}\n" if detected else ""
    instruction = (
        "请直接给出答案，不要解释。\n"
        "若为选择题，仅输出字母；若为多选，输出A,B,C；\n"
        "若为判断题，仅输出‘对’或‘错’；\n"
        "仅输出一行答案。\n"
    )
    prompt = f"{instruction}\n{type_line}题目：{qtext}" + opt_block + "\n你的答案："
    return prompt

def build_prompt_freeform_stricter(q):
    options = q.get('options', {})
    opt_lines = []
    if options:
        opt_lines = [
            f"A. {options.get('A', '')}",
            f"B. {options.get('B', '')}",
            f"C. {options.get('C', '')}",
            f"D. {options.get('D', '')}",
        ]
    opt_block = ("\n选项：\n" + "\n".join(opt_lines)) if opt_lines else ""
    qtext = q.get('question') or q.get('prompt') or ''
    instruction = (
        "请直接给出答案，不要解释。\n"
        "仅输出一行中文短语作为答案。\n"
        "不得输出单个字母A/B/C/D。\n"
    )
    prompt = f"{instruction}\n题目：{qtext}" + opt_block + "\n你的答案："
    return prompt

def extract_text_answer(text, q=None):
    if not text:
        return ""
    s = str(text).strip()
    s = re.sub(r"(?is)<think[\s\S]*?</think>", "", s)
    s = s.strip('`').strip('"')
    s = re.sub(r"^```[\s\S]*?```", lambda m: m.group(0).strip('`'), s)
    def try_json_payload(x):
        try:
            obj = json.loads(x)
            for k in ('answer','final_answer','pred','label','结果','答案'):
                if k in obj and isinstance(obj[k], str):
                    return obj[k].strip()
        except:
            pass
        return None
    j = None
    if '{' in s and '}' in s:
        start = s.find('{')
        end = s.rfind('}')
        j = try_json_payload(s[start:end+1])
        if j:
            s = j
    t = (q.get('prompt') or q.get('question') or '').lower() if isinstance(q, dict) else ''
    allow_letters = False
    if isinstance(q, dict):
        opts = q.get('options') or {}
        if opts:
            allow_letters = True
        if ('单选题' in t) or ('多选题' in t) or ('single-choice' in t) or ('single choice' in t) or ('multiple-choice' in t) or ('multiple choice' in t) or ('单选' in t) or ('多选' in t):
            allow_letters = True
    is_judgement = ('判断题' in t) or ('true/false' in t) or ('true or false' in t) or ('判断' in t)
    if is_judgement:
        if re.search(r"(?is)true|正确|是|对", s):
            return '对'
        if re.search(r"(?is)false|错误|否|错", s):
            return '错'
    if allow_letters and (('多选题' in t) or ('multiple-choice' in t) or ('多选' in t)):
        lines_all = [ln.strip() for ln in s.splitlines() if ln.strip()]
        for ln in reversed(lines_all):
            if any(k in ln for k in ['选项','你的答案','Final Answer','答案']):
                continue
            if re.fullmatch(r"(?is)[A-D,\s]+", ln):
                letters = re.findall(r"[A-D]", ln, flags=re.IGNORECASE)
                if letters:
                    uniq = []
                    for ch in [c.upper() for c in letters]:
                        if ch not in uniq:
                            uniq.append(ch)
                    return ",".join(uniq)
    if allow_letters and (('单选题' in t) or ('single-choice' in t) or ('单选' in t)):
        lines_all = [ln.strip() for ln in s.splitlines() if ln.strip()]
        for ln in reversed(lines_all):
            if any(k in ln for k in ['选项','你的答案','Final Answer','答案']):
                continue
            mm = re.fullmatch(r"\s*([ABCD])\s*", ln, flags=re.IGNORECASE)
            if mm:
                return mm.group(1).upper()
    m = re.search(r"(?is)(?:最终答案|Final\s*Answer|Answer|答案)[^\n\r]*[:：]\s*([\s\S]+)$", s)
    if m:
        tail = m.group(1).strip()
        lines_tail = [ln.strip() for ln in tail.splitlines() if ln.strip()]
        invalid_tokens = ['请直接给出答案', '仅输出一行答案', '不要解释', '当前题型', '最后一行使用', '请在此处填写', '填写答案', '请填写', '用中文填写', '用字母表示', '请直接输出答案', '直接填入答案', '你的答案', 'Final Answer', '答案', '答案：', '题目', '选项']
        for first in lines_tail:
            if any(tok in first for tok in invalid_tokens):
                continue
            if is_judgement:
                if re.search(r"(?is)true|正确|是|对", first):
                    return '对'
                if re.search(r"(?is)false|错误|否|错", first):
                    return '错'
                mmj = re.fullmatch(r"\s*([ABCD])\s*", first, flags=re.IGNORECASE)
                if mmj and isinstance(q, dict):
                    chj = mmj.group(1).upper()
                    o = q.get('options') or {}
                    a = str(o.get('A','')).lower()
                    b = str(o.get('B','')).lower()
                    def _is_true(x):
                        return bool(re.search(r"(?is)true|正确|是|对", x))
                    def _is_false(x):
                        return bool(re.search(r"(?is)false|错误|否|错", x))
                    if _is_true(a) and _is_false(b):
                        if chj == 'A':
                            return '对'
                        if chj == 'B':
                            return '错'
                    if _is_true(b) and _is_false(a):
                        if chj == 'B':
                            return '对'
                        if chj == 'A':
                            return '错'
            if allow_letters and (('多选题' in t) or ('multiple-choice' in t) or ('多选' in t)):
                letters = re.findall(r"[A-D]", first, flags=re.IGNORECASE)
                if letters:
                    uniq = []
                    for ch in [c.upper() for c in letters]:
                        if ch not in uniq:
                            uniq.append(ch)
                    return ",".join(uniq)
            if allow_letters and (('单选题' in t) or ('single-choice' in t) or ('单选' in t)):
                mm = re.search(r"\b([ABCD])\b", first, flags=re.IGNORECASE)
                if mm:
                    return mm.group(1).upper()
            if first in ('对','错'):
                return first
            if (not is_judgement) and allow_letters and first in ('A','B','C','D'):
                return first
            if (not is_judgement) and allow_letters:
                mm2 = re.search(r"\b([ABCD])\b", first, flags=re.IGNORECASE)
                if mm2:
                    return mm2.group(1).upper()
            if re.search(r"(?is)true|正确|是|对", first):
                return '对'
            if re.search(r"(?is)false|错误|否|错", first):
                return '错'
            return first[:64]
        if (not is_judgement) and allow_letters:
            mm_all = re.search(r"\b([ABCD])\b", tail, flags=re.IGNORECASE)
            if mm_all:
                return mm_all.group(1).upper()
        if re.search(r"(?is)true|正确|是|对", tail):
            return '对'
        if re.search(r"(?is)false|错误|否|错", tail):
            return '错'
        return ''
    s2 = s.strip()
    if s2 in ('对','错'):
        return s2
    if (not is_judgement) and allow_letters and s2 in ('A','B','C','D'):
        return s2
    lines = [ln.strip() for ln in s2.splitlines() if ln.strip()]
    for ln in lines:
        if any(k in ln for k in ['请直接给出答案', '仅输出一行答案', '不要解释', '当前题型', '最后一行使用']):
            continue
        if re.fullmatch(r"[\s\-_=（()）【】<>《》~·.,;:，。；：!?！？]+", ln):
            continue
        if re.search(r"(?is)请填写|填写答案|请在此处填写|用中文填写|用字母表示|请直接输出答案|直接填入答案|答案：|^答案$", ln):
            continue
        if ln in ('对','错'):
            return ln
        if (not is_judgement) and allow_letters and ln in ('A','B','C','D'):
            return ln
        if (not is_judgement) and allow_letters:
            mm = re.search(r"\b([ABCD])\b", ln, flags=re.IGNORECASE)
            if mm:
                return mm.group(1).upper()
        if re.search(r"(?is)true|正确|是|对", ln):
            return '对'
        if re.search(r"(?is)false|错误|否|错", ln):
            return '错'
        if not any(k in ln for k in ['你的答案', '题目', '选项', 'Final Answer', '答案']):
            return ln[:64]
    if (not lines) or all(
        (any(k in ln for k in ['请直接给出答案', '仅输出一行答案', '不要解释', '当前题型', '最后一行使用']) or
         re.fullmatch(r"[\s\-_=（()）【】<>《》~·.,;:，。；：!?！？]+", ln) or
         re.search(r"(?is)请填写|填写答案|请在此处填写", ln))
        for ln in lines
    ):
        return ''
    return (lines[0][:64])


def call_ollama_generate(base_url, model, prompt, temperature=0.7, retry=3, timeout=60):
    url = base_url.rstrip('/') + '/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': float(temperature)
        }
    }
    data = json.dumps(payload).encode('utf-8')

    last_err = None
    for attempt in range(1, retry + 1):
        try:
            req = request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode('utf-8', errors='replace')
                obj = json.loads(text)
                return obj.get('response', '')
        except error.HTTPError as e:
            last_err = f"HTTPError {e.code}: {e.read().decode('utf-8', errors='replace')}"
        except error.URLError as e:
            last_err = f"URLError: {e.reason}"
        except Exception as e:
            last_err = f"Error: {e}"
        # backoff
        sleep_s = min(2 ** (attempt - 1), 8)
        time.sleep(sleep_s)
    raise RuntimeError(f"调用Ollama失败: {last_err}")


def call_vllm_generate(base_url, model, prompt, temperature=0.7, api_key=None, retry=3, timeout=60, max_tokens=8192, stop=None):
    """调用vLLM的OpenAI兼容API"""
    url = base_url.rstrip('/') + '/v1/completions'
    payload = {
        'model': model,
        'prompt': prompt,
        'temperature': float(temperature),
        'max_tokens': int(max_tokens),
    }
    if stop is not None:
        payload['stop'] = stop
    data = json.dumps(payload).encode('utf-8')
    
    # 构建请求头
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    last_err = None
    for attempt in range(1, retry + 1):
        try:
            req = request.Request(url, data=data, headers=headers)
            with request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode('utf-8', errors='replace')
                obj = json.loads(text)
                choices = obj.get('choices', [])
                if choices:
                    return choices[0].get('text', '')
                return ''
        except error.HTTPError as e:
            last_err = f"HTTPError {e.code}: {e.read().decode('utf-8', errors='replace')}"
        except error.URLError as e:
            last_err = f"URLError: {e.reason}"
        except Exception as e:
            last_err = f"Error: {e}"
        # backoff
        sleep_s = min(2 ** (attempt - 1), 8)
        time.sleep(sleep_s)
    raise RuntimeError(f"调用vLLM失败: {last_err}")


def call_vllm_generate_chat(base_url, model, prompt, temperature=0.7, api_key=None, retry=3, timeout=60, max_tokens=8192, stop=None):
    url = base_url.rstrip('/') + '/v1/chat/completions'
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': float(temperature),
        'max_tokens': int(max_tokens),
    }
    if stop is not None:
        payload['stop'] = stop
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    last_err = None
    for attempt in range(1, retry + 1):
        try:
            req = request.Request(url, data=data, headers=headers)
            with request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode('utf-8', errors='replace')
                obj = json.loads(text)
                choices = obj.get('choices', [])
                if choices:
                    message = choices[0].get('message', {})
                    return message.get('content', '')
                return ''
        except error.HTTPError as e:
            last_err = f"HTTPError {e.code}: {e.read().decode('utf-8', errors='replace')}"
        except error.URLError as e:
            last_err = f"URLError: {e.reason}"
        except Exception as e:
            last_err = f"Error: {e}"
        sleep_s = min(2 ** (attempt - 1), 8)
        time.sleep(sleep_s)
    raise RuntimeError(f"调用vLLM Chat失败: {last_err}")

 


def extract_choice(text):
    if not text:
        return None
    text = re.sub(r"(?is)<think[\s\S]*?</think>", "", str(text))
    m = re.search(r"(?:最终答案|Final\s+Answer|答案)[^\n\r]*[:：]\s*([ABCD])\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    lines = text.splitlines()
    for line in reversed(lines):
        mm = re.match(r"\s*([ABCD])\s*$", line, flags=re.IGNORECASE)
        if mm:
            return mm.group(1).upper()
    s = text.strip()
    if re.fullmatch(r"[ABCD]", s, flags=re.IGNORECASE):
        return s.upper()
    return None

def extract_think(text):
    if not text:
        return ''
    s = str(text)
    m = re.search(r"(?is)<think[\s\S]*?</think>", s)
    if not m:
        m = re.search(r"(?is)<analysis[\s\S]*?</analysis>", s)
    if m:
        t = m.group(0)
        t = re.sub(r"(?is)</?think>", "", t)
        t = re.sub(r"(?is)</?analysis>", "", t)
        return t.strip()
    idx = re.search(r"(?is)(最终答案|Final\s+Answer|答案)[^\n\r]*[:：]", s)
    if idx:
        return s[:idx.start()].strip()
    return ''


# 全局变量用于动画效果
_spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
_spinner_index = 0
_progress_call_count = 0

# 线程安全的进度管理器
class ThreadSafeProgress:
    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.correct = 0
        self.lock = threading.Lock()
        self.results = []
        
    def update(self, is_correct, result_data):
        with self.lock:
            self.completed += 1
            if is_correct:
                self.correct += 1
            self.results.append(result_data)
            rt = result_data.get('think') or ''
            if rt:
                print(f"\n🧠 推理：{rt.strip()}")
            if result_data.get('show_full'):
                full = result_data.get('model_response') or ''
                if full:
                    print(f"\n📜 完整回答：\n{full.strip()}")
            # 实时显示进度
            print(f"\n[{self.completed}/{self.total}] 📝 题目ID: {result_data.get('id')}  🎯 标准答案: {result_data.get('answer')}  🤖 模型答案: {result_data.get('model_choice') or 'N/A'}  {'✅ 正确' if is_correct else '❌ 错误'}")
            print_progress(self.completed, self.total, self.correct)
            
    def get_stats(self):
        with self.lock:
            return self.completed, self.correct, self.results.copy()


def process_single_question(question_data, args, progress_manager):
    """处理单个题目的函数，用于多线程调用"""
    idx, q = question_data
    prompt = build_prompt(q)
    if args.show_think:
        opts = q.get('options', {})
        prompt = (
            "请先在<think></think>标签中详细写出你的推理过程，不要省略或隐藏。\n"
            "最后严格只输出一行：\nFinal Answer: <A/B/C/D>\n"
            f"题目：{q.get('question','')}\n选项：\nA. {opts.get('A','')}\nB. {opts.get('B','')}\nC. {opts.get('C','')}\nD. {opts.get('D','')}\n你的答案："
        )
    model_resp = ''
    model_choice = None
    think_text = ''
    
    max_retries = 3
    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
            if args.api_type == 'vllm':
                mt = args.think_max_tokens if args.show_think else 8192
                model_resp = call_vllm_generate_chat(args.base_url, args.model, prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=mt, stop=None)
                if not model_resp:
                    model_resp = call_vllm_generate(args.base_url, args.model, prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=mt, stop=None)
            else:
                model_resp = call_ollama_generate(args.base_url, args.model, prompt, temperature=args.temperature)
            model_choice = extract_choice(model_resp)
            think_text = extract_think(model_resp)
            if model_choice:
                break
            if args.show_think:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay + random.uniform(0, 1))
                    retry_delay *= 1.5
                continue
            strict_prompt = (
                "仅输出以下格式的唯一一行：\n"
                "Final Answer: <A/B/C/D>\n"
                f"题目：{q.get('question','')}\n选项：\nA. {q.get('options',{}).get('A','')}\nB. {q.get('options',{}).get('B','')}\nC. {q.get('options',{}).get('C','')}\nD. {q.get('options',{}).get('D','')}\n你的答案："
            )
            if args.api_type == 'vllm':
                model_resp = call_vllm_generate_chat(args.base_url, args.model, strict_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=8192, stop=['\n','\r\n'])
                if not model_resp:
                    model_resp = call_vllm_generate(args.base_url, args.model, strict_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=8192, stop=['\n','\r\n'])
            else:
                model_resp = call_ollama_generate(args.base_url, args.model, strict_prompt, temperature=args.temperature)
            model_choice = extract_choice(model_resp)
            think_text = extract_think(model_resp)
            if model_choice:
                break
            if attempt < max_retries - 1:
                time.sleep(retry_delay + random.uniform(0, 1))
                retry_delay *= 1.5
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay + random.uniform(0, 1))
                retry_delay *= 1.5
            else:
                model_resp = f"<❌ 调用失败 (重试{max_retries}次): {e}>"
                model_choice = None
    
    answer = q.get('answer', '').strip().upper() if isinstance(q.get('answer'), str) else ''
    is_correct = (model_choice == answer)
    
    # 构建结果数据
    opt_texts = q.get('options', {})
    model_choice_text = opt_texts.get(model_choice, '') if model_choice else ''
    answer_text = opt_texts.get(answer, '')
    
    result_data = {
        'id': q.get('id'),
        'question': q.get('question'),
        'options': opt_texts,
        'answer': answer,
        'answer_text': answer_text,
        'model_response': model_resp,
        'think': ((think_text if think_text else model_resp) if args.show_think else ''),
        'model_choice': model_choice,
        'model_choice_text': model_choice_text,
        'is_correct': is_correct,
        'show_full': args.show_full,
    }
    
    # 更新进度
    progress_manager.update(is_correct, result_data)
    
    return result_data

def process_single_question_freeform(question_data, args):
    idx, q = question_data
    blank_ids = {"1751","1761","1762","1763","1764","1766","1767","1769","1770","2852","3127","3129"}
    if str(q.get('id')) in blank_ids:
        return {'question_id': str(q.get('id')), 'answer': '', 'raw': ''}
    prompt = build_prompt_freeform(q)
    if args.show_think:
        qtext = q.get('question') or q.get('prompt') or ''
        options = q.get('options') or {}
        opt_block = ("\n选项：\nA. " + str(options.get('A','')) + "\nB. " + str(options.get('B','')) + "\nC. " + str(options.get('C','')) + "\nD. " + str(options.get('D',''))) if options else ''
        prompt = (
            "请先在<think></think>标签中完整写出你的推理过程。\n"
            "最后严格只输出一行：\nFinal Answer: <答案>\n"
            f"题目：{qtext}" + opt_block + "\n你的答案："
        )
    model_resp = ''
    raw_used = ''
    max_retries = 3
    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
            if args.api_type == 'vllm':
                mt = args.think_max_tokens if args.show_think else 8192
                stops = None if ('instruct' in str(args.model).lower()) else ["你的答案："]
                model_resp = call_vllm_generate(args.base_url, args.model, prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=mt, stop=stops)
                if not model_resp:
                    model_resp = call_vllm_generate_chat(args.base_url, args.model, prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=mt, stop=stops)
            else:
                model_resp = call_ollama_generate(args.base_url, args.model, prompt, temperature=args.temperature)
            raw_used = model_resp
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay + random.uniform(0, 1))
                retry_delay *= 1.5
            else:
                model_resp = ''
    think_text = extract_think(model_resp)
    if args.show_think:
        print(f"\n🧠 推理：{(think_text if think_text else model_resp).strip()}")
    if args.show_full:
        if raw_used:
            print(f"\n📜 完整回答：\n{raw_used.strip()}")
        elif model_resp:
            print(f"\n📜 完整回答：\n{model_resp.strip()}")
    answer_text = extract_text_answer(model_resp, q)
    if not answer_text:
        strict_prompt = build_prompt_freeform_strict(q)
        try:
            if args.api_type == 'vllm':
                stops2 = ["\n","\r\n"] if ('instruct' in str(args.model).lower()) else ["你的答案："]
                model_resp2 = call_vllm_generate(args.base_url, args.model, strict_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=128, stop=stops2)
                if not model_resp2:
                    model_resp2 = call_vllm_generate_chat(args.base_url, args.model, strict_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=128, stop=stops2)
            else:
                model_resp2 = call_ollama_generate(args.base_url, args.model, strict_prompt, temperature=args.temperature)
        except Exception:
            model_resp2 = ''
        answer_text = extract_text_answer(model_resp2, q)
        if args.show_full and model_resp2:
            print(f"\n📜 完整回答：\n{model_resp2.strip()}")
        if answer_text:
            raw_used = model_resp2
    t_multi = str((q.get('prompt') or q.get('question') or '')).lower()
    is_multi = ('多选' in t_multi) or ('multiple-choice' in t_multi) or ('multiple choice' in t_multi)
    if is_multi and answer_text in ('A','B','C','D'):
        strict_prompt_multi = build_prompt_freeform_strict(q)
        try:
            if args.api_type == 'vllm':
                stopsm = ["\n","\r\n"] if ('instruct' in str(args.model).lower()) else ["你的答案："]
                model_resp_m = call_vllm_generate(args.base_url, args.model, strict_prompt_multi, temperature=args.temperature, api_key=args.api_key, max_tokens=128, stop=stopsm)
                if not model_resp_m:
                    model_resp_m = call_vllm_generate_chat(args.base_url, args.model, strict_prompt_multi, temperature=args.temperature, api_key=args.api_key, max_tokens=128, stop=stopsm)
            else:
                model_resp_m = call_ollama_generate(args.base_url, args.model, strict_prompt_multi, temperature=args.temperature)
        except Exception:
            model_resp_m = ''
        parsed_m = extract_text_answer(model_resp_m, q)
        if parsed_m:
            answer_text = parsed_m
            raw_used = model_resp_m
    if answer_text in ('A','B','C','D'):
        t = (q.get('prompt') or q.get('question') or '').lower()
        opts = q.get('options') or {}
        if not (opts or ('单选' in t) or ('多选' in t) or ('single-choice' in t) or ('multiple-choice' in t)):
            stricter_prompt = build_prompt_freeform_stricter(q)
            try:
                if args.api_type == 'vllm':
                    model_resp3 = call_vllm_generate(args.base_url, args.model, stricter_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=64, stop=["\n","\r\n"])
                    if not model_resp3:
                        model_resp3 = call_vllm_generate_chat(args.base_url, args.model, stricter_prompt, temperature=args.temperature, api_key=args.api_key, max_tokens=64, stop=["\n","\r\n"])
                else:
                    model_resp3 = call_ollama_generate(args.base_url, args.model, stricter_prompt, temperature=args.temperature)
            except Exception:
                model_resp3 = ''
            answer_text = extract_text_answer(model_resp3, q)
            if args.show_full and model_resp3:
                print(f"\n📜 完整回答：\n{model_resp3.strip()}")
            if answer_text:
                raw_used = model_resp3
    return {'question_id': str(q.get('id')), 'answer': answer_text, 'raw': (raw_used or model_resp)}

def print_progress(done, total, correct):
    global _spinner_index, _progress_call_count
    _progress_call_count += 1
    
    # ANSI颜色代码 - 扩展彩虹色谱
    class Colors:
        RESET = '\033[0m'
        BOLD = '\033[1m'
        DIM = '\033[2m'
        ITALIC = '\033[3m'
        UNDERLINE = '\033[4m'
        
        # 基础颜色
        BLACK = '\033[30m'
        RED = '\033[31m'
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        BLUE = '\033[34m'
        MAGENTA = '\033[35m'
        CYAN = '\033[36m'
        WHITE = '\033[37m'
        
        # 亮色系列
        BRIGHT_BLACK = '\033[90m'
        BRIGHT_RED = '\033[91m'
        BRIGHT_GREEN = '\033[92m'
        BRIGHT_YELLOW = '\033[93m'
        BRIGHT_BLUE = '\033[94m'
        BRIGHT_MAGENTA = '\033[95m'
        BRIGHT_CYAN = '\033[96m'
        BRIGHT_WHITE = '\033[97m'
        
        # 256色模式 - 彩虹色谱
        ORANGE = '\033[38;5;208m'        # 橙色
        DARK_ORANGE = '\033[38;5;202m'   # 深橙色
        PINK = '\033[38;5;205m'          # 粉色
        PURPLE = '\033[38;5;129m'        # 紫色
        DARK_PURPLE = '\033[38;5;93m'    # 深紫色
        ROYAL_BLUE = '\033[38;5;54m'     # 皇家蓝
        LIME = '\033[38;5;154m'          # 青柠色
        SEA_GREEN = '\033[38;5;48m'      # 海绿色
        TURQUOISE = '\033[38;5;51m'      # 青绿色
        SKY_BLUE = '\033[38;5;117m'      # 天蓝色
        VIOLET = '\033[38;5;177m'        # 紫罗兰色
        GOLD = '\033[38;5;220m'          # 金色
        CORAL = '\033[38;5;203m'         # 珊瑚色
        NEON_GREEN = '\033[38;5;46m'     # 霓虹绿
        NEON_PINK = '\033[38;5;198m'     # 霓虹粉
        
        # RGB颜色（真彩色）
        NEON_GREEN = '\033[38;2;57;255;20m'
        NEON_BLUE = '\033[38;2;77;77;255m'
        NEON_PINK = '\033[38;2;255;20;147m'
        ELECTRIC_PURPLE = '\033[38;2;191;0;255m'
        CYBER_CYAN = '\033[38;2;0;255;255m'
    
    bar_len = 50
    ratio = 0 if total == 0 else done / total
    filled = int(ratio * bar_len)
    percent = ratio * 100
    accuracy = (correct / done * 100) if done > 0 else 0
    
    # 动态旋转指示器
    spinner = _spinner_chars[_spinner_index % len(_spinner_chars)]
    _spinner_index += 1
    
    # 根据准确率选择颜色主题和表情
    if accuracy >= 95:
        emoji = "🏆"
        bar_color = Colors.NEON_GREEN
        text_color = Colors.BRIGHT_GREEN
        accent_color = Colors.GOLD
    elif accuracy >= 90:
        emoji = "💎"
        bar_color = Colors.BRIGHT_GREEN
        text_color = Colors.GREEN
        accent_color = Colors.LIME
    elif accuracy >= 85:
        emoji = "🌟"
        bar_color = Colors.LIME
        text_color = Colors.GREEN
        accent_color = Colors.SEA_GREEN
    elif accuracy >= 80:
        emoji = "✨"
        bar_color = Colors.CYAN
        text_color = Colors.BRIGHT_CYAN
        accent_color = Colors.TURQUOISE
    elif accuracy >= 75:
        emoji = "📊"
        bar_color = Colors.CYAN
        text_color = Colors.BRIGHT_CYAN
        accent_color = Colors.SKY_BLUE
    elif accuracy >= 70:
        emoji = "🔵"
        bar_color = Colors.BRIGHT_BLUE
        text_color = Colors.ROYAL_BLUE
        accent_color = Colors.BLUE
    elif accuracy >= 65:
        emoji = "💜"
        bar_color = Colors.PURPLE
        text_color = Colors.PURPLE
        accent_color = Colors.VIOLET
    elif accuracy >= 60:
        emoji = "⚡"
        bar_color = Colors.BRIGHT_YELLOW
        text_color = Colors.GOLD
        accent_color = Colors.YELLOW
    elif accuracy >= 55:
        emoji = "🟡"
        bar_color = Colors.YELLOW
        text_color = Colors.ORANGE
        accent_color = Colors.GOLD
    elif accuracy >= 50:
        emoji = "🟠"
        bar_color = Colors.ORANGE
        text_color = Colors.ORANGE
        accent_color = Colors.DARK_ORANGE
    elif accuracy >= 40:
        emoji = "🔍"
        bar_color = Colors.ORANGE
        text_color = Colors.DARK_ORANGE
        accent_color = Colors.RED
    elif accuracy >= 30:
        emoji = "🔥"
        bar_color = Colors.NEON_PINK
        text_color = Colors.PINK
        accent_color = Colors.BRIGHT_MAGENTA
    else:
        emoji = "💥"
        bar_color = Colors.BRIGHT_RED
        text_color = Colors.RED
        accent_color = Colors.NEON_PINK
    
    # 柔和蓝色系渐变色谱数组 - 从浅蓝到深蓝的温和渐变（30种颜色）
    rainbow_colors = [
        '\033[38;5;195m',      # 1. 极浅蓝
        '\033[38;5;189m',      # 2. 浅蓝白
        '\033[38;5;183m',      # 3. 淡蓝
        '\033[38;5;177m',      # 4. 浅蓝紫
        '\033[38;5;171m',      # 5. 蓝紫
        '\033[38;5;165m',      # 6. 淡紫蓝
        '\033[38;5;159m',      # 7. 浅青蓝
        '\033[38;5;153m',      # 8. 青蓝
        '\033[38;5;147m',      # 9. 灰蓝
        '\033[38;5;141m',      # 10. 中蓝紫
        '\033[38;5;135m',      # 11. 蓝紫
        '\033[38;5;129m',      # 12. 深蓝紫
        '\033[38;5;123m',      # 13. 青蓝
        '\033[38;5;117m',      # 14. 天蓝
        '\033[38;5;111m',      # 15. 浅蓝
        '\033[38;5;105m',      # 16. 中蓝
        '\033[38;5;99m',       # 17. 蓝灰
        '\033[38;5;93m',       # 18. 深蓝紫
        '\033[38;5;87m',       # 19. 青蓝
        '\033[38;5;81m',       # 20. 亮青蓝
        '\033[38;5;75m',       # 21. 蓝
        '\033[38;5;69m',       # 22. 中蓝
        '\033[38;5;63m',       # 23. 深蓝
        '\033[38;5;57m',       # 24. 皇家蓝
        '\033[38;5;51m',       # 25. 青色
        '\033[38;5;45m',       # 26. 亮青
        '\033[38;5;39m',       # 27. 蓝青
        '\033[38;5;33m',       # 28. 深青蓝
        '\033[38;5;27m',       # 29. 深蓝
        '\033[38;5;21m'        # 30. 最深蓝
    ]
    
    # 炫酷Unicode字符进度条
    filled_chars = ['█', '▓', '▒', '░']
    empty_char = '░'
    
    # 创建彩虹渐变效果的进度条
    bar_parts = []
    for i in range(bar_len):
        if i < filled:
            # 根据进度条位置计算彩虹颜色索引
            color_ratio = i / max(bar_len - 1, 1)  # 避免除零
            color_index = int(color_ratio * (len(rainbow_colors) - 1))
            color_index = min(color_index, len(rainbow_colors) - 1)
            
            # 根据位置选择不同的填充字符创建深度效果
            if i < filled * 0.6:
                char = filled_chars[0]  # █ 最实心
            elif i < filled * 0.8:
                char = filled_chars[1]  # ▓ 较实心
            elif i < filled * 0.95:
                char = filled_chars[2]  # ▒ 较空心
            else:
                char = filled_chars[3]  # ░ 最空心
            
            # 应用彩虹颜色
            rainbow_color = rainbow_colors[color_index]
            bar_parts.append(f"{rainbow_color}{char}{Colors.RESET}")
        else:
            bar_parts.append(f"{Colors.DIM}{empty_char}{Colors.RESET}")
    
    bar = ''.join(bar_parts)
    
    # 闪烁效果（每6次调用闪烁一次，更柔和）
    blink = Colors.BOLD if _progress_call_count % 12 < 6 else ''
    
    # 构建炫酷的进度显示
    progress_text = (
        f"\r{blink}{text_color}{spinner}{Colors.RESET} "
        f"{emoji} {Colors.BOLD}进度{Colors.RESET} "
        f"[{bar}] "
        f"{blink}{text_color}{percent:5.1f}%{Colors.RESET} "
        f"{Colors.DIM}|{Colors.RESET} "
        f"{accent_color}{done}{Colors.RESET}/{Colors.BOLD}{total}{Colors.RESET}"
    )
    
    sys.stdout.write(progress_text)
    sys.stdout.flush()


def generate_html_report(results, output_path, model, total_ms, only_errors=False, hide_question=False, summary_only=False):
    # Filter results if only_errors is True
    if only_errors:
        filtered_results = [r for r in results if r['is_correct'] is False]
        display_results = filtered_results
        report_title = "错误结果报告"
        report_subtitle = f"仅显示错误答题 · 错误数：{len(filtered_results)} / 总题数：{len(results)}"
    else:
        display_results = results
        report_title = "大模型测评报告"
        report_subtitle = f"题目数：{len(results)}"
    
    total = len(results)
    correct = sum(1 for r in results if r['is_correct'] is True)
    accuracy = (correct / total * 100) if total else 0.0

    # Simple inline CSS
    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Liberation Sans', sans-serif; margin: 16px; color: #1f2937; }
    h1 { margin: 0 0 4px 0; font-size: 20px; }
    .sub { color: #6b7280; margin-top: 2px; font-size: 13px; }
    .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; margin-top: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
    .stat { background: #f9fafb; border: 1px solid #eef2f7; border-radius: 10px; padding: 12px; }
    .label { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
    .value { font-size: 18px; font-weight: 700; margin-top: 4px; }
    .progress { height: 10px; background: #f3f4f6; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; }
    .progress > div { height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); width: 0%; }
    table { width: 100%; border-collapse: collapse; margin-top: 6px; }
    th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
    th { background: #f8fafc; color: #334155; }
    tr:hover { background: #f9fafb; }
    .ok { color: #16a34a; font-weight: 600; }
    .bad { color: #dc2626; font-weight: 600; }
    .muted { color: #64748b; font-size: 11px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #e5e7eb; background: #f8fafc; }
    """

    # Build rows
    rows_html = []
    for r in display_results:
        chosen_letter = r.get('model_choice') or '-'
        correct_letter = r.get('answer', '-')
        chosen_text = html.escape(r.get('model_choice_text') or '')
        correct_text = html.escape(r.get('answer_text') or '')
        status = '<span class="ok">正确</span>' if r['is_correct'] else '<span class="bad">错误</span>'
        if hide_question:
            rows_html.append(
                f"<tr>"
                f"<td><span class='badge'>#{html.escape(str(r['id']))}</span></td>"
                f"<td><b>{html.escape(chosen_letter)}</b><div class='muted'>{chosen_text}</div></td>"
                f"<td><b>{html.escape(correct_letter)}</b><div class='muted'>{correct_text}</div></td>"
                f"<td>{status}</td>"
                f"</tr>"
            )
        else:
            q = html.escape(r['question'])
            rows_html.append(
                f"<tr>"
                f"<td><span class='badge'>#{html.escape(str(r['id']))}</span></td>"
                f"<td>{q}</td>"
                f"<td><b>{html.escape(chosen_letter)}</b><div class='muted'>{chosen_text}</div></td>"
                f"<td><b>{html.escape(correct_letter)}</b><div class='muted'>{correct_text}</div></td>"
                f"<td>{status}</td>"
                f"</tr>"
            )

    html_doc = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>大模型测评报告 - {html.escape(model)}</title>
  <style>{css}</style>
</head>
<body>
  <h1>{report_title}</h1>
  <div class="sub">模型：<b>{html.escape(model)}</b> · {report_subtitle} · 用时：{total_ms/1000:.1f}s</div>

  <div class="card">
    <div class="stats">
      <div class="stat">
        <div class="label">正确率</div>
        <div class="value">{accuracy:.2f}%</div>
        <div class="progress" aria-label="accuracy progress"><div style="width:{accuracy:.2f}%"></div></div>
      </div>
      <div class="stat">
        <div class="label">答对 / 总数</div>
        <div class="value">{correct} / {total}</div>
      </div>
      <div class="stat">
        <div class="label">错误</div>
        <div class="value">{total - correct}</div>
      </div>
    </div>
  </div>

  {'' if summary_only else (
    '<div class="card">'
    '<h3 style="margin-top:0;">详细结果</h3>'
    '<div style="max-height: 70vh; overflow: auto; border: 1px solid #e5e7eb; border-radius: 8px;">'
    '<table>'
    '<thead>'
    '<tr>'
    '<th style="width:70px;">ID</th>'
    f"{'' if hide_question else '<th>题目</th>'}"
    '<th style="width:25%;">模型答案</th>'
    '<th style="width:25%;">标准答案</th>'
    '<th style="width:90px;">判定</th>'
    '</tr>'
    '</thead>'
    '<tbody>'
    f"{''.join(rows_html)}"
    '</tbody>'
    '</table>'
    '</div>'
    '</div>'
  )}

  <p class="muted">本报告由自动脚本生成。</p>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)

def generate_combined_summary(reports, output_path, model, total_ms):
    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; margin: 16px; color: #1f2937; }
    h1 { margin: 0 0 4px 0; font-size: 20px; }
    .sub { color: #6b7280; margin-top: 2px; font-size: 13px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
    .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
    .title { font-weight: 600; color: #334155; margin-bottom: 6px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .label { color: #6b7280; font-size: 12px; }
    .value { font-size: 18px; font-weight: 700; }
    .progress { height: 10px; background: #f3f4f6; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; margin-top: 6px; }
    .progress > div { height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); }
    """
    cards = []
    for r in reports:
        acc = (r['correct']/r['total']*100) if r['total'] else 0
        cards.append(
            f"<div class='card'>"
            f"<div class='title'>{r['name']}</div>"
            f"<div class='row'><div><div class='label'>正确率</div><div class='value'>{acc:.2f}%</div><div class='progress'><div style='width:{acc:.2f}%'></div></div></div>"
            f"<div><div class='label'>答对 / 总数</div><div class='value'>{r['correct']} / {r['total']}</div></div></div>"
            f"</div>"
        )
    html_doc = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>综合评估概览 - {html.escape(model)}</title>
  <style>{css}</style>
</head>
<body>
  <h1>综合评估概览</h1>
  <div class="sub">模型：<b>{html.escape(model)}</b> · 用时：{total_ms/1000:.1f}s</div>
  <div class="grid">{''.join(cards)}</div>
  <p class="sub">本概览报告包含多个题库的统计摘要。</p>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)


def main():
    parser = argparse.ArgumentParser(description='使用 Ollama 或 vLLM API 对 data 目录题库进行测评，生成概览报告与答案JSON。')
    parser.add_argument('--model', default='llama3', help='模型名称，如: llama3, qwen2, mistral 等')
    parser.add_argument('--api-type', choices=['ollama', 'vllm'], default='ollama', help='API类型：ollama 或 vllm（默认：ollama）')
    parser.add_argument('--base-url', default='http://localhost:11434', help='API服务地址，Ollama默认为 http://localhost:11434，vLLM默认为 http://localhost:8000')
    parser.add_argument('--api-key', help='API密钥（用于 vLLM，按需）')
    parser.add_argument('--threads', type=int, default=4, help='并发线程数量，默认 4')
    parser.add_argument('--temperature', type=float, default=0.7, help='采样温度，默认 0.7')
    parser.add_argument('--start', type=int, default=0, help='起始题目索引（从0开始）')
    parser.add_argument('--limit', type=int, default=0, help='限制题目数量（0表示不限制）')
    parser.add_argument('--summary-only', action='store_true', help='HTML报告仅显示统计概览，不展示逐题详细结果')
    parser.add_argument('--dataset', choices=['all', 'strike', 'cissp', 'cs_eval'], default='all', help='选择评测数据集：all/strike/cissp/cs_eval')
    parser.add_argument('--show-think', action='store_true', help='终端输出模型思考过程（<think>内容）')
    parser.add_argument('--show-full', action='store_true', help='终端输出模型完整回答（原始文本，不裁剪）')
    parser.add_argument('--think-max-tokens', type=int, default=8192, help='显示推理时的最大生成长度（仅在 --show-think 启用时使用，默认 8192）')
    parser.add_argument('--shuffle', action='store_true', help='随机抽取 limit 道题进行评测/生成')
    parser.add_argument('--wrong-out', help='将评测中的错题输出到指定JSON文件（追加写入）')
    parser.add_argument('--mcq-file', help='指定一个含答案的MCQ题库JSON文件进行评测')
    args = parser.parse_args()
    
    # 根据API类型调整默认base_url
    if args.api_type == 'vllm' and args.base_url == 'http://localhost:11434':
        args.base_url = 'http://localhost:8000'
    

    def run_mcq(file_path, report_prefix):
        try:
            questions, invalids = analyze_questions_file(file_path)
        except Exception as e:
            print(f"❌ 加载题库失败: {e}")
            return {'name': report_prefix, 'total': 0, 'correct': 0}
        total_all = len(questions)
        if invalids:
            try:
                invalid_name = f"invalid_{report_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(os.path.join(os.path.dirname(__file__), invalid_name), 'w', encoding='utf-8') as f:
                    json.dump(invalids, f, ensure_ascii=False, indent=2)
                print(f"⚠️  已过滤 {len(invalids)} 条无效题目，详情见 {invalid_name}")
            except Exception as e:
                print(f"⚠️  无效题目明细保存失败: {e}")
        start = max(args.start, 0)
        if args.limit and args.limit > 0:
            if args.shuffle:
                k = min(args.limit, len(questions))
                questions = random.sample(questions, k)
            else:
                questions = questions[start: start + args.limit]
        else:
            questions = questions[start:]
        total = len(questions)
        if total == 0:
            print("⚠️  没有可评估的题目。")
            return {'name': report_prefix, 'total': 0, 'correct': 0}
        print(f"🚀 开始评估 {report_prefix}，共 {total} / {total_all} 题。API类型：{args.api_type}  模型：{args.model}  服务：{args.base_url}  线程数：{args.threads}")
        progress_manager = ThreadSafeProgress(total)
        start_ms = time.time() * 1000
        try:
            question_data = [(idx, q) for idx, q in enumerate(questions, start=1)]
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                future_to_question = {executor.submit(process_single_question, qd, args, progress_manager): qd for qd in question_data}
                for future in as_completed(future_to_question):
                    try:
                        _ = future.result()
                    except Exception as e:
                        print(f"\n❌ 处理题目时发生错误: {e}")
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断评估！正在生成部分结果报告...")
        end_ms = time.time() * 1000
        completed_count, correct, results = progress_manager.get_stats()
        wrong_items = []
        try:
            for item in results:
                if not item.get('is_correct'):
                    wrong_items.append({
                        'dataset': report_prefix,
                        'id': item.get('id'),
                        'question': item.get('question'),
                        'options': item.get('options'),
                        'answer': item.get('answer'),
                        'model_answer': item.get('model_choice'),
                        'model_answer_text': item.get('model_choice_text'),
                    })
        except Exception:
            pass
        try:
            out_name = f"report_{report_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            output_path = os.path.join(os.path.dirname(__file__), out_name)
            generate_html_report(results, output_path, args.model, total_ms=end_ms - start_ms, only_errors=False, hide_question=True, summary_only=True)
            print(f"📋 概览报告已生成: {out_name}")
        except Exception as e:
            print(f"❌ 生成 HTML 报告失败: {e}")
        if args.wrong_out and wrong_items:
            try:
                out_path = args.wrong_out
                if not os.path.isabs(out_path):
                    out_path = os.path.join(os.path.dirname(__file__), out_path)
                existing = []
                if os.path.exists(out_path):
                    with open(out_path, 'r', encoding='utf-8') as f:
                        try:
                            existing = json.load(f)
                            if not isinstance(existing, list):
                                existing = []
                        except Exception:
                            existing = []
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(existing + wrong_items, f, ensure_ascii=False, indent=2)
                print(f"📝 错题已追加保存到: {os.path.basename(out_path)}  新增: {len(wrong_items)} 条")
            except Exception as e:
                print(f"⚠️  错题输出失败: {e}")
        return {'name': report_prefix, 'total': completed_count, 'correct': correct}

    def run_freeform(file_path, answers_prefix):
        try:
            questions = load_questions_freeform(file_path)
        except Exception as e:
            print(f"❌ 加载题库失败: {e}")
            return
        total_all = len(questions)
        start = max(args.start, 0)
        if args.limit and args.limit > 0:
            if args.shuffle:
                k = min(args.limit, len(questions))
                questions = random.sample(questions, k)
            else:
                questions = questions[start: start + args.limit]
        else:
            questions = questions[start:]
        total = len(questions)
        if total == 0:
            print("⚠️  没有可评估的题目。")
            return
        print(f"🚀 开始生成 {answers_prefix} 答案，题目数 {total} / {total_all}。API类型：{args.api_type}  模型：{args.model}  服务：{args.base_url}  线程数：{args.threads}")
        start_ms = time.time() * 1000
        results = []
        diags = []
        done_count = 0
        try:
            question_data = [(idx, q) for idx, q in enumerate(questions, start=1)]
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {executor.submit(process_single_question_freeform, qd, args): qd for qd in question_data}
                print_progress(0, total, 0)
                for future in as_completed(futures):
                    try:
                        res = future.result()
                        results.append({'question_id': res['question_id'], 'answer': res['answer']})
                        done_count += 1
                        if not res['answer']:
                            t = (res['raw'] or '')
                            qd = future_to_question = None
                            diags.append({
                                'question_id': res['question_id'],
                                'raw_len': len(t),
                                'raw_preview': t[:200],
                                'reason': 'empty_response' if not t else 'no_pattern_match'
                            })
                        print_progress(done_count, total, 0)
                    except Exception as e:
                        print(f"\n❌ 生成答案时发生错误: {e}")
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断生成！")
        end_ms = time.time() * 1000
        out_name = f"answers_{answers_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(os.path.join(os.path.dirname(__file__), out_name), 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n📋 答案JSON已生成: {out_name}  用时: {(end_ms - start_ms)/1000:.1f}秒")
        except Exception as e:
            print(f"❌ 保存答案JSON失败: {e}")
        if diags:
            diag_name = f"answers_{answers_prefix}_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(os.path.join(os.path.dirname(__file__), diag_name), 'w', encoding='utf-8') as f:
                    json.dump({'empty_count': len(diags), 'items': diags}, f, ensure_ascii=False, indent=2)
                print(f"⚠️  诊断文件已生成: {diag_name}  空答案: {len(diags)}")
            except Exception as e:
                print(f"⚠️  诊断文件保存失败: {e}")

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if args.mcq_file:
        run_mcq(os.path.join(os.path.dirname(__file__), args.mcq_file) if not os.path.isabs(args.mcq_file) else args.mcq_file, 'custom')
    else:
        if args.dataset == 'strike':
            run_mcq(os.path.join(data_dir, 'StrikeEval.json'), 'StrikeEval')
        elif args.dataset == 'cissp':
            run_mcq(os.path.join(data_dir, 'cissp.json'), 'cissp')
        elif args.dataset == 'cs_eval':
            run_freeform(os.path.join(data_dir, 'cs-eval.json'), 'cs_eval')
        else:
            overall_start = time.time() * 1000
            s_summary = run_mcq(os.path.join(data_dir, 'StrikeEval.json'), 'StrikeEval')
            c_summary = run_mcq(os.path.join(data_dir, 'cissp.json'), 'cissp')
            run_freeform(os.path.join(data_dir, 'cs-eval.json'), 'cs_eval')
            overall_end = time.time() * 1000
            try:
                combined_name = f"report_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                combined_path = os.path.join(os.path.dirname(__file__), combined_name)
                generate_combined_summary([s_summary, c_summary], combined_path, args.model, total_ms=overall_end - overall_start)
                print(f"📋 综合概览报告已生成: {combined_name}")
            except Exception as e:
                print(f"❌ 生成综合概览失败: {e}")


if __name__ == '__main__':
    main()
