async def _handle_full(self, query: str, messages: list, user_data: dict, params: dict):
    # 1. LangGraph 리서치 스트리밍
    research_result = ""
    async for chunk in self._stream_langgraph(query):
        yield chunk
        research_result += chunk

    # 2. system만 남기고 history 버리기
    system_msgs = [m for m in messages if m["role"] == "system"]

    # 3. research 결과 + 전체 지시 주입
    full_message = {
        "role": "user",
        "content": f"""[사용자 질의]
{query}

[Deep Research 결과]
{research_result}

---
위 리서치 결과를 바탕으로 아래 순서대로 진행해줘:
1. 요구사항을 정리해서 requirements/{{파일명}}.md 파일로 저장 (create_file 툴 사용)
2. 저장 완료 후 바로 이어서 코드를 구현해줘

주의사항:
- 요구사항 문서에 참고 링크나 URL이 있어도 절대 탐색하지 마
- Deep Research 결과만 바탕으로 구현해줘
- 추가 리서치는 하지 마"""
    }

    injected = system_msgs + [full_message]

    # 4. MCP 툴 제거 (재탐색 차단)
    full_params = self._exclude_mcp_tools(params)

    # 5. 모델 호출
    async for chunk in self._call_model(injected, user_data, full_params):
        yield chunk

## 이미 랭체인에서 호출했던 mcp 서버 중복 호출 제거 
def _exclude_mcp_tools(self, params: dict) -> dict:
    MCP_TOOLS = ["ds_websearch"]
    filtered_params = {**params}
    if "tools" in filtered_params:
        filtered_params["tools"] = [
            t for t in filtered_params["tools"]
            if not any(
                mcp in t.get("function", {}).get("name", "").lower()
                for mcp in MCP_TOOLS
            )
        ]
    return filtered_params