# Clue — Luxury Noir (Python / Tkinter)

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

## License

Specify a license in the repo root when publishing (e.g. MIT), if applicable.
