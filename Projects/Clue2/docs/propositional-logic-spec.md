# Propositional Logic and AI Concepts in Clue2

## Overview

Clue2 implements a sophisticated constraint satisfaction problem (CSP) solver using propositional logic to power its AI decision-making. This document details the logical foundations, inference mechanisms, and AI concepts that enable the bot to play Clue effectively.

## Propositional Logic Foundation

### Boolean Variables

The knowledge base represents the game state using Boolean variables:

```
has_card(entity, card) = {
    True: Entity definitely has the card
    False: Entity definitely does not have the card
    None: Card ownership is unknown
}
```

Where `entity` includes all players plus the special `ENVELOPE` entity representing the murder solution.

### Logical Domains

- **Players**: Human player + bot players
- **Cards**: 21 total cards (6 suspects, 6 weapons, 9 rooms)
- **Envelope**: Special entity holding the solution cards
- **Variables**: `(entity, card)` pairs for each combination

### Truth Assignment Matrix

```
           | Card1 | Card2 | Card3 | ... | Card21
-----------+-------+-------+-------+-----+--------
Player1    |  T/F  |  T/F  |  T/F  |     |  T/F
Player2    |  T/F  |  T/F  |  T/F  |     |  T/F
...
Envelope   |  T/F  |  T/F  |  T/F  |     |  T/F
```

## Constraint Satisfaction Problem (CSP)

### CSP Definition

A CSP consists of:
1. **Variables**: The Boolean matrix entries
2. **Domains**: `{True, False, None}` for each variable
3. **Constraints**: Logical rules governing valid assignments

### Constraint Types

#### 1. Unary Constraints
- **Initial Knowledge**: Cards dealt to each player
- **Envelope Rules**: Exactly one card per category in envelope

#### 2. Binary Constraints
- **Card Uniqueness**: Each card owned by exactly one entity
- **Mutual Exclusion**: If entity has card A, cannot have card B (when hand full)

#### 3. Global Constraints
- **Hand Size Limits**: Each player has exactly their dealt card count
- **Solution Completeness**: Envelope contains exactly one of each category

#### 4. Disjunctive Constraints
- **At-Least-One Clauses**: From observed card shows
```
has_card(Player, Card1) OR has_card(Player, Card2) OR has_card(Player, Card3)
```

## Inference Rules and Logical Propagation

### Rule 1: Card Uniqueness
**Logic**: If a card's owner is confirmed, eliminate all other owners

```
IF has_card(owner, card) = True
THEN for all other entities e: has_card(e, card) = False
```

**Implementation**: 
```python
def _apply_card_uniqueness(self):
    changed = False
    for card in ALL_CARDS:
        owner = self._confirmed_owner(card)
        if owner is not None:
            for entity in self.entities:
                if entity != owner:
                    changed |= self._assign(entity, card, False)
    return changed
```

### Rule 2: Singleton Assignment
**Logic**: If only one possible owner remains, assign the card

```
IF possible_owners(card) = {entity}
THEN has_card(entity, card) = True
```

**Implementation**:
```python
def _apply_singleton_assignments(self):
    changed = False
    for card in ALL_CARDS:
        owner = self._confirmed_owner(card)
        if owner is None:
            possible_owners = self.get_possible_owners(card)
            if len(possible_owners) == 1:
                changed |= self._assign(next(iter(possible_owners)), card, True)
    return changed
```

### Rule 3: Player Card Limits
**Logic**: Enforce exact hand sizes using counting arguments

```
IF confirmed_cards(player) = hand_size(player)
THEN for all unknown cards c: has_card(player, c) = False

IF unknown_cards(player) = remaining_slots(player)
THEN for all unknown cards c: has_card(player, c) = True
```

**Implementation**:
```python
def _apply_player_card_limits(self):
    changed = False
    for player in self.player_names:
        confirmed = [card for card in ALL_CARDS if self.has_card[(player, card)] is True]
        unknown = [card for card in ALL_CARDS if self.has_card[(player, card)] is None]
        remaining = self.num_cards_per_player[player] - len(confirmed)
        
        if remaining == 0:
            for card in unknown:
                changed |= self._assign(player, card, False)
        elif remaining == len(unknown):
            for card in unknown:
                changed |= self._assign(player, card, True)
    return changed
```

### Rule 4: Clause Reduction
**Logic**: Remove impossible cards from disjunctive clauses

```
IF has_card(player, card) = False
THEN remove card from (player, {card1, card2, card3}) clause

IF clause reduces to single card
THEN assign that card to player
```

**Implementation**:
```python
def _apply_clause_reduction(self):
    changed = False
    reduced_clauses = []
    
    for entity, cards in self.clauses:
        remaining = {card for card in cards if self.has_card[(entity, card)] is not False}
        
        if not remaining:
            raise ContradictionError(f"Unsatisfied clause for {entity}")
        
        if any(self.has_card[(entity, card)] is True for card in remaining):
            continue  # Clause already satisfied
        
        if len(remaining) == 1:
            changed |= self._assign(entity, next(iter(remaining)), True)
        else:
            reduced_clauses.append((entity, frozenset(remaining)))
    
    self.clauses = reduced_clauses
    return changed
```

### Rule 5: Envelope Category Rules
**Logic**: Enforce exactly-one-per-category constraint

```
IF has_card(ENVELOPE, card) = True
THEN for all other cards in same category: has_card(ENVELOPE, other_card) = False

IF only one candidate remains in category
THEN assign that card to envelope
```

**Implementation**:
```python
def _apply_envelope_category_rules(self):
    changed = False
    
    for category, cards in CATEGORIES.items():
        true_cards = [card for card in cards if self.has_card[(ENVELOPE, card)] is True]
        
        if len(true_cards) > 1:
            raise ContradictionError(f"Envelope has multiple {category} cards")
        
        if len(true_cards) == 1:
            # Eliminate all others in category
            true_card = true_cards[0]
            for card in cards:
                if card != true_card:
                    changed |= self._assign(ENVELOPE, card, False)
        else:
            # Check if only one candidate remains
            candidates = [card for card in cards if self.has_card[(ENVELOPE, card)] is not False]
            if len(candidates) == 1:
                changed |= self._assign(ENVELOPE, candidates[0], True)
    
    return changed
```

## Logical Closure Algorithm

### Propagation to Fixed Point

The system iteratively applies inference rules until no new deductions can be made:

```python
def propagate(self):
    changed = True
    while changed:
        changed = False
        changed |= self._apply_card_uniqueness()
        changed |= self._apply_singleton_assignments()
        changed |= self._apply_player_card_limits()
        changed |= self._apply_clause_reduction()
        changed |= self._apply_envelope_category_rules()
        self._check_consistency()
```

### Convergence Properties

- **Monotonic**: Knowledge only increases, never decreases
- **Finite**: Maximum of 3-state assignments per variable
- **Complete**: Reaches logical closure in finite steps
- **Sound**: All deductions are logically valid

## AI Decision-Making Concepts

### One-Step Lookahead Evaluation

The bot evaluates moves by simulating all possible response outcomes:

```python
def evaluate_move(self, move, responder_order):
    baseline = self.kb.snapshot_metrics()
    outcome_scores = []
    
    for branch in self._enumerate_outcomes(move, responder_order):
        outcome_scores.append(branch.score_delta(baseline))
    
    return min(outcome_scores)  # Minimax: assume worst case
```

### Minimax Reasoning

**Concept**: Assume opponents will respond in ways that minimize our information gain

**Implementation**:
1. **Enumerate Outcomes**: For each possible responder and card they could show
2. **Simulate Knowledge**: Apply hypothetical constraints
3. **Score Information**: Calculate knowledge improvement
4. **Select Worst Case**: Choose move with best worst-case outcome

### Information Theory Metrics

#### Knowledge Scoring Function

```python
def score_delta(self, before_metrics):
    after = self.snapshot_metrics()
    return (
        before_metrics["total_possible_owners"] - after["total_possible_owners"] +
        after["confirmed_assignments"] - before_metrics["confirmed_assignments"] +
        before_metrics["envelope_candidate_total"] - after["envelope_candidate_total"] +
        before_metrics["unresolved_clauses"] - after["unresolved_clauses"]
    )
```

#### Information Pressure

Prioritizes moves targeting high-uncertainty cards:

```python
def _information_pressure(self, move):
    suspect, weapon, room = move
    pressure = 0
    
    for card in (suspect, weapon, room):
        possible_owners = len(self.kb.get_possible_owners(card))
        pressure += max(0, len(self.kb.entities) - possible_owners)
        
        category = self._get_category(card)
        if card in self.kb.get_envelope_candidates(category):
            pressure += 1
    
    return pressure
```

### Game Theory Concepts

#### Zero-Sum Game
- **Players**: Competing for limited information
- **Payoff**: Knowledge gain vs. opponent information concealment
- **Strategy**: Balance exploration (learning) vs. exploitation (winning)

#### Nash Equilibrium
- **Bot Strategy**: Optimal given opponent strategies
- **Information Hiding**: Minimize information revealed to opponents
- **Card Selection**: Choose cards to show strategically

### Search and Optimization

#### Move Space Exploration
- **Legal Moves**: All reachable room × suspect × weapon combinations
- **Pruning**: Eliminate obviously suboptimal moves
- **Evaluation**: Score each move using composite function

#### Escape Mechanisms
When stuck in local optima:

```python
def _apply_escape_rule(self, candidates, recent_suggestions, no_progress_streak):
    if no_progress_streak < 3:
        return candidates
    
    recent_set = set(recent_suggestions)
    fresh_candidates = [
        candidate for candidate in candidates 
        if candidate["move"] not in recent_set
    ]
    return fresh_candidates or candidates
```

## Advanced Logical Concepts

### Contradiction Detection

The system detects impossible states through consistency checking:

```python
def _check_consistency(self):
    # Each card must have at least one possible owner
    for card in ALL_CARDS:
        if not self.get_possible_owners(card):
            raise ContradictionError(f"{card} has no possible owner")
    
    # Players must be able to reach required hand size
    for player in self.player_names:
        confirmed = sum(1 for card in ALL_CARDS if self.has_card[(player, card)] is True)
        possible = sum(1 for card in ALL_CARDS if self.has_card[(player, card)] is not False)
        required = self.num_cards_per_player[player]
        
        if confirmed > required or possible < required:
            raise ContradictionError(f"{player} hand size inconsistency")
```

### Logical Entropy

The system uses entropy-like measures to evaluate uncertainty:

```
Entropy = -sum(p_i * log(p_i) for all possible assignments)
```

Where `p_i` represents the probability of each possible world state.

### Bayesian Inference

While not explicitly implemented, the system follows Bayesian principles:

- **Prior Probabilities**: Uniform distribution over possible solutions
- **Evidence**: Card shows and no-shows provide information
- **Posterior Updates**: Constraint propagation updates beliefs
- **Decision Theory**: Choose moves maximizing expected information gain

## Computational Complexity

### Worst-Case Analysis

- **Variables**: O(n × m) where n = players, m = cards
- **Constraints**: O(n × m + n + m) for all constraint types
- **Propagation**: O(k × (n × m)) where k = iterations to closure
- **Move Evaluation**: O(r × s × n × m) where r = responders, s = suggestions

### Optimization Techniques

- **Lazy Evaluation**: Only propagate when new information arrives
- **Incremental Updates**: Track changes to avoid recomputation
- **Early Termination**: Stop when no changes occur
- **Memoization**: Cache expensive computations

## Practical Applications

### Deduction Examples

#### Example 1: Card Uniqueness
```
Given: has_card(Player1, Knife) = True
Deduce: has_card(Player2, Knife) = False
        has_card(Player3, Knife) = False
        has_card(ENVELOPE, Knife) = False
```

#### Example 2: Hand Size Limit
```
Given: Player1 has 3 cards, confirmed: {Knife, Rope}
        Unknown cards: {Candlestick, Revolver}
Deduce: Player1 must have exactly one of {Candlestick, Revolver}
```

#### Example 3: Clause Reduction
```
Given: has_card(Player2, {Knife, Rope, Candlestick}) clause
        has_card(Player2, Knife) = False
        has_card(Player2, Rope) = False
Deduce: has_card(Player2, Candlestick) = True
```

### Strategic Decision Making

#### Information Maximization
- Target cards with many possible owners
- Prefer rooms with high uncertainty
- Balance between learning different card categories

#### Risk Management
- Avoid accusations without certainty
- Consider opponent knowledge states
- Plan for future information needs

## Extensions and Variations

### Advanced Logic Extensions

- **Probabilistic Reasoning**: Add probability distributions
- **Fuzzy Logic**: Handle uncertainty with degrees of belief
- **Temporal Logic**: Reason about information over time
- **Modal Logic**: Model knowledge about others' knowledge

### Alternative AI Approaches

- **Monte Carlo Tree Search**: Simulate many possible games
- **Neural Networks**: Learn patterns from game data
- **Reinforcement Learning**: Optimize through self-play
- **Expert Systems**: Rule-based deduction systems

This logical foundation provides Clue2 with a robust, mathematically sound approach to playing Clue effectively while maintaining explainable and verifiable AI behavior.
