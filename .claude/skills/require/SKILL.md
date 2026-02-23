---
name: require
description: "Use this skill when a user describes something they want to build, add, or change — in any form, casual or detailed. Examples: '이런 기능 만들고 싶어', 'I want to add X', 'can we do Y?'. Invokes the requirements-analyst sub-agent and saves the structured output to requirements/{feature-name}.md."
---

사용자가 만들고 싶은 것을 이야기했습니다. 지금부터 요구사항 정리를 시작합니다.

코드를 작성하지 마세요. 이 단계는 요구사항 문서를 만드는 단계입니다.

## 진행 순서

### 1. requirements-analyst 서브에이전트 실행
- Task 툴로 `requirements-analyst` 서브에이전트를 실행합니다.
- 사용자가 말한 내용을 그대로 프롬프트로 전달합니다. 요약하거나 바꾸지 마세요.
- 에이전트의 전체 출력을 수집합니다.

### 2. 파일명 결정
- 기능 내용을 바탕으로 짧은 kebab-case 파일명을 결정합니다.
  - 예: "검색 결과 캐싱" → `cache-search-results`
  - 예: "PDF 업로드 지원" → `pdf-upload`
- 저장 경로: `requirements/{feature-name}.md`

### 3. 마크다운 파일로 저장
- Write 툴로 `requirements/{feature-name}.md`에 저장합니다.
- 파일 맨 위에 메타데이터를 추가합니다:
  ```
  <!-- generated: {오늘 날짜} -->
  <!-- status: draft -->
  ```
- 에이전트 출력 전체를 그 아래에 붙여넣습니다.
- `requirements/` 디렉토리가 없으면 먼저 생성합니다.

### 4. 사용자에게 결과 안내 및 진행 여부 확인
- 저장된 파일 경로를 알려줍니다.
- Must Have 요구사항 개수와 미결 질문(Open Questions)이 있으면 간략히 요약합니다.
- 그런 다음 반드시 다음 질문을 합니다:
  > "요구사항 파일을 저장했습니다. 검토 없이 바로 구현을 시작할까요? (y/n)"
- 사용자가 **y** 또는 긍정적으로 답하면: 즉시 `implement` 워크플로우를 이어서 실행합니다 — `requirements/{feature-name}.md`를 입력으로 사용합니다.
- 사용자가 **n** 또는 부정적으로 답하면: "파일을 검토·수정한 뒤 `/implement requirements/{feature-name}.md`를 실행하세요." 라고 안내하고 종료합니다.

## 규칙
- 코드를 생성하지 않습니다.
- 같은 이름의 파일이 이미 있으면, 덮어쓰기 전에 사용자에게 확인합니다.
- 사용자의 설명이 너무 짧고 모호해서 요구사항을 추출할 수 없을 경우, 에이전트를 실행하기 전에 핵심 질문 2~3개를 먼저 물어봅니다.
