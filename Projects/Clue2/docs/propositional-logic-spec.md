# Propositional Logic and AI Concepts in Clue2

## Overview

Clue2 implements a constraint satisfaction problem (CSP) solver using propositional logic for AI decision-making. This document covers the logical foundations, inference mechanisms, and AI concepts.

## Propositional Logic Foundation

### Boolean Variables

```
has_card(entity, card) = {
    True: Entity definitely has card
    False: Entity definitely does not have card
    None: Card ownership unknown
}
```

### Logical Domains
- **Players**: Human + bot players
- **Cards**: 21 total (6 suspects, 6 weapons, 9 rooms)
- **Envelope**: Special entity for solution cards
- **Variables**: `(entity, card)` pairs for each combination

### Truth Assignment Matrix
```
           | Card1 | Card2 | ... | Card21
-----------+-------+------+-----+--------
Player1    |  T/F  |  T/F  |     |  T/F
Player2    |  T/F  |  T/F  |     |  T/F
...
Envelope   |  T/F  |  T/F  |     |  T/F
```

## Constraint Satisfaction Problem (CSP)

### CSP Definition
1. **Variables**: Boolean matrix entries
2. **Domains**: `{True, False, None}` for each variable
3. **Constraints**: Logical rules governing valid assignments

### Constraint Types

#### Unary Constraints
- Initial knowledge: Cards dealt to each player
- Envelope rules: Exactly one card per category

#### Binary Constraints
- Card uniqueness: Each card owned by exactly one entity
- Mutual exclusion: Cannot have multiple cards when hand full

#### Global Constraints
- Hand size limits: Exact dealt card count per player
- Solution completeness: One card per category in envelope

#### Disjunctive Constraints
- At-least-one clauses from observed card shows:
```
has_card(Player, Card1) OR has_card(Player, Card2) OR has_card(Player, Card3)
```

## Inference Rules and Logical Propagation

### Rule 1: Card Uniqueness
**Logic**: If card's owner confirmed, eliminate all other owners
```
IF has_card(owner, card) = True
THEN for all other entities e: has_card(e, card) = False
```

### Rule 2: Singleton Assignment
**Logic**: If only one possible owner remains, assign the card
```
IF possible_owners(card) = {entity}
THEN has_card(entity, card) = True
```

### Rule 3: Player Card Limits
**Logic**: Enforce exact hand sizes using counting arguments
```
IF confirmed_cards(player) = hand_size(player)
THEN for all unknown cards c: has_card(player, c) = False

IF unknown_cards(player) = remaining_slots(player)
THEN for all unknown cards c: has_card(player, c) = True
```

### Rule 4: Clause Reduction
**Logic**: Remove impossible cards from disjunctive clauses
```
IF has_card(player, card) = False
THEN remove card from (player, {card1, card2, card3}) clause

IF clause reduces to single card
THEN assign that card to player
```

### Rule 5: Envelope Category Rules
**Logic**: Enforce exactly-one-per-category constraint
```
IF has_card(ENVELOPE, card) = True
THEN for all other cards in same category: has_card(ENVELOPE, other_card) = False

IF only one candidate remains in category
THEN assign that card to envelope
```

## Logical Closure Algorithm

### Propagation to Fixed Point
System iteratively applies inference rules until no new deductions:

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
- **Monotonic**: Knowledge only increases
- **Finite**: Maximum 3-state assignments per variable
- **Complete**: Reaches logical closure in finite steps
- **Sound**: All deductions are logically valid

## AI Decision-Making Concepts

### One-Step Lookahead Evaluation
Bot evaluates moves by simulating all possible response outcomes:

```python
def evaluate_move(self, move, responder_order):
    baseline = self.kb.snapshot_metrics()
    outcome_scores = []
    
    for branch in self._enumerate_outcomes(move, responder_order):
        outcome_scores.append(branch.score_delta(baseline))
    
    return min(outcome_scores)  # Minimax: assume worst case
```

### Minimax Reasoning
**Concept**: Opponents respond to minimize information gain

**Implementation**:
1. Enumerate outcomes for each responder and possible card
2. Simulate knowledge with hypothetical constraints
3. Score information improvement
4. Select move with best worst-case outcome

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

## Game Theory Concepts

### Zero-Sum Game
- Players compete for limited information
- Payoff: Knowledge gain vs. opponent information concealment
- Strategy: Balance exploration vs. exploitation

### Nash Equilibrium
- Bot strategy optimal given opponent strategies
- Information hiding minimizes revealed information
- Strategic card selection

## Search and Optimization

### Move Space Exploration
- Legal moves: All reachable room × suspect × weapon combinations
- Pruning eliminates suboptimal moves
- Composite function evaluation

### Escape Mechanisms
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
System detects impossible states through consistency checking:
- Each card must have at least one possible owner
- Players must be able to reach required hand size

### Logical Entropy
Entropy-like measures evaluate uncertainty:
```
Entropy = -sum(p_i * log(p_i) for all possible assignments)
```

### Bayesian Inference
System follows Bayesian principles:
- Prior probabilities: Uniform distribution over solutions
- Evidence: Card shows and no-shows provide information
- Posterior updates: Constraint propagation updates beliefs
- Decision theory: Maximize expected information gain

## Computational Complexity

### Worst-Case Analysis
- Variables: O(n × m) where n = players, m = cards
- Constraints: O(n × m + n + m) for all constraint types
- Propagation: O(k × (n × m)) where k = iterations to closure
- Move evaluation: O(r × s × n × m) where r = responders, s = suggestions

### Optimization Techniques
- Lazy evaluation when new information arrives
- Incremental updates tracking changes
- Early termination when no changes occur
- Memoization of expensive computations

## Practical Applications

### Deduction Examples

#### Card Uniqueness
```
Given: has_card(Player1, Knife) = True
Deduce: has_card(Player2, Knife) = False
        has_card(Player3, Knife) = False
        has_card(ENVELOPE, Knife) = False
```

#### Hand Size Limit
```
Given: Player1 has 3 cards, confirmed: {Knife, Rope}
        Unknown cards: {Candlestick, Revolver}
Deduce: Player1 must have exactly one of {Candlestick, Revolver}
```

#### Clause Reduction
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
- Probabilistic reasoning with probability distributions
- Fuzzy logic for uncertainty with degrees of belief
- Temporal logic reasoning about information over time
- Modal logic modeling knowledge about others' knowledge

### Alternative AI Approaches
- Monte Carlo Tree Search simulating many possible games
- Neural networks learning patterns from game data
- Reinforcement learning optimizing through self-play
- Expert systems with rule-based deduction

This logical foundation provides Clue2 with a robust, mathematically sound approach to playing Clue effectively while maintaining explainable and verifiable AI behavior.
