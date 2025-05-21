# Task: Support Multi-Modal Tool Return in Agents & Storage
**Status**: Not Started

## Analysis
- [ ] Examine `src/agents/common/message_parser.py::extract_tool_outputs` – currently handles `content` as `str|dict|None`; needs binary/image/audio support and MIME typing.
- [ ] Locate DB schema for stored tool outputs (`src/db/models.py`?) – do we persist blobs or links?
- [ ] Identify tool implementations that already return images (search `content_type="image"` or similar).
- [ ] Understand current Evolution channel payloads – MMS? (WhatsApp images?)

## Plan
Step 1 — Data model extension
  - [ ] Define `ToolOutputContent = Union[str, dict, bytes]` + metadata field `mime_type: str | None` in parser output
  - [ ] Adjust `AgentResponse.tool_outputs` list item schema to include `mime_type` and `size`.

Step 2 — Parser upgrade
  - [ ] Update `extract_tool_outputs` to detect `part.kind == 'tool-return'` with multi-modal payload; capture `content_type`/`media_type` attributes when present.
  - [ ] Add preview logging for binary (e.g., log `bytes len`)

Step 3 — Persistence strategy
  - [ ] For small (<256 kB) blobs store base64 in DB; for larger save to `media/` folder and persist filepath.
  - [ ] Migrate DB models accordingly with Alembic revision.

Step 4 — Downstream consumption
  - [ ] API layer: if `mime_type` starts with `image/`, render link or data URI in JSON response.
  - [ ] CLI / Discord / WhatsApp presenters: detect and send proper attachment.

Step 5 — Tests
  - [ ] Create fake tool that returns an image (bytes) and assert round-trip through Agent → Response → Storage.

## Execution
- [ ] Implementation 1: schema + parser
- [ ] Implementation 2: DB migration + storage helper
- [ ] Implementation 3: update one channel presenter (Discord) as PoC

## Summary
- [ ] Files modified: message_parser, response models, storage helpers, migration script 