---
name: internal-research
description: |
  사내 서비스(Confluence, GitHub 등)를 딥리서치해서 결과를 저장합니다.
  scripts/deepresearch_call.py를 통해 LangGraph API를 호출합니다.

  호출 방식:
  - `/internal-research plan "질의"` — 아키텍처 문서 추출 → requirements/ 저장
  - `/internal-research summarize "질의"` — 요약본 → summarize/ 저장
  - `/internal-research "질의"` — plan 모드로 자동 실행

  Examples:
  - `/internal-research plan "https://confluence... 보고 인증 API 스펙 뽑아줘"`
  - `/internal-research summarize "https://confluence... 이 페이지 요약해줘"`
argument-hint: "[plan|summarize] \"질의\""
user-invocable: true
---

# Internal-Research Skill

> `scripts/deepresearch_call.py`를 실행해서 사내 LangGraph API를 호출하고 결과를 저장합니다.

---

## Step 0: 모드 및 질의 파싱

인자의 첫 단어를 확인합니다:
- 첫 단어가 `plan` → mode = `plan`, 나머지를 질의로 사용
- 첫 단어가 `summarize` → mode = `summarize`, 나머지를 질의로 사용
- 그 외 또는 인자 없음 → mode = `plan`, 전체를 질의로 사용

질의가 비어있으면 AskUserQuestion으로 입력받습니다.

---

## Step 1: 스크립트 실행

Bash로 실행합니다. 질의에 따옴표·특수문자가 포함될 수 있으므로 인자로 넘기지 않고 환경변수로 전달합니다:

```bash
QUERY="<질의>" MODE="<plan 또는 summarize>" \
  python3 "$(dirname "$0")/../.claude/skills/internal-research/scripts/deepresearch_call.py" "$MODE" <<'QEOF'
<질의 그대로>
QEOF
```

또는 스킬 디렉토리 절대경로를 직접 사용합니다:

```bash
python3 /path/to/.claude/skills/internal-research/scripts/deepresearch_call.py "<mode>" <<'QEOF'
<질의 그대로>
QEOF
```

스크립트는 stdin으로 질의를 받거나 첫 번째 인자로도 받습니다.

스크립트 출력:
- `stdout` → 리서치 결과 (그대로 사용)
- `stderr`에 `ERROR:` 포함 → 에러 메시지를 그대로 사용자에게 표시하고 종료

---

## Step 2: 파일명 결정

질의 내용을 바탕으로 kebab-case 파일명을 결정합니다.

예시:
- "인증 API 스펙 뽑아줘" → `auth-api`
- "결제 서비스 아키텍처" → `payment-service-architecture`
- URL만 있는 경우 → URL 경로의 마지막 세그먼트 기반

---

## Step 3: 결과 저장

스크립트 stdout 결과를 **재가공하지 않고 그대로** 저장합니다.

### mode: plan → `requirements/` 저장

경로: `requirements/{파일명}.md`

```
<!-- generated: {오늘 날짜} -->
<!-- status: draft -->
<!-- source: internal-research -->
<!-- mode: plan -->

{스크립트 출력 전체}
```

### mode: summarize → `summarize/` 저장

경로: `summarize/{파일명}.md`

```
<!-- generated: {오늘 날짜} -->
<!-- source: internal-research -->
<!-- mode: summarize -->

{스크립트 출력 전체}
```

디렉토리가 없으면 먼저 생성합니다.

저장 완료 후:
> "저장 완료: `{경로}`"

---

## 규칙

- 스크립트 결과를 재구조화하지 않습니다.
- stderr에 에러가 있으면 즉시 종료합니다. 재시도하지 않습니다.
- 크리덴셜은 `.env`에서 스크립트가 직접 로드합니다. 스킬에서 다루지 않습니다.
