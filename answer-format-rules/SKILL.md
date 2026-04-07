---
name: answer-format-rules
description: Enforce a strict house style for factual or retrieval-based answers. Use when Codex needs to write or rewrite a final answer to match fixed response rules such as default bilingual English-Chinese output, a one-sentence core definition, structured headings and lists, preserved `[Note X](#)` citations, citation placement constraints, YMYL disclaimers, ambiguity handling, or discard and refusal rules.
---

# Answer Format Rules

## Overview

Apply this skill before returning any user-facing answer that must follow the supplied house style.
Keep this file lean; read [references/format_rules.md](references/format_rules.md) whenever the task depends on detailed formatting, citation, safety, or discard rules.

## Workflow

1. Classify the request.
2. Verify note accuracy and scope.
3. Lock the core answer.
4. Build the body.
5. Preserve citations.
6. Apply safety and discard rules.
7. Run a final compliance check.

## Classify The Request

- Decide whether the answer should be a short answer, a standard factual explanation, a multi-meaning disambiguation, a how-to answer, a YMYL answer with a disclaimer, or a refusal or discard.
- If the query is non-English, depends primarily on images or video, is purely promotional, is highly time-sensitive, or maps to prohibited or unsupported content, follow the discard or refusal rules in [references/format_rules.md](references/format_rules.md).

## Verify Note Accuracy And Scope

- For time-sensitive, political, legal, medical, or otherwise unstable facts, browse or otherwise verify before finalizing.
- Treat online verification as a consistency check on note content, not as permission to expand beyond the notes.
- Every factual claim in the final answer must be supported by the notes. Do not add web-only facts, dates, numbers, entities, or developments that are absent from the notes.
- If a note cannot be verified confidently or conflicts with stronger evidence, remove or qualify that note-supported point instead of replacing it with new external facts.

## Lock The Core Answer

- Write a one-sentence opening paragraph that only states what the subject is.
- Wrap the full core definition in `***...***` and keep the linking verb outside the emphasis.
- For people, define with nationality plus profession only.
- For brands, products, and places, define with category or identity only.
- If the term has multiple major meanings, include the major meanings in the first sentence and keep their order aligned with the body sections.

## Build The Body

- Expand only the meanings promised by the opening sentence.
- For note-based tasks, keep every factual point traceable to the notes; online verification may filter claims but must not add new ones.
- Draft the English answer first, then produce a Chinese version that mirrors the same meaning, structure, and citation coverage.
- Use `####` headings only when multiple thematic blocks are needed. If the body has a single theme, go straight into lists.
- Put content under `####` headings into bullets or numbered steps rather than freeform paragraphs, unless the rules explicitly require a single paragraph for a single-item section.
- Use numbered lists for procedures, time order, rankings, and staged workflows.
- Keep subheadings concrete, parallel, and in Title Case.
- Keep the answer concise, decision-oriented, and free of repetitive filler.

## Preserve Citations

- Never delete existing `[Note X](#)` citations.
- Place citations at the end of the sentence, before the period, with a space before the first citation.
- Keep each citation independent: `[Note 1](#)[Note 2](#)`.
- Move citations from parent bullets to the concrete child bullets when nested detail appears.
- Ensure each bullet under a `####` heading carries at least one citation.

## Apply Safety And Discard Rules

- Keep only content that matches the locked core answer.
- Remove unverifiable personal impressions, unsupported judgments, and irrelevant alternate meanings.
- Add targeted health, legal, or investment disclaimers only when the answer gives advice in those domains.
- Refuse or discard prohibited sexual, violent, extremist, criminal, rumor, or pseudoscience content as directed in [references/format_rules.md](references/format_rules.md).

## Final Compliance Check

- Output both `English Version` and `中文版本` by default unless the task explicitly requests a single language.
- Put the English answer and the Chinese answer in separate code blocks with mirrored structure and citation coverage.
- Do not introduce facts in Chinese that are not present in English, or vice versa.
- Avoid meta phrasing such as "Based on the search results" or "According to the documents."
- Use quotation marks only for works or titles, not for people, brands, places, or ordinary nouns.
- Replace body-text markdown emphasis or backticks with straight double quotes when the rules require quoted titles or file names.
- Re-check punctuation, heading structure, note placement, and short-answer eligibility against [references/format_rules.md](references/format_rules.md) before finalizing.
