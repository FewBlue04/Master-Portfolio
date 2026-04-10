"""
Clue Game — Full Tkinter UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time

from engine.game import GameEngine
from engine.cards import (
    SUSPECTS, WEAPONS, ROOMS, ALL_CARDS, CARD_TYPE,
    SUSPECT_COLORS, WEAPON_ICONS
)

# ──────────────────────────────────────────────
# Color palette (dark luxury theme)
# ──────────────────────────────────────────────
BG_DARK    = "#0d0d0d"
BG_PANEL   = "#161616"
BG_CARD    = "#1e1e1e"
BG_HEADER  = "#111111"
GOLD       = "#c9a84c"
GOLD_LIGHT = "#e8c97d"
RED        = "#c0392b"
GREEN      = "#27ae60"
BLUE       = "#2980b9"
GREY       = "#555555"
TEXT_MAIN  = "#e8e0d0"
TEXT_DIM   = "#888888"
TEXT_GOLD  = "#c9a84c"
BORDER     = "#2a2a2a"
ACCENT     = "#8e1c1c"


def make_badge(parent, text, bg, fg=TEXT_MAIN, padx=8, pady=2):
    lbl = tk.Label(parent, text=text, bg=bg, fg=fg,
                   font=("Georgia", 9, "bold"), padx=padx, pady=pady,
                   relief="flat")
    return lbl


class ScrollableFrame(tk.Frame):
    """
    Scrollable container whose canvas is exposed so the app-level
    mousewheel router can drive it directly. No bindings here —
    all scroll routing is handled by ClueApp._on_mousewheel_route.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG_PANEL)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def scroll(self, units):
        self.canvas.yview_scroll(units, "units")


class SetupDialog(tk.Toplevel):
    """Setup window to choose player name and number of bots."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Clue — New Game")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)
        self.result = None

        self._build()
        self.grab_set()
        self.transient(parent)

    def _build(self):
        # Title
        tk.Label(self, text="🔍 CLUE", bg=BG_DARK, fg=GOLD,
                 font=("Georgia", 32, "bold")).pack(pady=(30, 4))
        tk.Label(self, text="THE MYSTERY GAME", bg=BG_DARK, fg=TEXT_DIM,
                 font=("Georgia", 11, "italic")).pack(pady=(0, 30))

        frame = tk.Frame(self, bg=BG_PANEL, padx=30, pady=30,
                         relief="flat", bd=1, highlightbackground=GOLD,
                         highlightthickness=1)
        frame.pack(padx=40, pady=0)

        tk.Label(frame, text="Your Name:", bg=BG_PANEL, fg=TEXT_MAIN,
                 font=("Georgia", 12)).grid(row=0, column=0, sticky="w", pady=8)
        self.name_var = tk.StringVar(value="Detective")
        entry = tk.Entry(frame, textvariable=self.name_var, bg=BG_CARD, fg=TEXT_MAIN,
                         insertbackground=GOLD, font=("Georgia", 12), width=18,
                         relief="flat", bd=4)
        entry.grid(row=0, column=1, padx=(12, 0), pady=8)

        tk.Label(frame, text="Number of Bots:", bg=BG_PANEL, fg=TEXT_MAIN,
                 font=("Georgia", 12)).grid(row=1, column=0, sticky="w", pady=8)
        self.bots_var = tk.IntVar(value=3)
        spin = tk.Spinbox(frame, from_=1, to=5, textvariable=self.bots_var,
                          bg=BG_CARD, fg=TEXT_MAIN, buttonbackground=BG_PANEL,
                          font=("Georgia", 12), width=5, relief="flat")
        spin.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=8)

        tk.Button(self, text="BEGIN INVESTIGATION",
                  bg=GOLD, fg=BG_DARK, activebackground=GOLD_LIGHT,
                  font=("Georgia", 13, "bold"), relief="flat",
                  padx=20, pady=10, cursor="hand2",
                  command=self._start).pack(pady=20)

    def _start(self):
        name = self.name_var.get().strip() or "Detective"
        bots = self.bots_var.get()
        self.result = (name, bots)
        self.destroy()


class ClueApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clue — Mystery Game")
        self.configure(bg=BG_DARK)
        self.geometry("1200x820")
        self.minsize(1000, 700)

        self.game = None
        self._pending_show_cards = []
        self._after_bot_id = None
        # Human manual notebook marks: card -> None | "no" | "yes"
        self.notebook_user_marks = {}

        self._show_setup()

    # ──────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────

    def _show_setup(self):
        dlg = SetupDialog(self)
        self.wait_window(dlg)
        if dlg.result is None:
            self.destroy()
            return
        name, bots = dlg.result
        self.game = GameEngine(human_name=name, num_bots=bots)
        self._build_main_ui()
        self._update_all()
        self._start_turn()

    def _build_main_ui(self):
        # Clear window
        for w in self.winfo_children():
            w.destroy()

        # ── Top bar ──
        topbar = tk.Frame(self, bg=BG_HEADER, height=48)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="🔍 CLUE", bg=BG_HEADER, fg=GOLD,
                 font=("Georgia", 18, "bold")).pack(side="left", padx=20)

        self.turn_label = tk.Label(topbar, text="", bg=BG_HEADER, fg=TEXT_DIM,
                                   font=("Georgia", 11, "italic"))
        self.turn_label.pack(side="left", padx=10)

        tk.Button(topbar, text="New Game", bg=GREY, fg=TEXT_MAIN,
                  relief="flat", font=("Georgia", 10), padx=10,
                  command=self._new_game, cursor="hand2").pack(side="right", padx=16, pady=8)

        # ── Main layout ──
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=10, pady=8)

        # Left: board + controls
        left = tk.Frame(main, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True)

        # Right: log + notebook
        right = tk.Frame(main, bg=BG_DARK, width=340)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        self._build_board(left)
        self._build_player_panel(left)
        self._build_action_panel(left)
        self._build_log_panel(right)
        self._build_notebook_panel(right)

        # Single root-level scroll router — handles notebook + log, no conflicts
        self.bind_all("<MouseWheel>", self._on_mousewheel_route)
        self.bind_all("<Button-4>",   self._on_mousewheel_route)
        self.bind_all("<Button-5>",   self._on_mousewheel_route)

    # ──────────────────────────────────────────────
    # Board
    # ──────────────────────────────────────────────

    def _build_board(self, parent):
        frame = tk.LabelFrame(parent, text=" MANSION MAP ", bg=BG_PANEL,
                              fg=GOLD, font=("Georgia", 10, "bold"),
                              bd=1, relief="solid", highlightbackground=GOLD)
        frame.pack(fill="both", expand=True, pady=(0, 6))

        self.board_canvas = tk.Canvas(frame, bg="#0a0a0a", highlightthickness=0)
        self.board_canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.board_canvas.bind("<Configure>", lambda e: self._draw_board())

    def _draw_board(self):
        c = self.board_canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10 or H < 10:
            return

        # 3x3 grid of rooms
        cols, rows = 3, 3
        pad = 8
        cell_w = (W - pad * 2) / cols
        cell_h = (H - pad * 2) / rows

        room_layout = [
            ["Kitchen",      "Ballroom",    "Conservatory"],
            ["Dining Room",  None,          "Billiard Room"],
            ["Lounge",       "Hall",        "Library"],  # note: Study added differently
        ]
        # Remap to actual 9 rooms in 3x3
        room_grid = [
            ["Kitchen",       "Ballroom",      "Conservatory"],
            ["Dining Room",   "Study",         "Billiard Room"],
            ["Lounge",        "Hall",          "Library"],
        ]

        player_rooms = self.game.get_player_rooms() if self.game else {}
        room_players = {}
        for pname, room in player_rooms.items():
            room_players.setdefault(room, []).append(pname)

        for r in range(rows):
            for col in range(cols):
                room = room_grid[r][col]
                x0 = pad + col * cell_w + 2
                y0 = pad + r * cell_h + 2
                x1 = x0 + cell_w - 4
                y1 = y0 + cell_h - 4

                # Room background
                is_human_here = player_rooms.get(self.game.human_name) == room if self.game else False
                fill = "#1a2a1a" if is_human_here else "#121212"
                outline = GOLD if is_human_here else BORDER

                c.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=2 if is_human_here else 1)

                # Room name
                c.create_text(
                    (x0 + x1) / 2, y0 + 18,
                    text=room.upper(), fill=GOLD if is_human_here else TEXT_DIM,
                    font=("Georgia", 8, "bold")
                )

                # Players in room
                plist = room_players.get(room, [])
                for pi, pname in enumerate(plist):
                    is_human = pname == (self.game.human_name if self.game else "")
                    eliminated = self.game.players[pname].eliminated if self.game else False
                    color = GOLD if is_human else (GREY if eliminated else BLUE)
                    label = "YOU" if is_human else pname[:5]
                    cx = x0 + 12 + (pi % 3) * 36
                    cy = y0 + 36 + (pi // 3) * 18
                    c.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=color, outline="")
                    c.create_text(cx, cy + 16, text=label, fill=color, font=("Georgia", 6))

    # ──────────────────────────────────────────────
    # Player panel (hand)
    # ──────────────────────────────────────────────

    def _build_player_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" YOUR HAND ", bg=BG_PANEL,
                              fg=GOLD, font=("Georgia", 10, "bold"),
                              bd=1, relief="solid")
        frame.pack(fill="x", pady=(0, 6))

        self.hand_frame = tk.Frame(frame, bg=BG_PANEL)
        self.hand_frame.pack(fill="x", padx=8, pady=6)

    def _update_hand(self):
        for w in self.hand_frame.winfo_children():
            w.destroy()
        if not self.game:
            return
        for card in self.game.get_human_cards():
            ctype = CARD_TYPE[card]
            colors = {"suspect": "#3a1a1a", "weapon": "#1a1a3a", "room": "#1a3a1a"}
            fg_c = {"suspect": "#e88", "weapon": "#88e", "room": "#8e8"}
            f = tk.Frame(self.hand_frame, bg=colors[ctype], padx=8, pady=4,
                         highlightbackground=BORDER, highlightthickness=1)
            f.pack(side="left", padx=4)
            icon = WEAPON_ICONS.get(card, "")
            tk.Label(f, text=f"{icon} {card}", bg=colors[ctype], fg=fg_c[ctype],
                     font=("Georgia", 9, "bold")).pack()
            tk.Label(f, text=ctype.upper(), bg=colors[ctype], fg=TEXT_DIM,
                     font=("Georgia", 7)).pack()

    # ──────────────────────────────────────────────
    # Action panel
    # ──────────────────────────────────────────────

    def _build_action_panel(self, parent):
        outer = tk.LabelFrame(parent, text=" ACTIONS ", bg=BG_PANEL,
                              fg=GOLD, font=("Georgia", 10, "bold"),
                              bd=1, relief="solid")
        outer.pack(fill="x")

        self.action_frame = tk.Frame(outer, bg=BG_PANEL)
        self.action_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.action_label = tk.Label(self.action_frame, text="", bg=BG_PANEL,
                                     fg=TEXT_MAIN, font=("Georgia", 10, "italic"),
                                     wraplength=600)
        self.action_label.pack()

        self.controls_frame = tk.Frame(self.action_frame, bg=BG_PANEL)
        self.controls_frame.pack(fill="x", pady=4)

    def _clear_controls(self):
        for w in self.controls_frame.winfo_children():
            w.destroy()

    # ──────────────────────────────────────────────
    # Log panel
    # ──────────────────────────────────────────────

    def _build_log_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" DETECTIVE LOG ", bg=BG_PANEL,
                              fg=GOLD, font=("Georgia", 10, "bold"),
                              bd=1, relief="solid")
        frame.pack(fill="both", expand=True, pady=(0, 6))

        self.log_text = tk.Text(frame, bg="#0a0a0a", fg=TEXT_MAIN,
                                font=("Courier", 9), state="disabled",
                                wrap="word", relief="flat",
                                padx=6, pady=6, height=18)
        sb = ttk.Scrollbar(frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

        # Tags
        self.log_text.tag_config("suggestion", foreground="#f0c040")
        self.log_text.tag_config("reveal",     foreground="#40c070")
        self.log_text.tag_config("nope",        foreground="#c04040")
        self.log_text.tag_config("alert",       foreground="#ff6030")
        self.log_text.tag_config("accusation",  foreground="#ff4040", font=("Courier", 9, "bold"))
        self.log_text.tag_config("win",         foreground="#ffd700", font=("Courier", 9, "bold"))
        self.log_text.tag_config("wrong",       foreground="#c04040")
        self.log_text.tag_config("info",        foreground=TEXT_DIM)
        self.log_text.tag_config("gameover",    foreground=RED, font=("Courier", 9, "bold"))

    def _update_log(self):
        if not self.game:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in self.game.log[-60:]:
            tag = entry.get("kind", "info")
            self.log_text.insert("end", entry["msg"] + "\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    # ──────────────────────────────────────────────
    # Detective Notebook panel
    # ──────────────────────────────────────────────

    def _build_notebook_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" DETECTIVE NOTEBOOK ", bg=BG_PANEL,
                              fg=GOLD, font=("Georgia", 10, "bold"),
                              bd=1, relief="solid")
        frame.pack(fill="both", expand=True)

        self.notebook_scroll = ScrollableFrame(frame, bg=BG_PANEL)
        self.notebook_scroll.pack(fill="both", expand=True)
        self.notebook_inner = self.notebook_scroll.inner

    def _toggle_user_mark(self, card):
        """Cycle human mark for a card: None -> 'no' -> 'yes' -> None."""
        current = self.notebook_user_marks.get(card)
        if current is None:
            self.notebook_user_marks[card] = 'no'
        elif current == 'no':
            self.notebook_user_marks[card] = 'yes'
        else:
            self.notebook_user_marks[card] = None
        self._update_notebook()

    def _update_notebook(self):
        for w in self.notebook_inner.winfo_children():
            w.destroy()
        if not self.game:
            return

        players = self.game.player_names  # ordered list
        human   = self.game.human_name
        human_cards = set(self.game.get_human_cards())

        # ── Column layout ──
        # col 0        : card name (fixed width)
        # col 1        : YOUR column (clickable toggle)
        # col 2..N     : one column per bot
        # We use grid on notebook_inner rows.

        COL_NAME  = 0
        COL_YOU   = 1                        # always col 1
        COL_BOTS  = {p: 2 + i              # bot name -> col index
                     for i, p in enumerate(p for p in players if p != human)}

        NAME_W = 16   # chars wide for card name label
        CELL_W = 3    # chars wide for each player cell

        # ── Header row: blank, YOU, Bot A, Bot B ... ──
        tk.Label(self.notebook_inner, text="", bg=BG_PANEL,
                 width=NAME_W).grid(row=0, column=COL_NAME, sticky="w", padx=(4,0))
        tk.Label(self.notebook_inner, text="YOU", bg=BG_PANEL, fg=GOLD,
                 font=("Georgia", 7, "bold"), width=CELL_W,
                 anchor="center").grid(row=0, column=COL_YOU, padx=1)
        for pname, col in COL_BOTS.items():
            abbr = pname[:4]   # "Bot A" -> "Bot " — trim to 4 chars
            tk.Label(self.notebook_inner, text=abbr, bg=BG_PANEL, fg=TEXT_DIM,
                     font=("Georgia", 7), width=CELL_W,
                     anchor="center").grid(row=0, column=col, padx=1)

        # ── Separator ──
        sep = tk.Frame(self.notebook_inner, bg=BORDER, height=1)
        sep.grid(row=1, column=0, columnspan=2 + len(COL_BOTS),
                 sticky="ew", pady=(0, 2), padx=4)

        # ── Card rows ──
        grid_row = 2
        for category, cards in [("SUSPECTS", SUSPECTS), ("WEAPONS", WEAPONS), ("ROOMS", ROOMS)]:

            # Category header spanning all columns
            cat_label = tk.Label(self.notebook_inner, text=f"─ {category} ─",
                                 bg=BG_PANEL, fg=GOLD, font=("Georgia", 8, "bold"),
                                 anchor="w")
            cat_label.grid(row=grid_row, column=0,
                           columnspan=2 + len(COL_BOTS),
                           sticky="ew", padx=4, pady=(6, 1))
            grid_row += 1

            for card in cards:
                icon    = WEAPON_ICONS.get(card, "")
                in_hand = card in human_cards

                # Card name
                name_fg   = GOLD if in_hand else TEXT_MAIN
                name_font = ("Georgia", 8, "bold") if in_hand else ("Georgia", 8)
                tk.Label(self.notebook_inner,
                         text=f"{icon} {card}",
                         bg=BG_PANEL, fg=name_fg, font=name_font,
                         width=NAME_W, anchor="w"
                         ).grid(row=grid_row, column=COL_NAME, sticky="w", padx=(4, 0))

                # ── YOUR column: clickable cycle toggle ──
                mark = self.notebook_user_marks.get(card)
                if in_hand:
                    # Always confirmed in your hand
                    sym, col_fg, relief = "■", GREEN, "flat"
                elif mark == 'yes':
                    sym, col_fg, relief = "■", GREEN, "flat"
                elif mark == 'no':
                    sym, col_fg, relief = "✕", RED, "flat"
                else:
                    sym, col_fg, relief = "·", GREY, "flat"

                def _make_toggle(c):
                    return lambda: self._toggle_user_mark(c)

                you_btn = tk.Button(
                    self.notebook_inner,
                    text=sym, fg=col_fg, bg=BG_PANEL,
                    activebackground=BG_CARD,
                    font=("Courier", 10, "bold"),
                    width=CELL_W, relief=relief, bd=0,
                    cursor="hand2" if not in_hand else "arrow",
                    command=_make_toggle(card) if not in_hand else (lambda: None)
                )
                you_btn.grid(row=grid_row, column=COL_YOU, padx=1)

                # ── Bot columns ──
                for pname, col in COL_BOTS.items():
                    player = self.game.players[pname]
                    val = player.kb.has_card.get((pname, card))
                    if val is True:
                        sym, col_fg = "■", GREEN
                    elif val is False:
                        sym, col_fg = "✕", GREY
                    else:
                        sym, col_fg = "?", TEXT_DIM

                    tk.Label(self.notebook_inner,
                             text=sym, bg=BG_PANEL, fg=col_fg,
                             font=("Courier", 10), width=CELL_W,
                             anchor="center"
                             ).grid(row=grid_row, column=col, padx=1)

                grid_row += 1

        # ── Footer legend ──
        legend_row = tk.Frame(self.notebook_inner, bg=BG_PANEL)
        legend_row.grid(row=grid_row, column=0,
                        columnspan=2 + len(COL_BOTS),
                        sticky="w", padx=4, pady=(8, 4))
        tk.Label(legend_row, text="Click YOUR column to mark cards",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Georgia", 7, "italic")).pack(side="left")

    def _on_mousewheel_route(self, event):
        """
        Root-level scroll router. Fires for every scroll event in the app.
        Walks the widget under the cursor upward to decide what to scroll:
          - If it is inside the notebook ScrollableFrame -> scroll the notebook canvas
          - If it is inside the log Text widget         -> scroll the log
          - Otherwise                                   -> do nothing
        This avoids all enter/leave timing problems and has zero conflict
        between the two scrollable areas.
        """
        # Resolve scroll delta uniformly across Windows / Linux
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))

        # Walk the widget tree from the widget currently under the cursor
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            # Hit the notebook scrollable canvas?
            if hasattr(self, 'notebook_scroll') and widget is self.notebook_scroll.canvas:
                self.notebook_scroll.scroll(delta)
                return
            # Hit any widget inside the notebook inner frame?
            if hasattr(self, 'notebook_scroll') and widget is self.notebook_scroll.inner:
                self.notebook_scroll.scroll(delta)
                return
            # Hit the log Text widget?
            if hasattr(self, 'log_text') and widget is self.log_text:
                self.log_text.yview_scroll(delta, "units")
                return
            try:
                widget = widget.master
            except Exception:
                break

    # ──────────────────────────────────────────────
    # Turn orchestration
    # ──────────────────────────────────────────────

    def _update_all(self):
        self._update_log()
        self._update_hand()
        self._update_notebook()
        self._draw_board()
        if self.game:
            cp = self.game.current_player_name
            self.turn_label.configure(text=f"Turn: {cp}")

    def _start_turn(self):
        if not self.game or self.game.game_over:
            self._show_game_over()
            return

        cp = self.game.current_player_name
        self.turn_label.configure(text=f"Turn: {cp}")

        if self.game.is_human_turn():
            self._human_turn()
        else:
            self.action_label.configure(text=f"⏳ {cp} is thinking...")
            self._clear_controls()
            # Delay bot turn for readability
            self._after_bot_id = self.after(800, self._run_bot_turn)

    def _run_bot_turn(self):
        if not self.game or self.game.game_over:
            self._show_game_over()
            return

        events = self.game.run_bot_turn()
        self._update_all()

        for ev in events:
            if ev.get("type") == "await_human_show":
                self._ask_human_to_show(ev)
                return

        if self.game.game_over:
            self._show_game_over()
            return

        self._start_turn()

    # ──────────────────────────────────────────────
    # Human turn
    # ──────────────────────────────────────────────

    def _human_turn(self):
        self._clear_controls()
        room = self.game.get_human_room()
        self.action_label.configure(
            text=f"Your turn! You are in the {room}. Make a suggestion or accusation."
        )

        btn_frame = self.controls_frame
        tk.Button(btn_frame, text="💬 Make Suggestion",
                  bg=GOLD, fg=BG_DARK, font=("Georgia", 11, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._suggestion_dialog).pack(side="left", padx=6)

        tk.Button(btn_frame, text="⚖️ Make Accusation",
                  bg=RED, fg=TEXT_MAIN, font=("Georgia", 11, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._accusation_dialog).pack(side="left", padx=6)

        tk.Button(btn_frame, text="🚶 Move Room",
                  bg=BG_CARD, fg=TEXT_MAIN, font=("Georgia", 11),
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._move_dialog).pack(side="left", padx=6)

    def _move_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Move to Room")
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text="Choose a room to move to:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 12)).pack(pady=12, padx=20)

        var = tk.StringVar(value=ROOMS[0])
        for room in ROOMS:
            rb = tk.Radiobutton(dlg, text=room, variable=var, value=room,
                                bg=BG_DARK, fg=TEXT_MAIN, selectcolor=BG_CARD,
                                activebackground=BG_DARK, font=("Georgia", 11))
            rb.pack(anchor="w", padx=30)

        def confirm():
            chosen = var.get()
            self.game.players[self.game.human_name].current_room = chosen
            dlg.destroy()
            self._update_all()
            self._human_turn()

        tk.Button(dlg, text="Move", bg=GOLD, fg=BG_DARK,
                  font=("Georgia", 11, "bold"), relief="flat", padx=14, pady=6,
                  command=confirm).pack(pady=14)

    def _suggestion_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Make a Suggestion")
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()
        dlg.transient(self)

        room = self.game.get_human_room()
        tk.Label(dlg, text=f"Suggestion in: {room}", bg=BG_DARK, fg=GOLD,
                 font=("Georgia", 13, "bold")).pack(pady=(16, 4), padx=20)
        tk.Label(dlg, text="Choose suspect and weapon:", bg=BG_DARK, fg=TEXT_DIM,
                 font=("Georgia", 10, "italic")).pack()

        form = tk.Frame(dlg, bg=BG_DARK)
        form.pack(padx=20, pady=12)

        tk.Label(form, text="Suspect:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).grid(row=0, column=0, sticky="w", pady=4)
        sus_var = tk.StringVar(value=SUSPECTS[0])
        sus_menu = ttk.Combobox(form, textvariable=sus_var, values=SUSPECTS,
                                state="readonly", width=20)
        sus_menu.grid(row=0, column=1, padx=8)

        tk.Label(form, text="Weapon:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).grid(row=1, column=0, sticky="w", pady=4)
        weap_var = tk.StringVar(value=WEAPONS[0])
        weap_menu = ttk.Combobox(form, textvariable=weap_var, values=WEAPONS,
                                 state="readonly", width=20)
        weap_menu.grid(row=1, column=1, padx=8)

        def confirm():
            s = sus_var.get()
            w = weap_var.get()
            r = room
            dlg.destroy()
            self._clear_controls()
            self.action_label.configure(text="Processing suggestion...")
            result = self.game.make_suggestion(self.game.human_name, s, w, r)
            self._update_all()
            self._handle_suggestion_result(result)

        tk.Button(dlg, text="Suggest!", bg=GOLD, fg=BG_DARK,
                  font=("Georgia", 12, "bold"), relief="flat", padx=16, pady=7,
                  command=confirm).pack(pady=14)

    def _handle_suggestion_result(self, result):
        if result.get("type") == "await_human_show":
            # This shouldn't happen when human is the asker asking about others
            # but handle it just in case
            self._after_human_suggestion_resolve()
        elif result.get("type") == "shown":
            card = result.get("card")
            shower = result.get("shower")
            if card:
                self.action_label.configure(
                    text=f"✅ {shower} showed you: {card}!")
            else:
                self.action_label.configure(
                    text=f"✅ {shower} showed a card to you.")
            self._update_all()
            self._after(2000, self._human_turn_done)
        elif result.get("type") == "no_refute":
            self.action_label.configure(
                text="🚨 Nobody could refute! The solution cards may be in the envelope!")
            self._update_all()
            self._after(2000, self._human_turn_done)
        else:
            self._human_turn_done()

    def _ask_human_to_show(self, ev):
        """Prompt human player to pick which card to show."""
        cards = ev["cards_can_show"]
        asker = ev["asker"]

        dlg = tk.Toplevel(self)
        dlg.title("Show a Card")
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text=f"{asker} made a suggestion.", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).pack(pady=(16, 4), padx=20)
        tk.Label(dlg, text="You can show one of these cards:", bg=BG_DARK, fg=GOLD,
                 font=("Georgia", 12, "bold")).pack()

        var = tk.StringVar(value=cards[0])
        for card in cards:
            rb = tk.Radiobutton(dlg, text=card, variable=var, value=card,
                                bg=BG_DARK, fg=TEXT_MAIN, selectcolor=BG_CARD,
                                activebackground=BG_DARK, font=("Georgia", 11))
            rb.pack(anchor="w", padx=30, pady=2)

        def confirm():
            chosen = var.get()
            dlg.destroy()
            result = self.game.human_shows_card(chosen)
            self._update_all()
            # Continue bot turn
            if not self.game.game_over:
                self.game.advance_turn()
                self._start_turn()
            else:
                self._show_game_over()

        tk.Button(dlg, text="Show Card", bg=GOLD, fg=BG_DARK,
                  font=("Georgia", 12, "bold"), relief="flat", padx=16, pady=7,
                  command=confirm).pack(pady=14)

    def _accusation_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Make an Accusation")
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()
        dlg.transient(self)

        tk.Label(dlg, text="⚖️ FINAL ACCUSATION", bg=BG_DARK, fg=RED,
                 font=("Georgia", 16, "bold")).pack(pady=(16, 4), padx=20)
        tk.Label(dlg, text="Warning: Wrong accusation = elimination!", bg=BG_DARK, fg=TEXT_DIM,
                 font=("Georgia", 9, "italic")).pack()

        form = tk.Frame(dlg, bg=BG_DARK)
        form.pack(padx=20, pady=12)

        tk.Label(form, text="Suspect:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).grid(row=0, column=0, sticky="w", pady=4)
        sus_var = tk.StringVar(value=SUSPECTS[0])
        ttk.Combobox(form, textvariable=sus_var, values=SUSPECTS,
                     state="readonly", width=20).grid(row=0, column=1, padx=8)

        tk.Label(form, text="Weapon:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).grid(row=1, column=0, sticky="w", pady=4)
        weap_var = tk.StringVar(value=WEAPONS[0])
        ttk.Combobox(form, textvariable=weap_var, values=WEAPONS,
                     state="readonly", width=20).grid(row=1, column=1, padx=8)

        tk.Label(form, text="Room:", bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Georgia", 11)).grid(row=2, column=0, sticky="w", pady=4)
        room_var = tk.StringVar(value=ROOMS[0])
        ttk.Combobox(form, textvariable=room_var, values=ROOMS,
                     state="readonly", width=20).grid(row=2, column=1, padx=8)

        def confirm():
            s = sus_var.get()
            w = weap_var.get()
            r = room_var.get()
            dlg.destroy()
            result = self.game.make_accusation(self.game.human_name, s, w, r)
            self._update_all()
            if result["type"] == "correct":
                self._show_game_over()
            elif result["type"] == "wrong":
                if self.game.game_over:
                    self._show_game_over()
                else:
                    self.action_label.configure(text="💀 Wrong accusation! You are eliminated.")
                    self.game.advance_turn()
                    self._after(1500, self._start_turn)

        tk.Button(dlg, text="Accuse!", bg=RED, fg=TEXT_MAIN,
                  font=("Georgia", 12, "bold"), relief="flat", padx=16, pady=7,
                  command=confirm).pack(pady=14)

    def _human_turn_done(self):
        if self.game and not self.game.game_over:
            self.game.advance_turn()
            self._start_turn()

    def _after_human_suggestion_resolve(self):
        if self.game and not self.game.game_over:
            self.game.advance_turn()
            self._start_turn()

    # ──────────────────────────────────────────────
    # Game over
    # ──────────────────────────────────────────────

    def _show_game_over(self):
        self._update_all()
        self._clear_controls()
        if not self.game:
            return

        sol = self.game.solution
        winner = self.game.winner
        human = self.game.human_name

        if winner == human:
            msg = f"🏆 YOU WIN!\n\nSolution: {sol['suspect']} · {sol['weapon']} · {sol['room']}"
            color = GOLD
        elif winner:
            msg = f"💀 {winner} solved the case!\n\nSolution: {sol['suspect']} · {sol['weapon']} · {sol['room']}"
            color = RED
        else:
            msg = f"💀 All players eliminated.\n\nSolution: {sol['suspect']} · {sol['weapon']} · {sol['room']}"
            color = GREY

        self.action_label.configure(text=msg, fg=color, font=("Georgia", 12, "bold"))
        tk.Button(self.controls_frame, text="Play Again", bg=GOLD, fg=BG_DARK,
                  font=("Georgia", 12, "bold"), relief="flat", padx=14, pady=6,
                  command=self._new_game).pack()

    def _new_game(self):
        if self._after_bot_id:
            self.after_cancel(self._after_bot_id)
        self.game = None
        self._show_setup()

    def _after(self, ms, fn):
        """Wrapper so we can track pending after calls."""
        self._after_bot_id = self.after(ms, fn)


def main():
    app = ClueApp()
    app.mainloop()


if __name__ == "__main__":
    main()