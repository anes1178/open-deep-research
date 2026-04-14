---
name: internal-research
description: |
  사내 서비스(Confluence, GitHub 등) 딥리서치부터 코드 구현까지 통합 관리합니다.

  호출 방식:
  - `/internal-research plan "질의"` — LangGraph 리서치 → requirements/ 저장
  - `/internal-research summarize "질의"` — LangGraph 리서치 → summarize/ 저장
  - `/internal-research do` — 최근 requirements 파일 기반 코드 구현
  - `/internal-research do requirements/auth-api.md` — 특정 파일 지정해서 구현

  Examples:
  - `/internal-research plan "https://confluence... 인증 API 스펙 뽑아줘"`
  - `/internal-research summarize "https://confluence... 요약해줘"`
  - `/internal-research do`
argument-hint: "[plan|summarize|do] [\"질의\" 또는 파일경로]"
user-invocable: true
---

# Internal-Research Skill

> 사내 LangGraph 딥리서치(`plan`/`summarize`) + 요구사항 기반 코드 구현(`do`)을 하나의 스킬로 통합합니다.

---

## 액션 판별

인자의 첫 단어를 확인합니다:

| 첫 단어 | 액션 | 설명 |
|---------|------|------|
| `plan` | **Plan** | LangGraph 리서치 → `requirements/` 저장 |
| `summarize` | **Summarize** | LangGraph 리서치 → `summarize/` 저장 |
| `do` | **Do** | `requirements/*.md` 읽어서 코드 구현 |
| 그 외 / 없음 | **Plan** | 기본값, 전체를 질의로 사용 |

---

## plan / summarize 액션

### Step 1: 질의 파싱

- `plan` 또는 `summarize` 키워드 이후 텍스트를 질의로 사용합니다.
- 질의가 비어있으면 AskUserQuestion으로 입력받습니다.

### Step 2: 스크립트 실행

스킬 디렉토리 내 `scripts/deepresearch_call.py`를 Bash로 실행합니다.
질의에 특수문자·줄바꿈이 포함될 수 있으므로 Python heredoc으로 전달합니다:

```bash
python3 ~/.claude/skills/internal-research/scripts/deepresearch_call.py <plan|summarize> << 'QEOF'
<질의 그대로>
QEOF
```

스크립트 출력:
- `stdout` → 리서치 결과 (그대로 사용)
- `stderr`에 `ERROR:` 포함 → 메시지를 사용자에게 표시하고 즉시 종료

### Step 3: 파일명 결정

질의 내용을 바탕으로 kebab-case 파일명을 결정합니다.
- "인증 API 스펙 뽑아줘" → `auth-api`
- "결제 서비스 아키텍처" → `payment-service-architecture`
- URL만 있는 경우 → URL 경로의 마지막 세그먼트 기반

### Step 4: 결과 저장

스크립트 stdout을 **재가공하지 않고 그대로** 저장합니다.

**plan** → `requirements/{파일명}.md`
```
<!-- generated: {오늘 날짜} -->
<!-- status: draft -->
<!-- source: internal-research -->
<!-- mode: plan -->

{stdout 전체}
```

**summarize** → `summarize/{파일명}.md`
```
<!-- generated: {오늘 날짜} -->
<!-- source: internal-research -->
<!-- mode: summarize -->

{stdout 전체}
```

디렉토리가 없으면 먼저 생성합니다.

저장 완료 후:
> "저장 완료: `{경로}`  
> 코드 구현을 시작하려면 `/internal-research do`를 실행하세요." (plan 모드만)

---

## do 액션

### Step 1: 요구사항 파일 결정

**인자에 파일 경로가 있는 경우**: 해당 경로를 사용합니다.

**인자가 `do`만 있는 경우**: 가장 최근 파일을 자동으로 찾습니다:

```bash
ls -t requirements/*.md 2>/dev/null | head -5
```

각 파일을 Read해서 `source: internal-research` 메타데이터가 있는 파일을 선택합니다.

- 파일 없음 → 다음 안내 후 종료:
  > "구현할 요구사항 파일이 없습니다. 먼저 `/internal-research plan \"질의\"`를 실행하세요."
- 여러 개 → 가장 최근 파일 사용, 사용자에게 알림
- `status: implemented` → AskUserQuestion으로 재구현 여부 확인

### Step 2: 요구사항 파싱

Read 툴로 파일 전체를 읽고 추출합니다:

| 항목 | 처리 |
|------|------|
| **Must Have** FR 목록 | 반드시 구현 |
| **Should Have** FR 목록 | 간단한 것만 구현 |
| **Out of Scope** | 절대 구현하지 않음 |
| **Open Questions** | 블로킹 여부 판단 |
| **기술 스펙** | 엔드포인트, 스키마, 인증 방식 등 |

블로킹 Open Question(Must Have 구현에 필수 정보 누락)이 있으면 AskUserQuestion으로 해결 후 진행합니다.

### Step 3: 코드베이스 탐색

- Glob으로 관련 파일 탐색
- 기존 패턴·스타일·네이밍 규칙 확인
- 재사용 가능한 기존 추상화 확인
- 새 파일 생성 vs 기존 파일 수정 결정

### Step 4: 구현 계획 수립

TodoWrite로 구현 단계를 등록합니다:

```
[ ] 의존성 패키지 설치 (필요 시)
[ ] FR-01: {Must Have 항목}
[ ] FR-02: {Must Have 항목}
[ ] FR-XX: {Should Have 항목} (간단한 것만)
[ ] requirements 파일 상태 업데이트
```

의존성 설치가 필요한 경우 먼저 안내합니다.

### Step 5: 구현

TodoWrite 순서대로 Must Have → Should Have 구현합니다.
각 FR 완료 시마다 TodoWrite 항목을 완료 처리합니다.

**규칙**:
- 각 변경에 `# FR-XX:` 인라인 주석 추가
- Out of Scope 항목은 절대 구현하지 않음
- 요구사항과 무관한 리팩토링·정리 하지 않음
- 요구사항에 없는 에러 핸들링·로깅·검증 추가하지 않음
- 기존 코드 스타일과 패턴을 따름

### Step 6: 요구사항 파일 상태 업데이트

```
<!-- status: implemented -->
<!-- implemented: {오늘 날짜} -->
```

### Step 7: 결과 보고

```
## 구현 완료

### 수정·생성된 파일
- `path/to/file.py` — 변경 내용 한 줄 요약

### 구현된 요구사항
**Must Have**
- FR-01: ...

**Should Have**
- FR-XX: ... (구현됨)
- FR-XX: ... (스킵 — 이유)

### 스킵된 항목
- FR-XX: Out of Scope

### 미해결 Open Questions
- {블로킹 아닌 항목}
```

---

## Hard Rules

- `plan`/`summarize`: 스크립트 결과를 재가공하지 않습니다.
- `plan`/`summarize`: stderr 에러 시 즉시 종료합니다. 재시도하지 않습니다.
- `do`: 유효한 요구사항 파일 없이 구현하지 않습니다.
- `do`: Out of Scope 항목은 절대 구현하지 않습니다.
- `do`: 블로킹 Open Question은 사용자 확인 후에만 진행합니다.
- 크리덴셜은 `scripts/deepresearch_call.py`의 `load_dotenv()`가 처리합니다.
