# Clue — (Python / Tkinter)

Single-player Clue-style game against AI bots: a **constraint-based knowledge engine**, deterministic bot policy, and a **Tkinter** UI (“Luxury Noir” theme).

## Requirements

- Python **3.10+**
- **Running the game** uses only the Python standard library (no `pip install` required).
- **Running tests** requires [pytest](https://pytest.org/) (see Development).

## Run

From this directory:

```bash
python main.py
```

`main.py` adds the project root to `sys.path` and starts the UI via `clue_game.app`.

## Tests

```bash
python -m pytest tests -q
```

Run this after changes to the engine, bot, or knowledge base. If you add continuous integration (e.g. GitHub Actions), use the same command there so local checks match CI.

## Imports

All application code lives in the **`clue_game`** package. Examples:

- `from clue_game.game import GameEngine`
- `from clue_game.bot import BotPlayer`
- `from clue_game.cards import ROOMS, SUSPECTS`

Scripts at the project root (`main.py`, `simulate.py`) add the root to `sys.path` so `clue_game` resolves when you run them from this folder.

## Layout

| Area | Role |
|------|------|
| `clue_game/` | Single package: game rules, cards/constants, bot, knowledge base, state tracker, Tk UI |
| `clue_game/app.py` | Tk UI (`ClueApp`) |
| `clue_game/game.py` | Rules engine (`GameEngine`), event log |
| `clue_game/bot.py` / `clue_game/knowledge_base.py` | Bot policy and CSP-style deductions |
| `clue_game/cards.py` | Suspects, weapons, rooms, map adjacency |
| `main.py` | Entry point |
| `simulate.py` | Headless trials for bot evaluation |
| `docs/clue-bot-engineering-spec.md` | Design notes |

## Development (optional)

Install dev tools (once per environment):

```bash
pip install -e ".[dev]"
```

Or minimal installs:

```bash
pip install pytest ruff
```

- **Format / lint** (consistent style and common mistakes):

  ```bash
  python -m ruff format .
  python -m ruff check .
  ```

  (`python -m` avoids PATH issues on Windows if `ruff` is not on your shell path.) Settings live in `pyproject.toml`.

- **Tests** — same as [Tests](#tests) above.

# Clue2 Documentation

This directory contains comprehensive documentation for the Clue2 project, a sophisticated implementation of the classic Clue board game featuring constraint-based AI and a themed user interface.

## Documentation Structure

### Core Documentation

- **[architecture-spec.md](./architecture-spec.md)** - Complete system architecture overview
- **[features-spec.md](./features-spec.md)** - Detailed feature specifications
- **[propositional-logic-spec.md](./propositional-logic-spec.md)** - AI logic and reasoning concepts

### Quick Reference

#### Architecture Overview
- **Game Engine**: Central rules enforcement and turn management
- **Knowledge Base**: Constraint satisfaction problem solver
- **Bot AI**: Deterministic one-step lookahead evaluation
- **User Interface**: Luxury Noir themed Tkinter application
- **State Tracking**: Append-only event history system

#### Key Concepts
- **Propositional Logic**: Boolean constraint matrix for card knowledge
- **Logical Propagation**: Iterative inference to logical closure
- **Minimax Reasoning**: Worst-case opponent response evaluation
- **Information Pressure**: Targeting high-uncertainty cards
- **Constraint Satisfaction**: CSP solver with multiple rule types

#### AI Features
- **Constraint-Based Deduction**: Automatic logical inference
- **One-Step Lookahead**: Simulate all possible response outcomes
- **Strategic Planning**: Balance exploration vs exploitation
- **Escape Mechanisms**: Avoid local optima and suggestion loops
- **Safe Accusations**: Only accuse when solution is certain

#### User Interface
- **Luxury Noir Theme**: Sophisticated dark color scheme
- **Interactive Board**: Room visualization with player positions
- **Detective Notebook**: Knowledge tracking with user marks
- **Event Logging**: Color-coded game history
- **Responsive Controls**: Intuitive suggestion and accusation dialogs

## Getting Started

### For Developers
1. Read the [architecture specification](./architecture-spec.md) to understand the system design
2. Review the [propositional logic documentation](./propositional-logic-spec.md) for AI concepts
3. Examine the [features specification](./features-spec.md) for implementation details

### For Users
1. Refer to the [features specification](./features-spec.md) for available functionality
2. Check the UI sections for interface navigation and controls
3. Review the AI sections for understanding bot behavior

### For Researchers
1. Study the [propositional logic specification](./propositional-logic-spec.md) for logical foundations
2. Examine the constraint satisfaction implementation details
3. Review the AI decision-making algorithms and evaluation functions

## Technical Deep Dives

### Knowledge Base System
The constraint satisfaction problem solver implements:
- Boolean matrix representation of card ownership
- Five core inference rules for logical propagation
- Contradiction detection and consistency checking
- Disjunctive clause handling for unknown card shows

### Bot Decision Making
The AI system features:
- Minimax evaluation with worst-case reasoning
- Information-theoretic scoring functions
- Adaptive behavior with progress tracking
- Escape mechanisms for avoiding local optima

### User Interface Design
The Tkinter interface provides:
- Component-based architecture with clear separation
- Event-driven updates from game engine
- Responsive layout with customizable panels
- Accessibility features and keyboard navigation

## Implementation Notes

### Code Organization
```
clue_game/
|
+-- app.py              # User interface and event handling
+-- game.py             # Game engine and rules enforcement
+-- bot.py              # AI decision making and strategy
+-- knowledge_base.py   # Constraint satisfaction solver
+-- cards.py            # Game constants and board layout
+-- state_tracker.py    # Event history and game logging
```

### Key Design Patterns
- **Observer Pattern**: UI updates from game events
- **Strategy Pattern**: Pluggable AI decision algorithms
- **State Pattern**: Game state management and turn flow
- **Command Pattern**: User action handling and undo support

### Performance Considerations
- Lazy evaluation for constraint propagation
- Incremental updates to avoid recomputation
- Efficient data structures for knowledge representation
- Async operations for responsive UI

## Extending the System

### Adding New Features
1. Review the architecture documentation for integration points
2. Follow the modular design patterns for new components
3. Ensure compatibility with existing constraint system
4. Update tests and documentation

### Modifying AI Behavior
1. Understand the propositional logic foundation
2. Modify evaluation functions in the bot module
3. Test with simulation framework
4. Update AI documentation accordingly

### Customizing UI
1. Review the component hierarchy in app.py
2. Modify color schemes and styling constants
3. Ensure accessibility compliance
4. Update feature documentation

## Testing and Validation

### Test Coverage
- Unit tests for individual modules
- Integration tests for component interactions
- Simulation tests for end-to-end scenarios
- Property tests for invariant verification

### Quality Assurance
- Consistency checking for knowledge base
- Contradiction detection for logical validity
- Performance monitoring for AI decisions
- User experience testing for interface

This documentation provides a comprehensive understanding of the Clue2 system, from high-level architecture to detailed implementation concepts.
