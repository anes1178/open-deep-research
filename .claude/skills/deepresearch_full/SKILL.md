아 그러면 스킬 내용을 LLM이 읽고 직접 수행하는 구조네!

그러면 full 모드 스킬만 심플하게:

```markdown
---
name: deepresearch-full
description: |
  /deepresearch plan 실행 후 완료되면 자동으로 /deepresearch do를 실행합니다.
  plan과 do를 순차적으로 처리하는 full 파이프라인입니다.
user-invocable: true
---

# DeepResearch Full 스킬

## 수행 순서

### 1단계: plan 실행
아래 메시지를 전송하고 응답이 완전히 끝날 때까지 기다려:
```
/deepresearch plan {사용자 질의}
```

### 2단계: 파일명 확인
plan 응답에서 `requirements/*.md` 파일 경로를 찾아.
찾지 못하면 사용자에게 "plan 단계에서 파일이 생성되지 않았습니다" 라고 알리고 종료.

### 3단계: do 실행
사용자에게 알림:
> "{파일명} 기반으로 코드 구현을 시작합니다."

아래 메시지를 전송해:
```
/deepresearch do {파일명}
```

## 규칙
- 반드시 plan이 완전히 끝난 후에 do 실행
- 각 단계 시작 전 사용자에게 진행 상황 알림
```

LLM이 이 스킬 읽고 순서대로 `/deepresearch plan` → 기다림 → `/deepresearch do` 실행하는 거야. create_file accept 타이밍도 자연스럽게 해결되고!