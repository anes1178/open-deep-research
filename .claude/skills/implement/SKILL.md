---
name: implement
description: "Use this skill when the user wants to generate code for a feature that already has a requirements document. Requires a path to a requirements/{feature-name}.md file as the argument. Always run /require first if no requirements file exists."
---

You are starting the **implementation phase** of a feature development workflow. Your job is to generate code strictly derived from the requirements document — not from assumptions or conversations.

## Your Task

The user has provided a path to a requirements document (given as the argument, e.g., `requirements/pdf-upload.md`).

### Step 0: Validate the requirements file
- Check that the file exists using the Read tool.
- If the file does not exist, **stop immediately** and tell the user:
  > "No requirements file found at `{path}`. Please run `/require \"{feature description}\"` first to generate one."
- If the file exists but its `status` metadata is `draft`, warn the user:
  > "This requirements document is marked as **draft**. Open questions or unresolved items may affect implementation quality. Proceeding anyway — review the output carefully."

### Step 1: Read and parse the requirements document
- Read the full contents of the requirements file.
- Extract:
  - **Must Have** functional requirements (FR table rows with "Must Have" priority)
  - **Should Have** functional requirements (implement if straightforward)
  - **Non-Functional Requirements** relevant to implementation (performance, security, etc.)
  - **Constraints** that affect code structure or technology choices
  - **Out of Scope** items — do NOT implement these, even if they seem natural extensions
- Note any **Open Questions** — flag them in your output but do not block on them unless they are blocking (e.g., "which database?" when no database exists yet).

### Step 2: Explore the existing codebase
- Before writing any code, read the relevant existing files to understand:
  - Current architecture and patterns in use
  - Where the new code should live (which files to edit vs. create)
  - Existing abstractions to reuse (don't duplicate)
- Focus on: `src/open_deep_research/` — `deep_researcher.py`, `configuration.py`, `state.py`, `utils.py`, `prompts.py`
- Check if any legacy code in `src/legacy/` is relevant.

### Step 3: Generate implementation code
- Implement **only** what is specified in the Must Have (and optionally Should Have) requirements.
- Follow the existing code style and patterns in the project.
- Do not add features, config options, or abstractions not requested in the requirements.
- For each implemented requirement, add a brief inline comment referencing its FR ID (e.g., `# FR-01: ...`).

### Step 4: Update the requirements file status
- After implementation, update the metadata header in `requirements/{feature-name}.md`:
  ```
  <!-- status: implemented -->
  <!-- implemented: {today's date} -->
  ```

### Step 5: Report to the user
Provide a summary:
- List of files created or modified
- Which FR IDs were implemented (Must Have / Should Have)
- Which FR IDs were skipped and why (Could Have, Won't Have, or blocked by open questions)
- Any open questions that were flagged but not blocking

## Hard Rules
- **Never implement without a valid requirements file.** If the argument is missing, ask the user to provide the path or run `/require` first.
- **Out of Scope items must not be implemented**, even if requested in the same message.
- Do not rewrite or refactor code unrelated to the requirements.
- Do not add error handling, logging, or validation beyond what the requirements specify.
- If an Open Question is blocking (you cannot implement a Must Have without answering it), stop and ask the user before proceeding.
