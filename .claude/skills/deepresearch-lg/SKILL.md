---
name: deepresearch-lg
description: |
  URL 또는 요구사항을 기반으로 요구사항 분석 → 마크다운 저장 → 코드 생성을 수행하는 통합 리서치 스킬.
  LangGraph 서버 실행 여부를 자동 감지하여 실행 환경에 맞게 동작합니다.

  - LangGraph 서버 실행 중 → LangGraph API 호출 (MCP가 LangGraph에 붙어있는 환경)
  - LangGraph 서버 없음   → Task(general-purpose) 직접 실행 (MCP가 Claude Code에 붙어있는 환경)

  호출 방식:
  - `/deepresearch-lg plan "질의"` — 요구사항 분석 후 MD 저장, 사용자 확인 대기
  - `/deepresearch-lg do`          — 저장된 MD 기반으로 코드 생성
  - `/deepresearch-lg "질의"`      — plan + do 전체 파이프라인 자동 실행

  Examples:
  - `/deepresearch-lg plan "A 사이트를 참고해서 FastAPI 서버 만들어줘"`
  - `/deepresearch-lg do`
  - `/deepresearch-lg "https://example.com 보고 인증 API 만들어줘"`
argument-hint: "[plan|do] [질의 또는 URL]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

# DeepResearch-LG Skill

> URL/요구사항 리서치 → 마크다운 요구사항 문서화 → 코드 생성을 수행합니다.
> LangGraph 서버 유무를 자동 감지하여 실행 환경에 맞는 경로를 선택합니다.

---

## 전체 흐름

```
/deepresearch-lg plan "질의"
        ↓
[Step 1] 모드 판별 + 입력 파싱
        ↓
[Step 2] 환경 감지
        ├─ LangGraph 실행 중 → 경로 A: LangGraph API 호출
        └─ LangGraph 없음   → 경로 B: Task(general-purpose) 호출
        ↓
[Step 3] 결과를 requirements/{name}.md 저장
        ↓
  Plan 모드 → 저장 후 종료 (사용자 검토 대기)
  Full 모드 → Step 4로 자동 진행
        ↓
[Step 4] requirements MD 기반 코드 생성
```

---

## Step 1: 모드 판별 + 입력 파싱

인자(argument)의 첫 번째 단어를 확인합니다:

- 첫 단어가 `plan` → **Plan 모드** (Step 1~3 실행 후 대기)
- 첫 단어가 `do`   → **Do 모드** (Step 4만 실행)
- 그 외 / 인자 없음 → **Full 모드** (Step 1~4 자동 실행)

`plan` 또는 Full 모드에서:
- `plan` 키워드 이후 텍스트를 질의(query)로 사용합니다.
- 질의에 URL(http:// 또는 https://) 포함 여부를 확인합니다.
- 질의가 너무 짧거나 모호하면(5단어 미만, URL 없음) AskUserQuestion으로 목표를 구체화합니다.

---

## Step 2: 환경 감지 및 리서치 실행 (Plan 모드 / Full 모드)

### 환경 감지

Bash로 LangGraph 서버 실행 여부를 확인합니다:

```bash
# LANGGRAPH_URL 환경변수 없으면 기본값 사용
LG_URL=${LANGGRAPH_URL:-http://localhost:2024}
curl -s -f "${LG_URL}/ok" > /dev/null 2>&1 && echo "langgraph" || echo "local"
```

---

### 경로 A — LangGraph 서버 실행 중 (`langgraph`)

```
언제: MCP(confluence_mcp, github_mcp)가 LangGraph 환경에만 붙어있을 때
방법: LangGraph API를 Bash로 호출
```

Bash로 다음 순서로 실행합니다:

```bash
# 1. 스레드 생성
THREAD_ID=$(curl -s -X POST "${LG_URL}/threads" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['thread_id'])")

# 2. 리서치 실행 및 결과 대기
curl -s -X POST "${LG_URL}/threads/${THREAD_ID}/runs/wait" \
  -H "Content-Type: application/json" \
  -d "{
    \"assistant_id\": \"Deep Researcher\",
    \"input\": {
      \"messages\": [{\"role\": \"user\", \"content\": \"{질의}\"}]
    }
  }" | python3 -c "
import sys, json
data = json.load(sys.stdin)
messages = data.get('messages', [])
for m in reversed(messages):
    if m.get('type') == 'ai':
        print(m['content'])
        break
"
```

Bash 출력 전체를 리서치 결과로 수집합니다.

---

### 경로 B — LangGraph 서버 없음 (`local`)

```
언제: MCP(confluence_mcp, github_mcp)가 Claude Code에 붙어있을 때
방법: Task(general-purpose) 직접 실행
```

Task 툴로 `general-purpose` 서브에이전트를 실행합니다.
프롬프트:

```
당신은 기술 요구사항 추출 에이전트입니다.

사용자의 질의: {질의}

[URL이 있는 경우]
1. 질의에 포함된 URL을 확인합니다.
   - Confluence URL이면 confluence_mcp 툴 사용
   - GitHub URL이면 github_mcp 툴 사용
2. 페이지를 fetch하고 기술적으로 관련된 정보를 추출합니다.
3. 반환된 링크 목록에서 context와 text를 보고 관련 있는 서브링크만 재귀적으로 탐색합니다.
   - 관련 링크: API 스펙, 인증 흐름, 데이터 모델, 설정 방법
   - 제외 링크: 마케팅, 가격, 변경 이력, 무관한 기능
   - 최대 깊이: 2단계, 최대 fetch 횟수: 5회
4. 각 fetch 후 think_tool로 판단합니다:
   - 추출한 기술 정보는 무엇인가?
   - 어떤 링크를 따라갈 것인가, 이유는?
   - 충분한 스펙이 확보됐는가?

[URL이 없는 경우]
- 툴 호출 없이 보유 지식 기반으로 직접 응답합니다.
- 불확실한 부분은 명시합니다.

최종 결과를 다음 구조로 출력합니다:
1. **목표 요약** — 사용자가 만들려는 것
2. **기술 스펙** — 엔드포인트, 스키마, 인증, 데이터 형식, 제약사항
3. **구현 요구사항** — 구체적으로 구현해야 할 항목 목록
4. **탐색한 페이지** — (URL 있는 경우) 방문한 URL과 각각에서 얻은 정보
```

Task 에이전트의 전체 출력을 수집합니다.

---

## Step 3: 마크다운 파일 저장 (Plan 모드 / Full 모드)

- 질의 내용을 바탕으로 kebab-case 파일명을 결정합니다.
  - 예: "FastAPI LLM 서버 연동" → `fastapi-llm-integration`
  - 예: "인증 API 구현" → `auth-api`
- 저장 경로: `requirements/{feature-name}.md`
- `requirements/` 디렉토리가 없으면 먼저 생성합니다.
- 같은 이름 파일이 이미 있으면 덮어쓰기 전에 사용자에게 확인합니다.
- 파일 맨 위에 메타데이터를 추가합니다:

```
<!-- generated: {오늘 날짜} -->
<!-- status: draft -->
<!-- source: deepresearch-lg -->
<!-- env: langgraph | local -->   ← 실제 사용된 경로 기록
```

Step 2의 리서치 결과 전체를 그 아래에 붙여넣습니다.

**Plan 모드**: 저장 후 다음을 안내하고 종료합니다:
> "요구사항 파일을 저장했습니다: `requirements/{feature-name}.md`
> 파일을 검토·수정한 뒤 `/deepresearch-lg do`를 실행하면 코드를 생성합니다."

**Full 모드**: 저장 후 확인 없이 Step 4로 진행합니다.

---

## Step 4: 코드 생성 (Do 모드 / Full 모드)

**Do 모드 진입 시**: 가장 최근에 수정된 `requirements/*.md` 파일을 자동으로 찾습니다.
- 파일이 없으면: "생성된 요구사항 파일이 없습니다. 먼저 `/deepresearch-lg plan`을 실행하세요." 안내 후 종료.
- 파일이 여러 개이면: AskUserQuestion으로 어느 파일을 사용할지 선택하게 합니다.

**4-1. 요구사항 파싱**
- Must Have 항목 추출
- Should Have 항목 추출 (간단한 것만 구현)
- Out of Scope 확인 → 절대 구현하지 않음
- 블로킹 Open Question이 있으면 사용자에게 질문 후 진행

**4-2. 코드베이스 탐색**
- 수정할 파일 파악 (새 파일 생성은 최소화)
- 기존 패턴·스타일·네이밍 규칙 확인

**4-3. 코드 구현**
- Must Have 먼저, 이후 Should Have
- 각 변경에 `# FR-XX:` 인라인 주석 추가
- Out of Scope 항목은 구현하지 않음

**4-4. 요구사항 파일 상태 업데이트**
```
<!-- status: implemented -->
<!-- implemented: {오늘 날짜} -->
```

---

## Step 5: 결과 보고

- 수정·생성된 파일 목록
- 구현된 항목 (Must Have / Should Have)
- 스킵된 항목과 이유
- 미해결 Open Questions

---

## 규칙

- 코드를 요구사항 문서에서만 도출합니다. 추측으로 기능을 추가하지 않습니다.
- Out of Scope 항목은 절대 구현하지 않습니다.
- 요구사항과 무관한 리팩토링·정리는 하지 않습니다.
- Full 모드에서도 블로킹 Open Question이 있을 때만 사용자에게 질문합니다.
