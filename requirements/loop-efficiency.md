# Requirements Analysis: Research Loop Efficiency Improvement

## 1. Executive Summary

The Open Deep Research agent currently over-iterates in both the supervisor loop and the researcher loop, causing unnecessarily long research sessions even when sufficient information has already been gathered. The goal of this feature is to introduce structural mechanisms that allow both the supervisor and individual researchers to detect sufficiency earlier, prevent redundant work, and terminate loops proactively rather than exhausting hard iteration limits.

## 2. Stakeholders & Context

**Primary users/beneficiaries:**
- End users who submit research queries and wait for results
- Developers and operators who configure and run the agent

**Business context and motivation:**
- Research runs are slow and expensive (LLM API calls, latency)
- Users report frustration when results take too long despite the answer being derivable from early findings
- Redundant research topics waste parallel agent slots and inflate cost

**Current state vs. desired state:**

| Dimension | Current State | Desired State |
|---|---|---|
| Supervisor termination | Only exits on `ResearchComplete`, no-tool-call, or hitting `max_researcher_iterations` (default 6) | Exits as soon as research is determined sufficient, even before the hard limit |
| Researcher termination | Only exits on `ResearchComplete`, no-tool-call, or hitting `max_react_tool_calls` (default 10) | Exits as soon as the specific sub-topic is answered, typically 2-5 searches |
| Duplicate topic handling | No deduplication; supervisor may dispatch identical or near-identical topics | Supervisor tracks dispatched topics and skips near-duplicates |
| Default iteration limits | Supervisor: 6, Researcher: 10 — both permissive | Defaults tightened to reflect typical sufficient-research patterns |
| Novelty of new findings | Not evaluated; new research output is accepted regardless of overlap | New research output is assessed for informational novelty before the supervisor continues |

**Key files affected:**
- `/Users/avely/open_deep_research/src/open_deep_research/deep_researcher.py` — supervisor, supervisor_tools, researcher, researcher_tools nodes
- `/Users/avely/open_deep_research/src/open_deep_research/state.py` — SupervisorState, ResearcherState
- `/Users/avely/open_deep_research/src/open_deep_research/configuration.py` — Configuration defaults and new fields
- `/Users/avely/open_deep_research/src/open_deep_research/prompts.py` — lead_researcher_prompt, research_system_prompt

---

## 3. Functional Requirements

| ID | Priority | Requirement | Acceptance Criteria |
|----|----------|-------------|---------------------|
| FR-01 | Must Have | The supervisor shall track all research topics dispatched via `ConductResearch` across its entire session, storing them as a list in `SupervisorState`. | Given a supervisor session, when `ConductResearch` is called, then the `dispatched_topics` field in `SupervisorState` is updated to include the new topic before the researcher subgraph is invoked. |
| FR-02 | Must Have | Before dispatching a new `ConductResearch` call, the `supervisor_tools` node shall compare the proposed topic against all previously dispatched topics and drop topics that are semantically near-duplicate (overlap above a configurable similarity threshold). | Given a second `ConductResearch` call with a topic substantially similar to a prior one, when `supervisor_tools` processes it, then a `ToolMessage` error is returned for that call explaining the duplication, and the researcher subgraph is NOT invoked for it. |
| FR-03 | Must Have | The supervisor prompt (`lead_researcher_prompt`) shall be updated to include an explicit instruction to review all previously dispatched topics before issuing new `ConductResearch` calls and to skip topics already covered. | Given an updated prompt, when the supervisor LLM is invoked, then its output demonstrates awareness of prior topics and does not re-request already-covered ground in the majority of test cases. |
| FR-04 | Must Have | The researcher prompt (`research_system_prompt`) shall be updated to enforce stricter stop-when-sufficient guidance, explicitly lowering the default tool-call budget guidance from "up to 5" to "up to 3 for complex, 1-2 for simple" and reinforcing the "stop immediately" triggers. | Given a simple factual query, when the researcher runs, then it terminates within 2 tool calls in the majority of test cases without hitting the hard limit. |
| FR-05 | Must Have | The default value of `max_researcher_iterations` in `Configuration` shall be reduced from 6 to 3. The UI slider range and description shall be updated accordingly. | Given a default configuration with no overrides, when `Configuration.from_runnable_config` is called, then `max_researcher_iterations` equals 3. |
| FR-06 | Must Have | The default value of `max_react_tool_calls` in `Configuration` shall be reduced from 10 to 5. The UI slider range and description shall be updated accordingly. | Given a default configuration with no overrides, when `Configuration.from_runnable_config` is called, then `max_react_tool_calls` equals 5. |
| FR-07 | Should Have | After each completed `ConductResearch` round, the `supervisor_tools` node shall compute a novelty score for the new findings relative to existing accumulated notes, using lightweight string-overlap heuristics (e.g., Jaccard similarity on word sets). If the score is below a configurable threshold `min_novelty_threshold`, the supervisor loop shall be terminated early by returning `goto=END`. | Given accumulated notes that fully cover a topic, when a new `ConductResearch` returns findings with less than `min_novelty_threshold` novelty, then `supervisor_tools` returns `goto=END` without re-invoking the supervisor. |
| FR-08 | Should Have | A new boolean configuration field `enable_early_termination` shall be added to `Configuration` with a default of `True`. When set to `False`, the early termination behavior from FR-07 is disabled and the system behaves as today. | Given `enable_early_termination=False`, when FR-07 novelty check would otherwise trigger, then the supervisor loop continues normally. |
| FR-09 | Should Have | A new float configuration field `min_novelty_threshold` shall be added to `Configuration` with a default of `0.15` (15% new unique words). Its range shall be 0.0-1.0. | Given `min_novelty_threshold=0.15`, when a novelty score of 0.10 is computed, then early termination is triggered. |
| FR-10 | Should Have | A new float configuration field `duplicate_topic_similarity_threshold` shall be added to `Configuration` with a default of `0.75` (75% word overlap). Its range shall be 0.0-1.0. | Given `duplicate_topic_similarity_threshold=0.75`, when two topics share 80% word overlap, then the second topic is rejected as a duplicate. |
| FR-11 | Could Have | The `SupervisorState` shall expose a `skipped_topics` field (list of strings) that records topics that were dropped as near-duplicates, for observability and debugging. | Given a duplicate topic rejection, when the state is inspected, then `skipped_topics` contains the rejected topic string. |
| FR-12 | Could Have | When early termination is triggered by the novelty check (FR-07), the supervisor shall inject a synthetic `ToolMessage` explaining why research was terminated early, so the rationale is visible in the message trace. | Given an early termination event, when the message trace is reviewed in LangGraph Studio, then the last ToolMessage contains a human-readable explanation of the novelty score and threshold. |
| FR-13 | Won't Have (this iteration) | LLM-based semantic similarity for duplicate detection (embedding cosine similarity). Word-overlap heuristics are sufficient for V1 and avoid additional API calls. | N/A |
| FR-14 | Won't Have (this iteration) | Per-researcher novelty tracking or cross-researcher deduplication of search queries within a single `ConductResearch` session. Scope is limited to the supervisor level for V1. | N/A |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Performance | The duplicate-topic detection check (FR-02) shall add no more than 5ms of latency per `ConductResearch` dispatch. Heuristics must not call any external API or LLM. |
| NFR-02 | Performance | The novelty scoring computation (FR-07) shall complete in under 10ms for notes up to 100,000 characters. It must be a pure Python computation with no blocking I/O. |
| NFR-03 | Correctness | Reducing default iteration limits (FR-05, FR-06) shall not cause any existing automated test in `tests/run_evaluate.py` to regress by more than 10% on benchmark scores compared to the previous defaults. |
| NFR-04 | Maintainability | All new configuration fields shall follow the existing `pydantic` Field pattern with `x_oap_ui_config` metadata so they appear correctly in LangGraph Studio UI. |
| NFR-05 | Observability | Duplicate topic rejections and early terminations shall be logged at `INFO` level using Python's standard `logging` module, consistent with existing logging patterns in `deep_researcher.py`. |
| NFR-06 | Backward Compatibility | All new configuration fields shall be optional with documented defaults. Existing behavior shall be preserved for users who set `enable_early_termination=False` and restore the old `max_researcher_iterations=6`, `max_react_tool_calls=10`. |
| NFR-07 | Provider Compatibility | Changes shall not depend on any specific LLM provider. Heuristic-based novelty and duplicate checks must work identically across OpenAI, Anthropic, Google, Groq, and DeepSeek model configurations. |

---

## 5. Constraints

- The similarity and novelty computations must be implemented without additional third-party dependencies (no `scikit-learn`, `sentence-transformers`, etc.) to avoid changes to `pyproject.toml` for the core logic. Standard library (`collections`, `re`, `math`) or already-present dependencies only.
- The LangGraph state schema (`SupervisorState`, `ResearcherState`) must remain compatible with the existing `override_reducer` pattern and LangGraph's state serialization. New fields must use supported type annotations.
- The `supervisor_subgraph` is compiled at module load time (`researcher_subgraph = researcher_builder.compile()`). Changes to node logic must not require restructuring the subgraph compilation pattern.
- The existing `Command[Literal["supervisor", "__end__"]]` return type on `supervisor_tools` must be preserved; the early termination path continues to use `goto=END`.
- The `max_concurrent_research_units` cap on parallel `ConductResearch` calls must be respected alongside duplicate filtering — duplicate filtering happens before the concurrency cap is applied.

---

## 6. Assumptions

- A1: Word-level Jaccard similarity (intersection / union of word sets after lowercasing and stopword stripping) is sufficient for detecting duplicate topics and measuring novelty in V1. Semantic equivalence that uses different vocabulary is an acceptable false-negative at this stage.
- A2: The accumulated `notes` list in `SupervisorState` is a reliable proxy for "all research gathered so far" for novelty scoring purposes. Raw notes (`raw_notes`) are not used for this computation to avoid size issues.
- A3: The default values 3 (supervisor iterations) and 5 (researcher tool calls) represent a reasonable balance for most use cases. These will be validated against existing benchmarks before release (see NFR-03).
- A4: Users who need more thorough research for complex topics will adjust `max_researcher_iterations` and `max_react_tool_calls` upward via configuration rather than relying solely on defaults.
- A5: The `think_tool` calls made by the supervisor already provide some self-assessment behavior; the prompt changes in FR-03 augment this without replacing it.
- A6: The LangGraph Studio UI will correctly render new slider and boolean fields added via `x_oap_ui_config` metadata following the same pattern as existing fields.

---

## 7. Out of Scope

- Embedding-based or LLM-based semantic deduplication (FR-13) — deferred to a future iteration.
- Per-researcher deduplication of search queries (FR-14) — deferred to a future iteration.
- Automatic adjustment of iteration limits based on query complexity (adaptive budgeting) — not in this iteration.
- Changes to the legacy implementations in `/Users/avely/open_deep_research/src/legacy/` (`graph.py`, `multi_agent.py`). These files are not affected.
- Changes to the `clarify_with_user`, `write_research_brief`, `compress_research`, or `final_report_generation` nodes — these are not part of the iteration loop problem.
- User-facing UI changes beyond LangGraph Studio configuration fields (no new API endpoints, no new graph outputs visible to the end user).
- Performance profiling infrastructure or benchmarking tooling beyond what already exists in `tests/`.

---

## 8. Open Questions

| Priority | ID | Question | Impact if Unresolved |
|----------|----|-----------|-----------------------|
| High | OQ-01 | What is the acceptable regression threshold on benchmark scores when reducing defaults from 6/10 to 3/5? NFR-03 assumes 10%, but this needs explicit sign-off from the team before shipping. | Could block the default value changes (FR-05, FR-06) |
| High | OQ-02 | Should the `dispatched_topics` list (FR-01) be exposed in the public `AgentState` or remain internal to `SupervisorState` only? Exposing it enables downstream inspection but widens the public state schema. | Affects state schema design and backward compatibility |
| Medium | OQ-03 | What stopword list (if any) should be used for Jaccard similarity? Using no stopwords makes common words inflate similarity scores; using NLTK stopwords adds a dependency. A hardcoded minimal English stopword list may be the right compromise. | Affects accuracy of FR-02 and FR-07 |
| Medium | OQ-04 | Should `min_novelty_threshold` and `duplicate_topic_similarity_threshold` appear in the LangGraph Studio UI, or should they be environment-variable-only configuration for advanced users? Showing them risks confusing general users. | Affects UX and `x_oap_ui_config` metadata design |
| Low | OQ-05 | Should early termination (FR-07) also emit a signal to the `final_report_generation` node indicating that the report was generated from a truncated research session? This could help with report quality self-assessment. | Nice-to-have observability; does not block implementation |

---

## 9. Dependencies & Risks

**Dependencies:**

- FR-07, FR-08, FR-09 depend on FR-01 being implemented first, since novelty scoring requires the `dispatched_topics` and accumulated notes to be reliably tracked.
- FR-02 depends on FR-01 (topic tracking must exist before deduplication can be applied).
- FR-03 and FR-04 (prompt changes) are independent and can be implemented in parallel with state/logic changes.
- FR-05 and FR-06 (default value changes) are trivially independent but should be validated against benchmarks before merging.

**Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Reduced defaults (FR-05, FR-06) degrade research quality on complex multi-faceted queries | Medium | High | Run full evaluation suite (`tests/run_evaluate.py`) before and after; allow a rollback path via configuration. |
| Jaccard-based duplicate detection produces false positives for legitimately distinct topics that share domain vocabulary (e.g., "machine learning training data" vs. "machine learning training speed") | Medium | Medium | Set `duplicate_topic_similarity_threshold` conservatively at 0.75; rely on the supervisor's own `think_tool` reasoning as a second line of defense. |
| Novelty scoring on accumulated notes is inaccurate for very short or very long notes corpora | Low | Low | Cap the notes corpus used for novelty scoring at a fixed character limit (e.g., 50,000 chars) to ensure consistent behavior. |
| New `SupervisorState` fields break existing LangGraph state serialization in LangGraph Cloud deployments | Low | High | Test state serialization with the LangGraph dev server (`uvx langgraph dev`) before shipping; add new fields with `Optional` types and defaults. |
| Stricter researcher prompt (FR-04) causes researchers to terminate before gathering enough information for complex sub-topics | Medium | Medium | Make prompt guidance conditional on topic complexity cues (e.g., "if the topic has multiple distinct sub-questions, you may use up to 5 searches"). |
