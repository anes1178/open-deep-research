---
name: internal-do
description: |
  internal-researcher 에이전트가 생성한 requirements 파일을 기반으로 코드를 구현합니다.
  파일 경로를 인자로 받거나, 생략 시 가장 최근 internal-researcher 파일을 자동으로 찾습니다.

  Examples:
  - `/internal-do` — 최근 internal-researcher requirements 파일 자동 감지 후 구현
  - `/internal-do requirements/auth-api.md` — 특정 파일 지정
argument-hint: "[requirements/{feature}.md]"
user-invocable: true
---

# Internal-Do Skill

> `internal-researcher` 에이전트가 생성한 요구사항 문서를 기반으로 코드를 구현합니다.

---

## Step 0: 요구사항 파일 확인

**인자가 있는 경우**: 해당 경로를 사용합니다.

**인자가 없는 경우**: Bash로 가장 최근 파일을 찾습니다:

```bash
ls -t requirements/*.md 2>/dev/null | head -5
```

각 파일을 Read해서 `source: internal-researcher` 메타데이터가 있는 파일을 선택합니다.

- 해당 파일 없음 → 다음 안내 후 종료:
  > "구현할 요구사항 파일이 없습니다. 사내 URL과 함께 요청하면 `internal-researcher`가 파일을 생성합니다."
- 여러 개 있으면 → 가장 최근 파일 사용, 사용자에게 알림

---

## Step 1: 요구사항 문서 파싱

Read 툴로 파일 전체를 읽고 아래를 추출합니다:

| 항목 | 처리 |
|------|------|
| **Must Have** FR 목록 | 반드시 구현 |
| **Should Have** FR 목록 | 간단한 것만 구현 |
| **Out of Scope** | 절대 구현하지 않음 — 리스트업만 |
| **Open Questions** | 블로킹 여부 판단 |
| **기술 스펙** | 엔드포인트, 스키마, 인증 방식 등 |

`status: implemented` 파일이면 AskUserQuestion으로 재구현 여부를 확인합니다.

블로킹 Open Question(Must Have 구현에 필수 정보 누락)이 있으면 구현 전 AskUserQuestion으로 해결합니다.

---

## Step 2: 코드베이스 탐색

구현 전에 아래를 파악합니다:

- Glob으로 관련 파일 탐색
- 기존 패턴·스타일·네이밍 규칙 확인 (Read로 핵심 파일 읽기)
- 재사용 가능한 기존 추상화 확인
- 새 파일 생성 vs 기존 파일 수정 결정

---

## Step 3: 구현 계획 수립 및 태스크 등록

TodoWrite로 구현 단계를 등록합니다:

```
[ ] 의존성 패키지 설치 (필요 시)
[ ] FR-01: {Must Have 항목}
[ ] FR-02: {Must Have 항목}
...
[ ] FR-XX: {Should Have 항목} (간단한 것만)
[ ] requirements 파일 상태 업데이트
```

의존성 설치가 필요한 경우 먼저 안내합니다:
```bash
# 예시
pip install {package}  # 또는 npm install / uv add 등
```

---

## Step 4: 구현

TodoWrite 항목 순서대로 Must Have → Should Have 구현합니다.

각 FR 완료 시마다 해당 TodoWrite 항목을 완료 처리합니다.

**규칙**:
- 각 변경에 `# FR-XX:` 인라인 주석 추가
- Out of Scope 항목은 절대 구현하지 않음
- 요구사항과 무관한 리팩토링·정리 하지 않음
- 요구사항에 없는 에러 핸들링·로깅·검증 추가하지 않음
- 기존 코드 스타일과 패턴을 따름

---

## Step 5: 요구사항 파일 상태 업데이트

구현 완료 후 요구사항 파일 상단 메타데이터를 수정합니다:

```
<!-- status: implemented -->
<!-- implemented: {오늘 날짜} -->
```

TodoWrite의 마지막 항목을 완료 처리합니다.

---

## Step 6: 결과 보고

아래 형식으로 보고합니다:

```
## 구현 완료

### 수정·생성된 파일
- `path/to/file.py` — 변경 내용 한 줄 요약

### 구현된 요구사항
**Must Have**
- FR-01: ...
- FR-02: ...

**Should Have**
- FR-XX: ... (구현됨)
- FR-XX: ... (스킵 — 이유)

### 스킵된 항목
- FR-XX: Out of Scope
- FR-XX: {스킵 이유}

### 미해결 Open Questions
- {블로킹 아닌 Open Question 목록}
```

---

## Hard Rules

- 유효한 요구사항 파일 없이 구현하지 않습니다.
- Out of Scope 항목은 절대 구현하지 않습니다.
- 블로킹 Open Question은 사용자 확인 후에만 진행합니다.
- 요구사항과 무관한 코드는 건드리지 않습니다.
