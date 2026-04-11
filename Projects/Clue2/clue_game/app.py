"""
Clue Game - Luxury Noir Tkinter UI.
"""

import tkinter as tk
from tkinter import ttk

from .cards import CARD_TYPE, ROOMS, SUSPECTS, WEAPONS
from .game import GameEngine

BG_DARK = "#090807"
BG_HEADER = "#0f0d0b"
BG_PANEL = "#16120f"
BG_PANEL_ALT = "#1e1814"
BG_CARD = "#241d18"
BG_CANVAS = "#0b0908"
GOLD = "#c9a84c"
GOLD_LIGHT = "#edd38a"
INK = "#f2ead9"
TEXT_MAIN = "#e4dac4"
TEXT_DIM = "#93856e"
RED = "#b65145"
GREEN = "#71b784"
BLUE = "#7ea6c7"
GREY = "#6e655a"
BORDER = "#322821"

CARD_PALETTE = {
    "suspect": {"bg": "#351a19", "fg": "#f0b4aa", "label": "SUSPECT"},
    "weapon": {"bg": "#1b2234", "fg": "#bcc8f0", "label": "WEAPON"},
    "room": {"bg": "#1b3123", "fg": "#b3d8ba", "label": "ROOM"},
}

ROOM_STYLES = {
    "Kitchen": {"fill": "#22352a", "accent": "#93d0a0"},
    "Ballroom": {"fill": "#2d2134", "accent": "#dcb7ff"},
    "Conservatory": {"fill": "#1d342d", "accent": "#9ce0c9"},
    "Dining Room": {"fill": "#35211d", "accent": "#dfb494"},
    "Billiard Room": {"fill": "#233128", "accent": "#8bc6aa"},
    "Library": {"fill": "#2a2f1d", "accent": "#c7d5a0"},
    "Study": {"fill": "#241f2c", "accent": "#c9b3ef"},
    "Hall": {"fill": "#2f251f", "accent": "#e6c898"},
    "Lounge": {"fill": "#3a1e24", "accent": "#f0a5b5"},
}

NOTEBOOK_GLYPHS = {
    "yes": "◆",
    "no": "×",
    "unknown": "·",
}


class ScrollableFrame(tk.Frame):
    """Vertical scroll area: canvas + inner frame whose width tracks content (no horizontal stretch)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG_PANEL, highlightthickness=0)
        self.inner = tk.Frame(self.canvas, bg=BG_PANEL)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._inner_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(fill="both", expand=True)

    def _sync_inner_window_width(self):
        """Keep embedded frame at content width so grid columns don't stretch with the canvas."""
        self.canvas.update_idletasks()
        w = max(self.inner.winfo_reqwidth(), 1)
        self.canvas.itemconfigure(self._inner_window, width=w)

    def _on_inner_configure(self, _event):
        self._sync_inner_window_width()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, _event):
        self._sync_inner_window_width()

    def scroll(self, units):
        self.canvas.yview_scroll(units, "units")


class ClueApp(tk.Tk):
    """Luxury Noir themed Tk UI: board, ledger, detective log, notebook, and human actions."""

    def __init__(self):
        super().__init__()
        self.title("Clue - Luxury Noir")
        self.configure(bg=BG_DARK)
        self.geometry("1280x860")
        self.minsize(1080, 760)

        self.game = None
        self._after_bot_id = None
        self.notebook_user_marks = {}
        self.revealed_to_player = {}
        self.last_shown_card = None
        self.show_bot_cards = tk.BooleanVar(value=False)
        self.setup_name_var = tk.StringVar(value="Detective")
        self.setup_bots_var = tk.IntVar(value=3)
        self.reveal_popup = None

        self._show_setup()

    def _show_setup(self):
        for child in self.winfo_children():
            child.destroy()

        shell = tk.Frame(self, bg=BG_DARK)
        shell.pack(fill="both", expand=True)

        hero = tk.Frame(shell, bg=BG_DARK)
        hero.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(hero, text="CLUE", bg=BG_DARK, fg=GOLD, font=("Georgia", 34, "bold")).pack(
            pady=(0, 4)
        )
        tk.Label(
            hero,
            text="Luxury Noir Edition",
            bg=BG_DARK,
            fg=TEXT_DIM,
            font=("Georgia", 11, "italic"),
        ).pack(pady=(0, 20))

        frame = tk.Frame(
            hero, bg=BG_PANEL, padx=30, pady=24, highlightbackground=GOLD, highlightthickness=1
        )
        frame.pack()

        tk.Label(frame, text="Your Name", bg=BG_PANEL, fg=TEXT_MAIN, font=("Georgia", 12)).grid(
            row=0, column=0, sticky="w", pady=8
        )
        tk.Entry(
            frame,
            textvariable=self.setup_name_var,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=GOLD,
            font=("Georgia", 12),
            width=18,
            relief="flat",
            bd=4,
        ).grid(row=0, column=1, padx=(12, 0), pady=8)

        tk.Label(frame, text="Bot Count", bg=BG_PANEL, fg=TEXT_MAIN, font=("Georgia", 12)).grid(
            row=1, column=0, sticky="w", pady=8
        )
        tk.Spinbox(
            frame,
            from_=1,
            to=5,
            textvariable=self.setup_bots_var,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            buttonbackground=BG_PANEL,
            font=("Georgia", 12),
            width=5,
            relief="flat",
        ).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=8)

        tk.Button(
            hero,
            text="Begin Investigation",
            bg=GOLD,
            fg=BG_DARK,
            activebackground=GOLD_LIGHT,
            font=("Georgia", 13, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            command=self._start_new_game,
        ).pack(pady=(18, 0))

    def _start_new_game(self):
        name = self.setup_name_var.get().strip() or "Detective"
        bots = self.setup_bots_var.get()
        self.game = GameEngine(human_name=name, num_bots=bots)
        self.notebook_user_marks = {}
        self.revealed_to_player = {}
        self.last_shown_card = None
        self._build_main_ui()
        self._update_all()
        self._start_turn()

    def _panel(self, parent, title):
        return tk.LabelFrame(
            parent,
            text=f" {title} ",
            bg=BG_PANEL,
            fg=GOLD,
            font=("Georgia", 10, "bold"),
            bd=1,
            relief="solid",
            highlightbackground=GOLD,
            highlightthickness=1,
        )

    def _build_main_ui(self):
        for child in self.winfo_children():
            child.destroy()

        topbar = tk.Frame(self, bg=BG_HEADER, height=54)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="CLUE", bg=BG_HEADER, fg=GOLD, font=("Georgia", 20, "bold")).pack(
            side="left", padx=20
        )
        tk.Label(
            topbar, text="Case File", bg=BG_HEADER, fg=TEXT_DIM, font=("Georgia", 10, "italic")
        ).pack(side="left", padx=(0, 12))

        self.turn_label = tk.Label(
            topbar, text="", bg=BG_HEADER, fg=TEXT_MAIN, font=("Georgia", 11, "italic")
        )
        self.turn_label.pack(side="left")

        tk.Checkbutton(
            topbar,
            text="Show Bot Hands",
            variable=self.show_bot_cards,
            command=self._update_all,
            bg=BG_HEADER,
            fg=TEXT_MAIN,
            activebackground=BG_HEADER,
            activeforeground=GOLD,
            selectcolor=BG_PANEL,
            font=("Georgia", 9),
        ).pack(side="right", padx=(0, 12))
        tk.Button(
            topbar,
            text="New Game",
            bg=GREY,
            fg=TEXT_MAIN,
            relief="flat",
            font=("Georgia", 10),
            padx=10,
            command=self._new_game,
        ).pack(side="right", padx=16, pady=8)

        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(main, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, bg=BG_DARK, width=390)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        self._build_board(left)
        self._build_player_panel(left)
        self._build_action_panel(left)
        self._build_log_panel(right)
        self._build_notebook_panel(right)

        self.bind_all("<MouseWheel>", self._on_mousewheel_route)
        self.bind_all("<Button-4>", self._on_mousewheel_route)
        self.bind_all("<Button-5>", self._on_mousewheel_route)

    def _build_board(self, parent):
        frame = self._panel(parent, "Mansion Map")
        frame.pack(fill="both", expand=True, pady=(0, 8))
        self.board_canvas = tk.Canvas(frame, bg=BG_CANVAS, highlightthickness=0)
        self.board_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.board_canvas.bind("<Configure>", lambda _e: self._draw_board())

    def _draw_board(self):
        canvas = self.board_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 10 or height < 10:
            return

        pad = 10
        cols = rows = 3
        cell_w = (width - pad * 2) / cols
        cell_h = (height - pad * 2) / rows
        room_grid = [
            ["Kitchen", "Ballroom", "Conservatory"],
            ["Dining Room", "Study", "Billiard Room"],
            ["Lounge", "Hall", "Library"],
        ]

        player_rooms = self.game.get_player_rooms() if self.game else {}
        room_players = {}
        for name, room in player_rooms.items():
            room_players.setdefault(room, []).append(name)

        for row in range(rows):
            for col in range(cols):
                room = room_grid[row][col]
                style = ROOM_STYLES[room]
                x0 = pad + col * cell_w + 3
                y0 = pad + row * cell_h + 3
                x1 = x0 + cell_w - 6
                y1 = y0 + cell_h - 6
                is_human_here = (
                    player_rooms.get(self.game.human_name) == room if self.game else False
                )

                canvas.create_rectangle(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill=style["fill"],
                    outline=GOLD if is_human_here else style["accent"],
                    width=2 if is_human_here else 1,
                )
                canvas.create_rectangle(
                    x0 + 5, y0 + 5, x1 - 5, y0 + 18, fill=style["accent"], outline=""
                )
                canvas.create_rectangle(
                    x0 + 10, y0 + 28, x1 - 10, y1 - 10, outline=style["accent"], width=1
                )
                canvas.create_text(
                    (x0 + x1) / 2,
                    y0 + 12,
                    text=room.upper(),
                    fill=BG_DARK,
                    font=("Georgia", 8, "bold"),
                )

                players = room_players.get(room, [])
                for index, player_name in enumerate(players):
                    is_human = player_name == self.game.human_name
                    eliminated = self.game.players[player_name].eliminated
                    fill = GOLD if is_human else (GREY if eliminated else BLUE)
                    label = "YOU" if is_human else player_name.replace("Bot ", "")
                    cx = x0 + 20 + (index % 3) * 42
                    cy = y1 - 32 - (index // 3) * 22
                    canvas.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill=fill, outline="")
                    canvas.create_text(
                        cx, cy + 16, text=label, fill=fill, font=("Georgia", 6, "bold")
                    )

    def _build_player_panel(self, parent):
        frame = self._panel(parent, "Case Ledger")
        frame.pack(fill="x", pady=(0, 8))
        self.hand_frame = tk.Frame(frame, bg=BG_PANEL)
        self.hand_frame.pack(fill="x", padx=8, pady=(8, 6))
        self.reveal_frame = tk.Frame(frame, bg=BG_PANEL)
        self.reveal_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.bot_cards_frame = tk.Frame(frame, bg=BG_PANEL)
        self.bot_cards_frame.pack(fill="x", padx=8, pady=(0, 8))

    def _build_action_panel(self, parent):
        frame = self._panel(parent, "Action")
        frame.pack(fill="x")
        self.action_frame = tk.Frame(frame, bg=BG_PANEL)
        self.action_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.action_label = tk.Label(
            self.action_frame,
            text="",
            bg=BG_PANEL,
            fg=TEXT_MAIN,
            font=("Georgia", 10, "italic"),
            wraplength=700,
            justify="left",
        )
        self.action_label.pack(anchor="w")
        self.controls_frame = tk.Frame(self.action_frame, bg=BG_PANEL)
        self.controls_frame.pack(fill="x", pady=6)

    def _build_log_panel(self, parent):
        frame = self._panel(parent, "Detective Log")
        frame.pack(fill="both", expand=True, pady=(0, 8))
        self.log_text = tk.Text(
            frame,
            bg=BG_CANVAS,
            fg=TEXT_MAIN,
            font=("Courier New", 9),
            state="disabled",
            wrap="word",
            relief="flat",
            padx=8,
            pady=8,
            height=18,
        )
        self.log_text.tag_config("suggestion", foreground=GOLD_LIGHT)
        self.log_text.tag_config("reveal", foreground=GREEN)
        self.log_text.tag_config("nope", foreground=RED)
        self.log_text.tag_config("alert", foreground="#f08f64")
        self.log_text.tag_config("accusation", foreground="#ec8270")
        self.log_text.tag_config("win", foreground=GOLD_LIGHT)
        self.log_text.tag_config("wrong", foreground=RED)
        self.log_text.tag_config("info", foreground=TEXT_DIM)
        self.log_text.tag_config("gameover", foreground=RED)
        self.log_text.pack(fill="both", expand=True)

    def _build_notebook_panel(self, parent):
        frame = self._panel(parent, "Detective Notebook")
        frame.pack(fill="both", expand=True)
        self.notebook_scroll = ScrollableFrame(frame, bg=BG_PANEL)
        self.notebook_scroll.pack(fill="both", expand=True)
        self.notebook_inner = self.notebook_scroll.inner

    def _update_hand(self):
        for widget in self.hand_frame.winfo_children():
            widget.destroy()
        for widget in self.reveal_frame.winfo_children():
            widget.destroy()
        for widget in self.bot_cards_frame.winfo_children():
            widget.destroy()

        if not self.game:
            return

        tk.Label(
            self.hand_frame, text="Your Cards", bg=BG_PANEL, fg=GOLD, font=("Georgia", 9, "bold")
        ).pack(anchor="w")
        cards_row = tk.Frame(self.hand_frame, bg=BG_PANEL)
        cards_row.pack(fill="x", pady=(4, 0))
        for card in self.game.get_human_cards():
            palette = CARD_PALETTE[CARD_TYPE[card]]
            tile = tk.Frame(
                cards_row,
                bg=palette["bg"],
                padx=8,
                pady=4,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            tile.pack(side="left", padx=4)
            tk.Label(
                tile, text=card, bg=palette["bg"], fg=palette["fg"], font=("Georgia", 9, "bold")
            ).pack()
            tk.Label(
                tile, text=palette["label"], bg=palette["bg"], fg=TEXT_DIM, font=("Georgia", 7)
            ).pack()

        if self.last_shown_card:
            panel = tk.Frame(
                self.reveal_frame,
                bg=BG_PANEL_ALT,
                padx=10,
                pady=8,
                highlightbackground=GOLD,
                highlightthickness=1,
            )
            panel.pack(fill="x")
            tk.Label(
                panel, text="Latest Reveal", bg=BG_PANEL_ALT, fg=GOLD, font=("Georgia", 8, "bold")
            ).pack(anchor="w")
            tk.Label(
                panel,
                text=f"{self.last_shown_card['shower']} showed you {self.last_shown_card['card']}",
                bg=BG_PANEL_ALT,
                fg=INK,
                font=("Georgia", 10, "bold"),
            ).pack(anchor="w", pady=(2, 0))

        if self.show_bot_cards.get():
            tk.Label(
                self.bot_cards_frame,
                text="Bot Hands",
                bg=BG_PANEL,
                fg=GOLD,
                font=("Georgia", 9, "bold"),
            ).pack(anchor="w")
            all_cards = self.game.get_player_cards()
            for name in self.game.player_names:
                if name == self.game.human_name:
                    continue
                row = tk.Frame(self.bot_cards_frame, bg=BG_PANEL)
                row.pack(fill="x", pady=3)
                tk.Label(
                    row,
                    text=name,
                    bg=BG_PANEL,
                    fg=TEXT_MAIN,
                    font=("Georgia", 9, "bold"),
                    width=10,
                    anchor="w",
                ).pack(side="left")
                cards_holder = tk.Frame(row, bg=BG_PANEL)
                cards_holder.pack(side="left", fill="x")
                for card in all_cards.get(name, []):
                    palette = CARD_PALETTE[CARD_TYPE[card]]
                    tk.Label(
                        cards_holder,
                        text=card,
                        bg=palette["bg"],
                        fg=palette["fg"],
                        font=("Georgia", 7, "bold"),
                        padx=6,
                        pady=2,
                    ).pack(side="left", padx=2, pady=1)

    def _clear_controls(self):
        for child in self.controls_frame.winfo_children():
            child.destroy()

    def _update_log(self):
        if not self.game:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in self.game.log[-70:]:
            tag = entry.get("kind", "info")
            self.log_text.insert("end", entry["msg"] + "\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _toggle_user_mark(self, card):
        current = self.notebook_user_marks.get(card)
        if current is None:
            self.notebook_user_marks[card] = "no"
        elif current == "no":
            self.notebook_user_marks[card] = "yes"
        else:
            self.notebook_user_marks[card] = None
        self._update_notebook()

    def _update_notebook(self):
        for widget in self.notebook_inner.winfo_children():
            widget.destroy()
        if not self.game:
            return

        # Pack table northwest so YOU stays just right of the card column, not stretched across the canvas.
        table = tk.Frame(self.notebook_inner, bg=BG_PANEL)
        table.pack(anchor="nw")

        table.grid_anchor("nw")

        players = self.game.player_names
        human = self.game.human_name
        human_cards = set(self.game.get_human_cards())
        all_bots = [p for p in players if p != human]
        show_bots = self.show_bot_cards.get()
        # Reserve one grid column per bot so layout stays stable when hands are hidden.
        bot_columns = {player: 2 + index for index, player in enumerate(all_bots)}
        num_cols = 2 + len(all_bots)
        for col in range(num_cols):
            table.grid_columnconfigure(col, weight=0, minsize=0)

        tk.Label(table, text="", bg=BG_PANEL, width=18).grid(
            row=0, column=0, sticky="w", padx=(4, 0)
        )
        tk.Label(
            table, text="YOU", bg=BG_PANEL, fg=GOLD, font=("Georgia", 7, "bold"), width=4
        ).grid(row=0, column=1, sticky="w", padx=(0, 1))
        for player, col in bot_columns.items():
            header = player.replace("Bot ", "B") if show_bots else ""
            tk.Label(
                table, text=header, bg=BG_PANEL, fg=TEXT_DIM, font=("Georgia", 7), width=4
            ).grid(row=0, column=col, sticky="w", padx=1)

        legend = tk.Frame(table, bg=BG_PANEL)
        legend.grid(row=1, column=0, columnspan=num_cols, sticky="w", padx=4, pady=(4, 8))
        tk.Label(
            legend,
            text=f"{NOTEBOOK_GLYPHS['yes']} known   {NOTEBOOK_GLYPHS['no']} ruled out   {NOTEBOOK_GLYPHS['unknown']} unknown",
            bg=BG_PANEL,
            fg=TEXT_DIM,
            font=("Georgia", 7, "italic"),
        ).pack(side="left")

        row = 2
        for title, cards in (("Suspects", SUSPECTS), ("Weapons", WEAPONS), ("Rooms", ROOMS)):
            tk.Label(table, text=title, bg=BG_PANEL, fg=GOLD, font=("Georgia", 9, "bold")).grid(
                row=row, column=0, columnspan=num_cols, sticky="w", padx=4, pady=(6, 2)
            )
            row += 1

            for card in cards:
                known_to_human = card in human_cards or self.revealed_to_player.get(card, False)
                tk.Label(
                    table,
                    text=card,
                    bg=BG_PANEL,
                    fg=GOLD if known_to_human else TEXT_MAIN,
                    font=("Georgia", 8, "bold" if known_to_human else "normal"),
                    width=18,
                    anchor="w",
                ).grid(row=row, column=0, sticky="w", padx=(4, 0))

                if known_to_human:
                    symbol, color = NOTEBOOK_GLYPHS["yes"], GREEN
                elif self.notebook_user_marks.get(card) == "yes":
                    symbol, color = NOTEBOOK_GLYPHS["yes"], GREEN
                elif self.notebook_user_marks.get(card) == "no":
                    symbol, color = NOTEBOOK_GLYPHS["no"], RED
                else:
                    symbol, color = NOTEBOOK_GLYPHS["unknown"], GREY

                tk.Button(
                    table,
                    text=symbol,
                    fg=color,
                    bg=BG_PANEL,
                    activebackground=BG_CARD,
                    font=("Courier New", 10, "bold"),
                    width=3,
                    relief="flat",
                    bd=0,
                    cursor="arrow" if known_to_human else "hand2",
                    command=(lambda c=card: self._toggle_user_mark(c))
                    if not known_to_human
                    else (lambda: None),
                ).grid(row=row, column=1, sticky="w", padx=(0, 1))

                for player, col in bot_columns.items():
                    if show_bots:
                        value = self.game.players[player].kb.has_card.get((player, card))
                        if value is True:
                            symbol, color = NOTEBOOK_GLYPHS["yes"], GREEN
                        elif value is False:
                            symbol, color = NOTEBOOK_GLYPHS["no"], GREY
                        else:
                            symbol, color = NOTEBOOK_GLYPHS["unknown"], TEXT_DIM
                        tk.Label(
                            table,
                            text=symbol,
                            bg=BG_PANEL,
                            fg=color,
                            font=("Courier New", 10, "bold"),
                            width=3,
                        ).grid(row=row, column=col, sticky="w", padx=1)
                    else:
                        tk.Label(
                            table, text="", bg=BG_PANEL, font=("Courier New", 10, "bold"), width=3
                        ).grid(row=row, column=col, sticky="w", padx=1)
                row += 1

    def _on_mousewheel_route(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))

        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if hasattr(self, "notebook_scroll") and widget is self.notebook_scroll.canvas:
                self.notebook_scroll.scroll(delta)
                return
            if hasattr(self, "notebook_scroll") and widget is self.notebook_scroll.inner:
                self.notebook_scroll.scroll(delta)
                return
            if hasattr(self, "log_text") and widget is self.log_text:
                self.log_text.yview_scroll(delta, "units")
                return
            try:
                widget = widget.master
            except Exception:
                break

    def _update_all(self):
        self._update_log()
        self._update_hand()
        self._update_notebook()
        self._draw_board()
        if self.game:
            self.turn_label.configure(text=f"Turn: {self.game.current_player_name}")

    def _start_turn(self):
        if not self.game or self.game.game_over:
            self._show_game_over()
            return
        if self.game.is_human_turn():
            self._human_turn()
        else:
            self.action_label.configure(
                text=f"{self.game.current_player_name} is considering the case."
            )
            self._clear_controls()
            self._after_bot_id = self.after(700, self._run_bot_turn)

    def _run_bot_turn(self):
        if not self.game or self.game.game_over:
            self._show_game_over()
            return
        events = self.game.run_bot_turn()
        self._update_all()
        for event in events:
            if event.get("type") == "await_human_show":
                self._ask_human_to_show(event)
                return
        if self.game.game_over:
            self._show_game_over()
            return
        self._start_turn()

    def _human_turn(self):
        self._clear_controls()
        room = self.game.get_human_room()
        self.action_label.configure(text=f"You are in the {room}. Choose your next move.")
        tk.Button(
            self.controls_frame,
            text="Make Suggestion",
            bg=GOLD,
            fg=BG_DARK,
            font=("Georgia", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            command=self._suggestion_dialog,
        ).pack(side="left", padx=6)
        tk.Button(
            self.controls_frame,
            text="Make Accusation",
            bg=RED,
            fg=TEXT_MAIN,
            font=("Georgia", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            command=self._accusation_dialog,
        ).pack(side="left", padx=6)
        tk.Button(
            self.controls_frame,
            text="Move Room",
            bg=BG_CARD,
            fg=TEXT_MAIN,
            font=("Georgia", 11),
            relief="flat",
            padx=12,
            pady=6,
            command=self._move_dialog,
        ).pack(side="left", padx=6)

    def _move_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Move to Room")
        dialog.configure(bg=BG_DARK)
        dialog.grab_set()
        dialog.transient(self)

        tk.Label(
            dialog, text="Choose a room to move to", bg=BG_DARK, fg=TEXT_MAIN, font=("Georgia", 12)
        ).pack(pady=12, padx=20)
        value = tk.StringVar(value=self.game.get_human_room())
        for room in ROOMS:
            tk.Radiobutton(
                dialog,
                text=room,
                variable=value,
                value=room,
                bg=BG_DARK,
                fg=TEXT_MAIN,
                selectcolor=BG_CARD,
                activebackground=BG_DARK,
                font=("Georgia", 11),
            ).pack(anchor="w", padx=26)

        def confirm():
            self.game.players[self.game.human_name].current_room = value.get()
            dialog.destroy()
            self._update_all()
            self._human_turn()

        tk.Button(
            dialog,
            text="Move",
            bg=GOLD,
            fg=BG_DARK,
            font=("Georgia", 11, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            command=confirm,
        ).pack(pady=14)

    def _suggestion_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Make a Suggestion")
        dialog.configure(bg=BG_DARK)
        dialog.grab_set()
        dialog.transient(self)

        room = self.game.get_human_room()
        tk.Label(
            dialog, text=f"Suggestion in {room}", bg=BG_DARK, fg=GOLD, font=("Georgia", 13, "bold")
        ).pack(pady=(16, 6), padx=20)
        form = tk.Frame(dialog, bg=BG_DARK)
        form.pack(padx=20, pady=10)

        tk.Label(form, text="Suspect", bg=BG_DARK, fg=TEXT_MAIN, font=("Georgia", 11)).grid(
            row=0, column=0, sticky="w", pady=4
        )
        suspect_var = tk.StringVar(value=SUSPECTS[0])
        ttk.Combobox(
            form, textvariable=suspect_var, values=SUSPECTS, state="readonly", width=20
        ).grid(row=0, column=1, padx=8)

        tk.Label(form, text="Weapon", bg=BG_DARK, fg=TEXT_MAIN, font=("Georgia", 11)).grid(
            row=1, column=0, sticky="w", pady=4
        )
        weapon_var = tk.StringVar(value=WEAPONS[0])
        ttk.Combobox(
            form, textvariable=weapon_var, values=WEAPONS, state="readonly", width=20
        ).grid(row=1, column=1, padx=8)

        def confirm():
            dialog.destroy()
            self.action_label.configure(text="Investigating suggestion...")
            result = self.game.make_suggestion(
                self.game.human_name, suspect_var.get(), weapon_var.get(), room
            )
            self._update_all()
            self._handle_suggestion_result(result)

        tk.Button(
            dialog,
            text="Suggest",
            bg=GOLD,
            fg=BG_DARK,
            font=("Georgia", 12, "bold"),
            relief="flat",
            padx=16,
            pady=7,
            command=confirm,
        ).pack(pady=14)

    def _handle_suggestion_result(self, result):
        if result.get("type") == "shown":
            card = result.get("card")
            shower = result.get("shower")
            if card:
                self.revealed_to_player[card] = True
                self.last_shown_card = {"shower": shower, "card": card}
                self._show_reveal_popup(shower, card)
                self.action_label.configure(text=f"{shower} showed you {card}.")
            else:
                self.action_label.configure(text=f"{shower} showed you a card.")
            self._update_all()
            self._after(1800, self._human_turn_done)
        elif result.get("type") == "no_refute":
            self.action_label.configure(
                text="Nobody could refute the suggestion. The envelope just got more interesting."
            )
            self._update_all()
            self._after(1800, self._human_turn_done)
        else:
            self._human_turn_done()

    def _show_reveal_popup(self, shower, card):
        if self.reveal_popup and self.reveal_popup.winfo_exists():
            self.reveal_popup.destroy()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=GOLD)
        popup.attributes("-topmost", True)

        inner = tk.Frame(popup, bg=BG_PANEL_ALT, padx=18, pady=14)
        inner.pack(padx=2, pady=2)
        tk.Label(
            inner, text="CARD REVEALED", bg=BG_PANEL_ALT, fg=GOLD, font=("Georgia", 9, "bold")
        ).pack()
        tk.Label(inner, text=card, bg=BG_PANEL_ALT, fg=INK, font=("Georgia", 15, "bold")).pack(
            pady=(4, 0)
        )
        tk.Label(
            inner,
            text=f"shown by {shower}",
            bg=BG_PANEL_ALT,
            fg=TEXT_DIM,
            font=("Georgia", 8, "italic"),
        ).pack()

        self.update_idletasks()
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.winfo_rooty() + 90
        popup.geometry(f"+{x}+{y}")
        popup.after(1800, popup.destroy)
        self.reveal_popup = popup

    def _ask_human_to_show(self, event):
        dialog = tk.Toplevel(self)
        dialog.title("Show a Card")
        dialog.configure(bg=BG_DARK)
        dialog.grab_set()
        dialog.transient(self)

        tk.Label(
            dialog,
            text=f"{event['asker']} made a suggestion.",
            bg=BG_DARK,
            fg=TEXT_MAIN,
            font=("Georgia", 11),
        ).pack(pady=(16, 4), padx=20)
        tk.Label(
            dialog,
            text="Choose one card to show",
            bg=BG_DARK,
            fg=GOLD,
            font=("Georgia", 12, "bold"),
        ).pack()

        value = tk.StringVar(value=event["cards_can_show"][0])
        for card in event["cards_can_show"]:
            tk.Radiobutton(
                dialog,
                text=card,
                variable=value,
                value=card,
                bg=BG_DARK,
                fg=TEXT_MAIN,
                selectcolor=BG_CARD,
                activebackground=BG_DARK,
                font=("Georgia", 11),
            ).pack(anchor="w", padx=28, pady=2)

        def confirm():
            self.game.human_shows_card(value.get())
            dialog.destroy()
            self._update_all()
            if not self.game.game_over:
                self.game.advance_turn()
                self._start_turn()
            else:
                self._show_game_over()

        tk.Button(
            dialog,
            text="Show Card",
            bg=GOLD,
            fg=BG_DARK,
            font=("Georgia", 12, "bold"),
            relief="flat",
            padx=16,
            pady=7,
            command=confirm,
        ).pack(pady=14)

    def _accusation_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Make an Accusation")
        dialog.configure(bg=BG_DARK)
        dialog.grab_set()
        dialog.transient(self)

        tk.Label(
            dialog, text="Final Accusation", bg=BG_DARK, fg=RED, font=("Georgia", 16, "bold")
        ).pack(pady=(16, 4), padx=20)
        tk.Label(
            dialog,
            text="A wrong accusation means elimination.",
            bg=BG_DARK,
            fg=TEXT_DIM,
            font=("Georgia", 9, "italic"),
        ).pack()

        form = tk.Frame(dialog, bg=BG_DARK)
        form.pack(padx=20, pady=12)
        suspect_var = tk.StringVar(value=SUSPECTS[0])
        weapon_var = tk.StringVar(value=WEAPONS[0])
        room_var = tk.StringVar(value=ROOMS[0])

        for row, (label, var, values) in enumerate(
            [
                ("Suspect", suspect_var, SUSPECTS),
                ("Weapon", weapon_var, WEAPONS),
                ("Room", room_var, ROOMS),
            ]
        ):
            tk.Label(form, text=label, bg=BG_DARK, fg=TEXT_MAIN, font=("Georgia", 11)).grid(
                row=row, column=0, sticky="w", pady=4
            )
            ttk.Combobox(form, textvariable=var, values=values, state="readonly", width=20).grid(
                row=row, column=1, padx=8
            )

        def confirm():
            dialog.destroy()
            result = self.game.make_accusation(
                self.game.human_name, suspect_var.get(), weapon_var.get(), room_var.get()
            )
            self._update_all()
            if result["type"] == "correct":
                self._show_game_over()
            elif result["type"] == "wrong":
                if self.game.game_over:
                    self._show_game_over()
                else:
                    self.action_label.configure(text="Wrong accusation. You are eliminated.")
                    self.game.advance_turn()
                    self._after(1500, self._start_turn)

        tk.Button(
            dialog,
            text="Accuse",
            bg=RED,
            fg=TEXT_MAIN,
            font=("Georgia", 12, "bold"),
            relief="flat",
            padx=16,
            pady=7,
            command=confirm,
        ).pack(pady=14)

    def _human_turn_done(self):
        if self.game and not self.game.game_over:
            self.game.advance_turn()
            self._start_turn()

    def _show_game_over(self):
        self._update_all()
        self._clear_controls()
        if not self.game:
            return

        solution = self.game.solution
        winner = self.game.winner
        if winner == self.game.human_name:
            title = "Case Closed: You Win"
            color = GOLD
        elif winner:
            title = f"Case Closed: {winner} Wins"
            color = RED
        else:
            title = "Case Unsolved"
            color = GREY

        self.action_label.configure(text=title, fg=color, font=("Georgia", 14, "bold"))

        summary = tk.Frame(self.controls_frame, bg=BG_PANEL)
        summary.pack(fill="x", pady=(8, 10))
        tk.Label(
            summary,
            text=f"Solution: {solution['suspect']} | {solution['weapon']} | {solution['room']}",
            bg=BG_PANEL,
            fg=INK,
            font=("Georgia", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            summary, text="Final Hands", bg=BG_PANEL, fg=GOLD, font=("Georgia", 10, "bold")
        ).pack(anchor="w")

        all_cards = self.game.get_player_cards()
        for name in self.game.player_names:
            block = tk.Frame(
                summary,
                bg=BG_PANEL_ALT,
                padx=8,
                pady=6,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            block.pack(fill="x", pady=3)
            tk.Label(
                block, text=name, bg=BG_PANEL_ALT, fg=TEXT_MAIN, font=("Georgia", 9, "bold")
            ).pack(anchor="w")
            row = tk.Frame(block, bg=BG_PANEL_ALT)
            row.pack(anchor="w", fill="x", pady=(4, 0))
            for card in all_cards.get(name, []):
                palette = CARD_PALETTE[CARD_TYPE[card]]
                tk.Label(
                    row,
                    text=card,
                    bg=palette["bg"],
                    fg=palette["fg"],
                    font=("Georgia", 7, "bold"),
                    padx=6,
                    pady=2,
                ).pack(side="left", padx=2, pady=1)

        tk.Button(
            self.controls_frame,
            text="Play Again",
            bg=GOLD,
            fg=BG_DARK,
            font=("Georgia", 12, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            command=self._new_game,
        ).pack()

    def _new_game(self):
        if self._after_bot_id:
            self.after_cancel(self._after_bot_id)
        self.game = None
        self._show_setup()

    def _after(self, ms, fn):
        self._after_bot_id = self.after(ms, fn)


def main():
    app = ClueApp()
    app.mainloop()


if __name__ == "__main__":
    main()
