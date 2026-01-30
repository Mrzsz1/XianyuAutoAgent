import argparse
import ast
import json
import os
from getpass import getpass
from pathlib import Path
from typing import Dict, Optional

import httpx


def load_env_file(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        os.environ.setdefault(key, value)


def parse_headers(raw: Optional[str]) -> Dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 兼容 Windows 命令行把引号吃掉后的形态：{User-Agent:Mozilla/5.0,Accept:application/json}
        stripped = raw.strip()
        if stripped.startswith("{") and stripped.endswith("}") and '"' not in stripped and "'" not in stripped:
            inner = stripped[1:-1].strip()
            if not inner:
                return {}
            parsed: Dict[str, str] = {}
            for part in inner.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    k, v = part.split(":", 1)
                elif "=" in part:
                    k, v = part.split("=", 1)
                else:
                    raise ValueError(f"无法解析 header 项: {part}")
                parsed[k.strip()] = v.strip()
            data = parsed
        else:
        # 兼容用户误传 Python dict 语法：{'User-Agent':'Mozilla/5.0'}
            try:
                data = ast.literal_eval(raw)
            except Exception as e:
                snippet = raw.replace("\n", " ")[:120]
                raise ValueError(
                    f"headers 解析失败：{e}. 你传入的是：{snippet}...；"
                    "请使用 JSON，例如：{\"User-Agent\":\"Mozilla/5.0\",\"Accept\":\"application/json\"}"
                ) from e
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise ValueError("headers 必须是 JSON 对象，且键/值都为字符串，例如：{\"User-Agent\":\"Mozilla/5.0\"}")
    return dict(data)


def summarize_body(text: str, limit: int = 400) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe an OpenAI-compatible /v1 endpoint without stopping the main program."
    )
    parser.add_argument("--env-file", default=".env", help="env 文件路径（默认 .env，不会覆盖已存在环境变量）")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base url（例如 https://xx.com/v1）")
    parser.add_argument("--model", default=None, help="模型名（例如 qwen-max）")
    parser.add_argument("--headers", default=None, help="额外请求头 JSON（例如 {\"User-Agent\":\"Mozilla/5.0\"}）")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="追加单个 header（可重复），格式 Key:Value 或 Key=Value（推荐 PowerShell 用这个）",
    )
    parser.add_argument("--prompt-key", action="store_true", help="如果环境变量没 API_KEY，则交互式输入（不回显）")
    args = parser.parse_args()

    load_env_file(args.env_file)

    base_url = (args.base_url or os.getenv("MODEL_BASE_URL", "")).rstrip("/")
    model = args.model or os.getenv("MODEL_NAME", "")
    api_key = os.getenv("API_KEY", "")

    if not api_key and args.prompt_key:
        api_key = getpass("API_KEY (不会回显): ").strip()

    extra_headers = parse_headers(args.headers or os.getenv("MODEL_DEFAULT_HEADERS"))
    for item in args.header:
        item = (item or "").strip()
        if not item:
            continue
        if ":" in item:
            k, v = item.split(":", 1)
        elif "=" in item:
            k, v = item.split("=", 1)
        else:
            raise ValueError("--header 格式应为 Key:Value 或 Key=Value")
        extra_headers[k.strip()] = v.strip()

    if not base_url:
        print("缺少 base_url：请传 --base-url 或设置 MODEL_BASE_URL")
        return 2
    if not api_key:
        print("缺少 API_KEY：请设置环境变量 API_KEY，或加 --prompt-key")
        return 2

    headers = dict(extra_headers)
    headers.setdefault("Accept", "application/json")
    headers.setdefault("User-Agent", "Mozilla/5.0")
    headers["Authorization"] = f"Bearer {api_key}"

    print("base_url:", base_url)
    print("model:", model or "(未指定)")
    print("extra_headers:", "on" if extra_headers else "off")

    with httpx.Client(timeout=20.0, headers=headers) as client:
        # 1) models list
        try:
            r = client.get(base_url + "/models")
            print("/models status:", r.status_code)
            print("/models content-type:", r.headers.get("content-type", ""))
            print("/models body(head):", summarize_body(r.text))
        except Exception as e:
            print("/models error:", repr(e))

        # 2) chat completion
        if model:
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0,
                }
                r = client.post(base_url + "/chat/completions", json=payload)
                print("/chat/completions status:", r.status_code)
                ct = r.headers.get("content-type", "")
                print("/chat/completions content-type:", ct)
                body_head = summarize_body(r.text)
                print("/chat/completions body(head):", body_head)
                if "text/html" in ct.lower() and ("blocked" in body_head.lower() or "request was blocked" in body_head.lower()):
                    print("=> 看起来是 WAF/Cloudflare 拦截（返回了 HTML 且包含 blocked 字样）")
            except Exception as e:
                print("/chat/completions error:", repr(e))
        else:
            print("未指定 model：跳过 /chat/completions（可用 --model 或设置 MODEL_NAME）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
