"""
사내 딥리서치 API 호출 스크립트.
.env 파일에서 크리덴셜을 로드하고 LangGraph API를 호출합니다.

Usage:
    python3 deepresearch_call.py "<query>" <mode>
    mode: plan | summarize
"""

import sys
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "IM_LIGHT_URL",
    "AUTH_TOKEN",
    "DS_WEBSEARCH_MCP_URL",
    "DS_WEBSEARCH_MCP_NAME",
    "GITHUB_TOKEN",
    "CONFLUENCE_USERNAME",
    "CONFLUENCE_PASSWORD",
]


def check_env():
    missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]
    if missing:
        print(f"ERROR: 환경 변수 누락: {', '.join(missing)}", file=sys.stderr)
        print("서버 관리자에게 문의하세요.", file=sys.stderr)
        sys.exit(1)


def check_server(base_url: str):
    try:
        resp = requests.get(f"{base_url}/health", timeout=3)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"ERROR: 서버 연결 실패 ({base_url}): {e}", file=sys.stderr)
        print("서버 관리자에게 문의하세요.", file=sys.stderr)
        sys.exit(1)


def call_api(query: str, mode: str) -> str:
    base_url = os.environ["IM_LIGHT_URL"]
    payload = {
        "query": query,
        "user_data": {
            "auth_token": os.environ["AUTH_TOKEN"],
            "mcp_servers": [
                {
                    "url": os.environ["DS_WEBSEARCH_MCP_URL"],
                    "name": os.environ["DS_WEBSEARCH_MCP_NAME"],
                    "requestOptions": {
                        "headers": {
                            "github-token": os.environ["GITHUB_TOKEN"],
                            "confluence-username": os.environ["CONFLUENCE_USERNAME"],
                            "confluence-password": os.environ["CONFLUENCE_PASSWORD"],
                        }
                    },
                }
            ],
        },
        "mode": mode,
    }

    resp = requests.post(
        f"{base_url}/agent/deepresearch/completions",
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()

    data = resp.json()
    if "result" in data:
        return data["result"]
    if "content" in data:
        return data["content"]
    messages = data.get("messages", [])
    if messages:
        return messages[-1].get("content", "")
    return json.dumps(data, ensure_ascii=False)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 deepresearch_call.py \"<query>\" <mode>", file=sys.stderr)
        print("mode: plan | summarize", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    mode = sys.argv[2]

    if mode not in ("plan", "summarize"):
        print(f"ERROR: mode는 'plan' 또는 'summarize' 이어야 합니다. (받은 값: {mode})", file=sys.stderr)
        sys.exit(1)

    check_env()
    check_server(os.environ["IM_LIGHT_URL"])

    result = call_api(query, mode)
    print(result)


if __name__ == "__main__":
    main()
