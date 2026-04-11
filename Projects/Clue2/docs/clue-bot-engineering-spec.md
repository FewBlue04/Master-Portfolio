# Clue Bot Engineering Spec

## Purpose

This document defines the target architecture and implementation plan for converting the current Clue AI into a deterministic deduction engine. The goal is to replace probability-driven behavior with a strict constraint propagation system plus a one-step greedy information-reduction policy.

This spec is written against the current repository state on April 10, 2026 and is intended to be executable: the next implementation pass should use this as the source of truth.

## Product Goal

Build a Clue bot that:

- Maintains a fully consistent knowledge base of card ownership constraints.
- Propagates constraints to closure after every observation.
- Chooses suggestions using deterministic one-step information reduction.
- Accuses only when the envelope solution is logically proven.

The bot is not a probability model, Monte Carlo player, or deep-search game AI. It is a deterministic constraint solver with a greedy move policy.

## Current Repo Assessment

The repo already contains pieces of the target system, but it does not yet satisfy the required design:

- [`clue_game/knowledge_base.py`](clue_game/knowledge_base.py) has a useful logical core, but its API is incomplete for simulation-based move scoring and state introspection.
- [`clue_game/bot.py`](clue_game/bot.py) violated the target design by using probability estimates and randomness (since addressed in code; this spec remains the design reference).
- [`simulate_quick.py`](simulate_quick.py) explicitly referenced Monte Carlo behavior, which is out of scope for the target bot.
- Implementation lives in the `clue_game` package (no separate `engine/` shim layer).
- [`clue_game/game.py`](clue_game/game.py) provides the integration points where bot observations and turn decisions flow through the engine.

## In Scope

- Rewrite the bot decision logic to be fully deterministic.
- Expand the knowledge base into a proper constraint engine with cloning, consistency checks, and scoring support.
- Standardize how observations are represented and applied.
- Add deterministic move evaluation based on measurable state reduction.
- Remove probability-based and randomness-based tie-breaking from bot behavior.
- Add tests for propagation, consistency, and move selection.

## Out of Scope

- Reinforcement learning
- Monte Carlo or stochastic search
- Opponent personality models
- Multi-turn planning beyond one-step simulation
- UI redesign
- Board movement optimization beyond current-room suggestion generation unless needed for correctness

## Target Architecture

The implementation will center around two primary modules.

### 1. KnowledgeBase

The `KnowledgeBase` is the source of truth for all logical facts and unresolved possibilities.

Responsibilities:

- Represent all possible owners for every card.
- Track confirmed ownership.
- Track envelope candidates by category.
- Enforce global game constraints.
- Apply observations as constraints.
- Propagate constraints until fixpoint.
- Detect contradictions.
- Support deep cloning for move evaluation.
- Expose deterministic state-delta metrics for scoring.

### 2. ClueBot

The `ClueBot` is a deterministic policy layer over the `KnowledgeBase`.

Responsibilities:

- Check for a solved envelope and accuse immediately.
- Generate legal suggestions from the current room.
- Evaluate each suggestion by simulating one-step outcomes on cloned knowledge bases.
- Choose the move with the highest deterministic reduction score.
- Break ties with a fixed, documented lexicographic rule.

## Canonical Data Model

The implementation should standardize on these concepts even if internal names differ.

### Entities

- Each player name
- Special entity: `ENVELOPE`

### Card Ownership State

Preferred representation:

- `possible_owners: dict[str, set[str]]`

Equivalent matrix form is also acceptable:

- `(entity, card) -> True | False | None`

Requirement:

- The code must support efficient derivation of the current possible owners of any card.

### Known Ownership

- `known_cards[player]: set[str]`

This may be derived rather than stored directly, but the API should expose it clearly.

### Envelope Candidates

- `envelope_candidates["suspect"]`
- `envelope_candidates["weapon"]`
- `envelope_candidates["room"]`

These may also be derived from card ownership state, but they must be queryable as first-class knowledge.

### Player Card Limits

- `num_cards_per_player[player]`

These limits are mandatory constraints in propagation.

### Disjunctive Show Constraints

When a player showed one of three suggested cards but the exact card is unknown, the knowledge base must preserve a disjunctive clause equivalent to:

- `player has at least one of {suspect, weapon, room}`

This is already partially modeled by `clauses` and should remain part of the design.

## Required Logical Constraints

The knowledge base must enforce all of the following:

1. Each card has exactly one owner among players plus envelope.
2. Each player holds exactly their dealt number of cards.
3. The envelope holds exactly one suspect, one weapon, and one room.
4. Any observation that contradicts prior knowledge is invalid and must fail fast.

## Propagation Rules

After every state update, the system must run propagation to closure until no further deductions are possible.

### Rule 1. Ownership Elimination

If `card` is confirmed to belong to `X`, eliminate all other entities as owners of that card.

### Rule 2. Singleton Assignment

If a card has exactly one remaining possible owner, assign that owner immediately.

### Rule 3. Player Card Completion

For each player:

- If confirmed cards equals their hand size, mark all other cards as impossible for that player.
- If confirmed cards plus unknown slots exactly equals their hand size, assign all unknowns to that player.

### Rule 4. Envelope Category Completion

For each category:

- If all but one card are eliminated from the envelope, assign the remaining card to the envelope.

### Rule 5. Clause Reduction

For each disjunctive show clause:

- Remove any card already impossible for that player.
- If one card remains, assign it.
- If one member of the clause is already true, mark the clause satisfied.
- If no cards remain, raise a contradiction.

### Rule 6. Consistency Enforcement

The system must reject any update path that leads to:

- A card with zero possible owners
- A player with more confirmed cards than allowed
- An envelope category with zero candidates
- A disjunctive clause with no satisfiable member
- Conflicting direct assignments

## Observation API

The knowledge base implementation must support these observation types:

- `observe_hand(player, card)`
- `observe_no_show(player, suspect, weapon, room)`
- `observe_showed_unknown(player, suspect, weapon, room)`
- `observe_showed_card_to_me(player, card)` or equivalent

If the current bot/game API uses slightly different names, those methods can be adapted, but the behavior must match these semantics.

## KnowledgeBase API Requirements

The target `KnowledgeBase` should expose at minimum:

- `add_constraint(...)`
- `propagate()`
- `clone()`
- `is_consistent()`
- `get_solution()`
- `is_solved()`
- `can_accuse()`
- `get_possible_owners(card)`
- `get_envelope_candidates(category)`
- `snapshot_metrics()`

### `snapshot_metrics()`

This should return deterministic counts used for move evaluation, for example:

- total remaining possible owners across all cards
- number of confirmed assignments
- number of remaining envelope candidates by category

This method is preferred over embedding score math directly against raw internals.

## Decision Policy

The bot must follow this exact decision order on its turn.

### Step 1. Accuse If Solved

If suspect, weapon, and room are all confirmed in the envelope:

- return accusation immediately

### Step 2. Generate Legal Suggestions

For the bot’s current room:

- generate every `(suspect, weapon, current_room)` combination

No randomness is allowed.

### Step 3. Evaluate Suggestions via One-Step Simulation

For each candidate suggestion:

1. Clone the current knowledge base.
2. Apply deterministic hypothetical responder outcomes that can arise from that suggestion.
3. Propagate to fixpoint after each hypothetical update.
4. Compute the resulting reduction score.

Important clarification:

Because the exact future observation depends on who can respond and what is revealed, the implementation must evaluate suggestions only through deterministic consequence models derived from current knowledge. It must not introduce probabilities. If multiple hypothetical outcomes are possible, the implementation should use a documented deterministic policy such as:

- worst-case guaranteed reduction, or
- minimum reduction across all logically possible responder outcomes

Recommended choice for implementation:

- score each suggestion by the minimum guaranteed reduction across its logically possible immediate outcomes

This best matches the product goal of maximizing guaranteed shrinkage of the hypothesis space.

### Step 4. Select Best Suggestion

Choose the move with the highest score.

Tie-breaker must be fixed and documented:

1. suspect name lexicographic ascending
2. weapon name lexicographic ascending
3. room name lexicographic ascending

No random tie-breaking is allowed.

## Scoring Function

The score must be based only on measurable deterministic reduction after propagation.

Recommended metric:

```text
score =
  eliminated_possible_owners
  + newly_forced_assignments
  + reduced_envelope_candidates
```

### Metric Definitions

- `eliminated_possible_owners`: decrease in total remaining possible-owner relationships across all cards
- `newly_forced_assignments`: increase in count of cards/entities that became confirmed true
- `reduced_envelope_candidates`: decrease in remaining envelope candidate counts summed across suspect, weapon, and room categories

The implementation may weight these components equally unless testing shows a compelling deterministic reason to change weights. Any weighting must remain static and documented.

## Required Refactor Targets

### 1. Rewrite `bot.py`

[`bot.py`](C:\Users\Matt\Downloads\Computer Science\Master-Portfolio\Projects\Clue2\bot.py) must be refactored to remove:

- `random`
- probability estimation
- clause-pressure heuristics not grounded in actual propagated state reduction
- any tie-breaking by chance

It should be replaced with:

- legal move generation
- one-step deterministic simulation
- guaranteed reduction scoring
- fixed lexicographic tie-breaking

### 2. Expand `clue_game/knowledge_base.py`

[`clue_game/knowledge_base.py`](clue_game/knowledge_base.py) should become the authoritative constraint engine.

Required additions:

- explicit clone support
- public propagation entry point
- public consistency checker
- possible-owner introspection helpers
- envelope candidate helpers
- metrics snapshot support
- cleaner exception model for contradictions

### 3. Package layout

All engine code imports through the `clue_game` package; keep public imports stable after rewrites.

### 4. Remove Monte Carlo References

[`simulate_quick.py`](simulate_quick.py) and any other Monte Carlo-related code paths should be removed or rewritten so all simulation remains deterministic and compatible with the new bot.

## Integration Requirements

The rewritten bot must continue to work with [`clue_game/game.py`](clue_game/game.py):

- suggestion flow
- no-show notifications
- known-card reveal handling
- unknown-card show handling
- safe accusation flow

No UI changes are required for the first implementation pass unless the current UI depends on removed bot internals.

## Error Handling

Contradictions should raise a dedicated exception type such as `ContradictionError` instead of generic `Exception`. This will make simulation safe:

- real observations that contradict state can be surfaced as engine bugs or invalid updates
- hypothetical move simulations can catch contradictions and score those lines as invalid

## Testing Requirements

The implementation pass should add automated tests covering at least:

1. Card uniqueness propagation
2. Player hand-size completion
3. Envelope singleton completion by category
4. Clause reduction from unknown shows
5. Contradiction detection
6. Knowledge base cloning isolation
7. Bot accusation only when fully solved
8. Bot suggestion determinism
9. Tie-breaking determinism
10. Move selection based on state reduction, not probability

Preferred test location:

- `tests/` package if added during implementation

## Acceptance Criteria

The bot is considered complete when all of the following are true:

- No production bot logic uses probability, Monte Carlo, or randomness.
- Every knowledge update triggers closure propagation.
- The knowledge base can be cloned and safely simulated.
- The bot accuses only when all three envelope cards are proven.
- Suggestion choice is deterministic and repeatable from the same state.
- Move scoring is derived only from measurable reduction in possible states.
- Existing game flow still runs without manual patching to core engine behavior.

## Implementation Plan

### Phase 1. Constraint Engine

- Refactor `clue_game/knowledge_base.py` into a public, cloneable, testable constraint engine.
- Add contradiction exception type.
- Add scoring metric snapshots.

### Phase 2. Deterministic Bot Policy

- Refactor `clue_game/bot.py` to remove stochastic logic.
- Implement legal suggestion generation.
- Implement one-step deterministic suggestion evaluation.
- Add lexicographic tie-breaking.

### Phase 3. Engine Compatibility

- Verify `clue_game/game.py` bot hooks still work.
- Remove or rewrite Monte Carlo simulation scripts.

### Phase 4. Verification

- Add tests for propagation and move choice.
- Run a quick deterministic simulation harness to ensure no runtime regressions.

## Open Design Decision

One detail from the original request needs to be made explicit before implementation: when evaluating a suggestion, the exact immediate outcome is not always uniquely determined from current knowledge.

This spec resolves that ambiguity by choosing:

- evaluate each suggestion by its minimum guaranteed immediate reduction across logically possible outcomes

If you want a different deterministic interpretation later, the main alternative is:

- evaluate by maximum possible reduction across logically possible outcomes

For implementation, the guaranteed-minimum interpretation is the safer and more faithful reading of "maximize deterministic reduction."

## Summary

The target system is a deterministic deduction engine, not a heuristic guesser. The upcoming implementation should primarily rewrite [`clue_game/knowledge_base.py`](clue_game/knowledge_base.py), [`clue_game/bot.py`](clue_game/bot.py), and Monte Carlo-related simulation code so the Clue bot behaves as a strict logical solver with one-step deterministic move selection.
