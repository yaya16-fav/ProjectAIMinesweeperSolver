"""
Minesweeper 6x6 - GUI Version (Forest/Mine Background Edition)
================================================================
Fitur di versi ini:
    - Background scene "mulut tambang di tengah hutan senja" di-generate
      SENDIRI secara prosedural pakai Pillow (bukan file gambar eksternal)
    - Kunang-kunang kecil terbang pelan & berkedip di background (secukupnya,
      6 ekor, tidak berlebihan)
    - Judul "MINESWEEPER" jadi papan kayu (signboard) ala rambu tambang
    - Semua panel UI (bezel grid, panel keterangan, tombol) tetap bergaya
      3D chunky seperti versi sebelumnya
    - Popup Game Over / Menang tetap ada, dengan tombol Main Lagi

PERUBAHAN LAYOUT (permintaan user):
    - Window sekarang lebih LEBAR dan tidak terlalu tinggi (landscape-ish),
      supaya tidak "mentok" ke bawah layar laptop.
    - Panel "keterangan klik" sekarang benar-benar menempel rapi di BAWAH
      kotak grid 6x6 (sebelumnya bisa tertumpuk/kelihatan di tengah karena
      ukuran grid diukur SEBELUM tombol-tombol selnya dibuat -> sudah
      diperbaiki dengan membangun tombol grid sekaligus saat bezel dibuat).
    - Seluruh blok (judul, panel kontrol, grid, keterangan) diposisikan
      di TENGAH window baik secara horizontal maupun vertikal.

DEPENDENSI TAMBAHAN:
    pip install pillow

Cara jalankan:
    python minesweeper_gui_polished.py
"""

import random
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageTk

from minesweeper_ai import MinesweeperAI


# ============================================================
# COLOR PALETTE
# ============================================================

PALETTE = {
    "bezel_bg":        "#F4D35E",
    "bezel_border":    "#C7861F",
    "bezel_inset":     "#E0B84A",
    "panel_bg":        "#FFFDF5",
    "panel_border":    "#E8C170",
    "cell_unopened":   "#2EC4B6",
    "cell_hover":      "#7EEAE0",
    "cell_revealed":   "#FFFFFF",
    "cell_flagged":    "#FFB703",
    "cell_mine_hit":   "#E63946",
    "cell_mine_other": "#FF8FA3",
    "text_light":      "#3A2E1F",
    "text_dim":        "#8A7A66",
    "accent":          "#0E9E86",
    "restart_btn":     "#EF476F",
    "restart_btn_hover": "#FF5C7A",
    "popup_bg":        "#FFFDF5",
    # papan kayu judul (signboard), menyatu dengan tema tambang/hutan
    "signboard_bg":     "#6B4226",
    "signboard_border": "#3E2513",
    "sign_text_face":   "#FFE8B5",
    "sign_text_shadow": "#2E1B10",
    # kunang-kunang
    "firefly_glow": "#FFEB99",
    "firefly_body": "#FFFDE7",
    # tombol & highlight AI solver
    "ai_btn":            "#2EC4B6",
    "ai_btn_hover":      "#4FE0D2",
    "ai_btn_stop":       "#6C757D",
    "ai_btn_stop_hover": "#868E96",
    "ai_highlight_sure": "#00E676",   # langkah pasti (dari penalaran logika)
    "ai_highlight_guess": "#FF7A00",  # langkah tebakan (tidak ada info cukup)
}

NUMBER_COLORS = {
    1: "#1D4ED8", 2: "#15803D", 3: "#DC2626", 4: "#7C3AED",
    5: "#B45309", 6: "#0E7490", 7: "#831843", 8: "#334155",
}

BOMB_ICON = "\U0001F4A3"
EXPLOSION_ICON = "\U0001F4A5"
FLAG_ICON = "\U0001F6A9"
FACE_NORMAL = "\U0001F642"
FACE_WIN = "\U0001F60E"
FACE_LOSE = "\U0001F635"
TROPHY_ICON = "\U0001F3C6"
PARTY_ICON = "\U0001F389"


# ============================================================
# GAME ENGINE (logic murni, tidak berubah)
# ============================================================

class MinesweeperGame:
    SIZE = 6

    def __init__(self, num_mines=6, seed=None):
        self.rows = self.SIZE
        self.cols = self.SIZE
        self.num_mines = num_mines
        self._rng = random.Random(seed)

        self.mines = set()
        self.revealed = set()
        self.flagged = set()
        self.numbers = {}

        self.first_move_done = False
        self.game_over = False
        self.won = False
        self.exploded_cell = None

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def get_neighbors(self, cell):
        r, c = cell
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    neighbors.append((nr, nc))
        return neighbors

    def _generate_mines(self, safe_cell):
        forbidden = {safe_cell} | set(self.get_neighbors(safe_cell))
        all_cells = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        candidates = [cell for cell in all_cells if cell not in forbidden]
        n = min(self.num_mines, len(candidates))
        self.mines = set(self._rng.sample(candidates, n))

    def _count_adjacent_mines(self, cell):
        return sum(1 for n in self.get_neighbors(cell) if n in self.mines)

    def _flood_fill_open(self, start_cell):
        stack = [start_cell]
        while stack:
            cell = stack.pop()
            if cell in self.revealed or cell in self.flagged:
                continue
            self.revealed.add(cell)
            count = self._count_adjacent_mines(cell)
            self.numbers[cell] = count
            if count == 0:
                for n in self.get_neighbors(cell):
                    if n not in self.revealed:
                        stack.append(n)

    def open_cell(self, r, c):
        cell = (r, c)
        if not self.in_bounds(r, c) or self.game_over:
            return "INVALID"
        if cell in self.flagged:
            return "FLAGGED"
        if cell in self.revealed:
            return "ALREADY_OPEN"

        if not self.first_move_done:
            self._generate_mines(cell)
            self.first_move_done = True

        if cell in self.mines:
            self.revealed.add(cell)
            self.game_over = True
            self.exploded_cell = cell
            return "MINE"

        self._flood_fill_open(cell)

        if self._check_win():
            self.game_over = True
            self.won = True
            return "WIN"
        return "OPENED"

    def flag_cell(self, r, c):
        cell = (r, c)
        if not self.in_bounds(r, c) or cell in self.revealed or self.game_over:
            return "INVALID"
        if cell in self.flagged:
            self.flagged.remove(cell)
            return "UNFLAGGED"
        self.flagged.add(cell)
        return "FLAGGED"

    def _check_win(self):
        total_cells = self.rows * self.cols
        return len(self.revealed) == total_cells - len(self.mines)

    def get_visible_state(self):
        state = {}
        for r in range(self.rows):
            for c in range(self.cols):
                cell = (r, c)
                if cell in self.revealed:
                    state[cell] = self.numbers.get(cell, self._count_adjacent_mines(cell))
                elif cell in self.flagged:
                    state[cell] = "flagged"
                else:
                    state[cell] = "unknown"
        return state


# ============================================================
# AI SOLVER WRAPPER
# ============================================================
# Subclass TIPIS di atas MinesweeperAI (dari minesweeper_ai.py) — HANYA
# untuk melacak apakah langkah terakhir berasal dari penalaran pasti
# (basic rules / constraint satisfaction) atau dari tebakan acak
# (_guess). Tujuannya semata-mata kosmetik (warna highlight berbeda di
# GUI), algoritma solver ASLI di minesweeper_ai.py tidak diubah sama
# sekali — kelas ini cuma "menumpangi" method yang sudah ada.

class TrackedMinesweeperAI(MinesweeperAI):
    def __init__(self, rows, cols, total_bombs):
        super().__init__(rows, cols, total_bombs)
        self.last_action_was_guess = False
        # 'start' | 'basic' | 'csp' | 'guess' — dipakai GUI untuk menulis
        # alasan langkah dalam bahasa manusia di panel log.
        self.last_reason = "start"

    def _apply_basic_rules(self):
        before = len(self._queue)
        super()._apply_basic_rules()
        if len(self._queue) > before:
            self.last_reason = "basic"

    def _apply_constraint_satisfaction(self):
        before = len(self._queue)
        super()._apply_constraint_satisfaction()
        if len(self._queue) > before:
            self.last_reason = "csp"

    def _guess(self):
        self.last_action_was_guess = True
        self.last_reason = "guess"
        return super()._guess()

    def get_action(self):
        self.last_action_was_guess = False
        return super().get_action()


# ============================================================
# BACKGROUND GENERATOR (hutan + mulut tambang, prosedural via Pillow)
# Dibuat scalable terhadap width/height supaya tetap penuh & proporsional
# saat window melebar.
# ============================================================

def generate_forest_mine_background(width, height, seed=7):
    rnd = random.Random(seed)

    def lerp(a, b, t):
        return int(a + (b - a) * t)

    def lerp_color(c1, c2, t):
        return tuple(lerp(c1[i], c2[i], t) for i in range(3))

    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    sky_top = (26, 26, 58)
    sky_horizon = (150, 90, 90)
    horizon_y = int(height * 0.42)
    ground_top = int(height * 0.60)

    for y in range(ground_top):
        t = min(1.0, y / horizon_y)
        draw.line([(0, y), (width, y)], fill=lerp_color(sky_top, sky_horizon, t))

    star_count = max(20, width // 15)
    for _ in range(star_count):
        x = rnd.randint(0, width)
        y = rnd.randint(0, int(horizon_y * 0.7))
        r = rnd.choice([1, 1, 1, 2])
        b = rnd.randint(180, 255)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, min(255, b + 20)))

    moon_x, moon_y = width - 90, 90
    for radius, color in [(46, (70, 65, 60)), (34, (110, 100, 85)), (24, (230, 220, 190))]:
        draw.ellipse([moon_x - radius, moon_y - radius, moon_x + radius, moon_y + radius], fill=color)

    def draw_hill(base_y, amplitude, color, seed_offset):
        r2 = random.Random(seed_offset)
        points = [(0, height)]
        x = 0
        while x <= width:
            y = base_y + r2.randint(-amplitude, amplitude)
            points.append((x, y))
            x += 40
        points.append((width, base_y))
        points.append((width, height))
        draw.polygon(points, fill=color)

    draw_hill(int(height * 0.50), 18, (45, 40, 55), 1)
    draw_hill(int(height * 0.55), 22, (32, 30, 42), 2)

    def draw_pine(x, base_y, h, w, color):
        layers = 4
        for i in range(layers):
            t = i / layers
            lw = w * (1 - t * 0.75)
            top = base_y - h * (t + 1) / layers
            bottom = base_y - h * t / layers
            draw.polygon([(x, top), (x - lw / 2, bottom), (x + lw / 2, bottom)], fill=color)
        trunk_w = w * 0.12
        draw.rectangle([x - trunk_w / 2, base_y - 4, x + trunk_w / 2, base_y + 10], fill=(30, 24, 20))

    tree_back = (28, 38, 30)
    tree_front = (16, 24, 18)

    # Jumlah pohon dihitung dari lebar canvas, supaya background tetap
    # penuh (tidak bolong di kanan) walau window dibuat lebih lebar.
    back_spacing = 55
    back_count = max(6, (width - 20) // back_spacing + 1)
    for i in range(back_count):
        x = 20 + i * back_spacing + rnd.randint(-10, 10)
        h = rnd.randint(70, 110)
        draw_pine(x, int(height * 0.56), h, h * 0.55, tree_back)

    front_spacing = 90
    front_count = max(4, (width - 10) // front_spacing + 1)
    for i in range(front_count):
        x = 10 + i * front_spacing + rnd.randint(-15, 15)
        h = rnd.randint(110, 160)
        draw_pine(x, int(height * 0.62), h, h * 0.6, tree_front)

    ground_top_color = (58, 46, 34)
    ground_bottom_color = (30, 22, 16)
    for y in range(ground_top, height):
        t = (y - ground_top) / max(1, (height - ground_top))
        draw.line([(0, y), (width, y)], fill=lerp_color(ground_top_color, ground_bottom_color, t))

    grass_count = max(150, (width * height) // 2500)
    for _ in range(grass_count):
        x = rnd.randint(0, width)
        y = rnd.randint(ground_top, ground_top + 30)
        h = rnd.randint(4, 9)
        draw.line([(x, y), (x - 2, y - h)], fill=(70, 90, 50), width=1)
        draw.line([(x, y), (x + 2, y - h)], fill=(60, 80, 45), width=1)

    mine_cx = width // 2
    mine_base_y = int(height * 0.72)
    rock_color = (70, 62, 58)
    draw.ellipse([mine_cx - 150, mine_base_y - 90, mine_cx + 150, mine_base_y + 60], fill=rock_color)
    for _ in range(14):
        rx = mine_cx + rnd.randint(-130, 130)
        ry = mine_base_y + rnd.randint(-70, 30)
        rr = rnd.randint(6, 16)
        shade = rnd.randint(-12, 12)
        c = tuple(max(0, min(255, v + shade)) for v in rock_color)
        draw.ellipse([rx - rr, ry - rr, rx + rr, ry + rr], fill=c)

    frame_w, frame_h = 120, 150
    wood_color = (74, 48, 30)
    wood_dark = (52, 32, 20)
    left = mine_cx - frame_w // 2
    right = mine_cx + frame_w // 2
    top = mine_base_y - frame_h

    draw.rectangle([left - 14, top, left, mine_base_y], fill=wood_color)
    draw.rectangle([right, top, right + 14, mine_base_y], fill=wood_color)
    draw.rectangle([left - 20, top - 18, right + 20, top], fill=wood_dark)
    draw.ellipse([left, top + 10, right, mine_base_y + 20], fill=(8, 6, 8))

    rail_color = (90, 80, 70)
    draw.line([(mine_cx - 40, mine_base_y + 15), (mine_cx - 90, height)], fill=rail_color, width=4)
    draw.line([(mine_cx + 40, mine_base_y + 15), (mine_cx + 90, height)], fill=rail_color, width=4)
    for i in range(6):
        t = i / 5
        y = lerp(mine_base_y + 15, height, t)
        x1 = lerp(mine_cx - 40, mine_cx - 90, t)
        x2 = lerp(mine_cx + 40, mine_cx + 90, t)
        draw.line([(x1, y), (x2, y)], fill=(60, 50, 42), width=3)

    lantern_x, lantern_y = left - 24, top + 40
    for radius, color in [(26, (255, 200, 90)), (16, (255, 225, 140)), (7, (255, 250, 210))]:
        draw.ellipse([lantern_x - radius, lantern_y - radius, lantern_x + radius, lantern_y + radius], fill=color)

    return img


# ============================================================
# GUI
# ============================================================

class MinesweeperGUI:
    # Window dibuat LEBAR & tidak terlalu tinggi (landscape-ish) supaya
    # tidak mentok ke bawah layar laptop.
    BG_W = 640
    BG_H = 680
    FIREFLY_COUNT = 6

    # Area terbang kunang-kunang, dihitung relatif terhadap tinggi window
    # (bukan angka pixel tetap) supaya tetap proporsional untuk ukuran apa pun.
    FIREFLY_Y_MIN_FRAC = 0.06
    FIREFLY_Y_MAX_FRAC = 0.34

    def __init__(self, root, num_mines=6):
        self.root = root
        self.num_mines = num_mines
        self.root.title("Minesweeper 6x6")
        self.root.resizable(False, False)
        self.root.geometry(f"{self.BG_W}x{self.BG_H}")

        self.firefly_y_min = self.BG_H * self.FIREFLY_Y_MIN_FRAC
        self.firefly_y_max = self.BG_H * self.FIREFLY_Y_MAX_FRAC

        self.title_font = tkfont.Font(family="Segoe UI", size=19, weight="bold")
        self.info_font = tkfont.Font(family="Segoe UI", size=10)
        self.info_font_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.cell_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.icon_font = tkfont.Font(family="Segoe UI Emoji", size=13)
        self.logo_font = tkfont.Font(family="Segoe UI Emoji", size=22)

        # ---- Canvas dasar + background hutan/tambang ----
        self.canvas = tk.Canvas(self.root, width=self.BG_W, height=self.BG_H,
                                 highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        bg_image = generate_forest_mine_background(self.BG_W, self.BG_H)
        self.bg_photo = ImageTk.PhotoImage(bg_image)  # simpan referensi, wajib!
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

        # ---- Kunang-kunang (dibuat SEBELUM panel UI, supaya panel
        # otomatis "menutupi" kunang-kunang saat lewat di baliknya) ----
        self.fireflies = []
        self._init_fireflies(self.FIREFLY_COUNT)

        # ---- State AI solver ----
        # Didefinisikan SEBELUM panel kontrol dibangun karena binding
        # tombol AI SOLVE (hover, dsb.) langsung membaca self.ai_running.
        self.ai = None
        self.ai_running = False
        self.ai_move_count = 0
        self.manual_locked = False
        self.AI_STEP_DELAY_MS = 350
        self._ai_after_id = None
        self._last_highlighted_btn = None
        # Jendela log terpisah (dibuat saat AI SOLVE ditekan)
        self.log_window = None
        self.log_text = None
        self.ai_mode_var = tk.StringVar(value="manual")  # 'manual' | 'auto'
        self.ai_paused = False
        self.next_step_button = None
        self.pause_button = None

        # ---- Panel UI ----
        # PENTING: grid tombol 6x6 dibangun SEKALIGUS di sini (bukan
        # belakangan di new_game()), supaya saat layout dihitung, tinggi
        # kotak grid sudah final -> panel keterangan tidak akan
        # tertumpuk/salah posisi lagi.
        title_widget = self._build_title()
        control_widget = self._build_control_panel()
        bezel_widget = self._build_bezel_and_grid()
        instruction_widget = self._build_instruction_panel()

        self.popup = None
        self.new_game()

        # Layout dihitung SETELAH semua widget (termasuk 36 tombol grid)
        # benar-benar ada, dan diposisikan di tengah window baik
        # horizontal maupun vertikal.
        self._layout_widgets_on_canvas(
            [title_widget, control_widget, bezel_widget, instruction_widget]
        )

        self._animate_fireflies()

    # ---------------- Layout helper ----------------

    def _layout_widgets_on_canvas(self, widgets, spacing=16, min_margin=20):
        """Menumpuk widget dari atas ke bawah, di-center secara horizontal
        (per widget) DAN memposisikan seluruh blok widget di tengah
        window secara vertikal (jika window lebih tinggi dari total
        konten)."""
        self.root.update_idletasks()
        heights = [w.winfo_reqheight() for w in widgets]
        total_height = sum(heights) + spacing * (len(widgets) - 1)

        y = max(min_margin, (self.BG_H - total_height) // 2)
        center_x = self.BG_W // 2
        for w, h in zip(widgets, heights):
            self.canvas.create_window(center_x, y, anchor="n", window=w)
            y += h + spacing

    # ---------------- Kunang-kunang ----------------

    def _init_fireflies(self, count):
        for _ in range(count):
            x = random.uniform(30, self.BG_W - 30)
            y = random.uniform(self.firefly_y_min, self.firefly_y_max)
            vx = random.uniform(-0.4, 0.4)
            vy = random.uniform(-0.25, 0.25)

            glow_id = self.canvas.create_oval(
                x - 9, y - 9, x + 9, y + 9,
                fill=PALETTE["firefly_glow"], outline="", stipple="gray25"
            )
            body_id = self.canvas.create_oval(
                x - 3, y - 3, x + 3, y + 3,
                fill=PALETTE["firefly_body"], outline=""
            )
            self.fireflies.append({
                "glow": glow_id, "body": body_id,
                "x": x, "y": y, "vx": vx, "vy": vy,
                "visible": True, "blink_countdown": random.randint(20, 60),
            })

    def _animate_fireflies(self):
        for f in self.fireflies:
            # sedikit belokan acak supaya terbangnya terasa organik, bukan lurus
            f["vx"] += random.uniform(-0.05, 0.05)
            f["vy"] += random.uniform(-0.05, 0.05)
            f["vx"] = max(-0.5, min(0.5, f["vx"]))
            f["vy"] = max(-0.35, min(0.35, f["vy"]))

            f["x"] += f["vx"]
            f["y"] += f["vy"]

            if f["x"] < 25 or f["x"] > self.BG_W - 25:
                f["vx"] *= -1
                f["x"] = max(25, min(self.BG_W - 25, f["x"]))
            if f["y"] < self.firefly_y_min or f["y"] > self.firefly_y_max:
                f["vy"] *= -1
                f["y"] = max(self.firefly_y_min, min(self.firefly_y_max, f["y"]))

            self.canvas.coords(f["glow"], f["x"] - 9, f["y"] - 9, f["x"] + 9, f["y"] + 9)
            self.canvas.coords(f["body"], f["x"] - 3, f["y"] - 3, f["x"] + 3, f["y"] + 3)

            f["blink_countdown"] -= 1
            if f["blink_countdown"] <= 0:
                f["visible"] = not f["visible"]
                state = "normal" if f["visible"] else "hidden"
                self.canvas.itemconfig(f["glow"], state=state)
                self.canvas.itemconfig(f["body"], state=state)
                f["blink_countdown"] = random.randint(15, 50)

        self.root.after(70, self._animate_fireflies)

    # ---------------- UI construction (dipanggil dengan parent=self.canvas) ----------------

    def _build_title(self):
        # Judul dibuat seperti PAPAN KAYU (signboard) ala rambu tambang,
        # menyatu dengan tema hutan/tambang di background
        frame = tk.Frame(
            self.canvas, bg=PALETTE["signboard_bg"],
            highlightbackground=PALETTE["signboard_border"], highlightthickness=2,
            bd=5, relief=tk.RAISED
        )
        row = tk.Frame(frame, bg=PALETTE["signboard_bg"])
        row.pack(padx=18, pady=12)

        title_text = "MINESWEEPER"
        text_width = self.title_font.measure(title_text)
        text_height = self.title_font.metrics("linespace")
        canvas_w = text_width + 8
        canvas_h = text_height + 8

        title_canvas = tk.Canvas(
            row, width=canvas_w, height=canvas_h,
            bg=PALETTE["signboard_bg"], highlightthickness=0, bd=0
        )
        title_canvas.pack(side=tk.LEFT)

        title_canvas.create_text(
            4, 4, text=title_text, anchor="nw",
            font=self.title_font, fill=PALETTE["sign_text_shadow"]
        )
        title_canvas.create_text(
            2, 2, text=title_text, anchor="nw",
            font=self.title_font, fill=PALETTE["sign_text_face"]
        )

        return frame

    def _build_control_panel(self):
        control = tk.Frame(
            self.canvas, bg=PALETTE["panel_bg"],
            highlightbackground=PALETTE["panel_border"], highlightthickness=1,
            bd=3, relief=tk.RIDGE
        )
        inner = tk.Frame(control, bg=PALETTE["panel_bg"])
        inner.pack(padx=14, pady=8)

        self.face_label = tk.Label(
            inner, text=FACE_NORMAL, font=("Segoe UI Emoji", 20),
            bg=PALETTE["panel_bg"], width=2
        )
        self.face_label.grid(row=0, column=0, padx=(0, 14))

        self.mine_counter_label = tk.Label(
            inner, text=f"{BOMB_ICON} {self.num_mines}", font=("Segoe UI Emoji", 13, "bold"),
            fg=PALETTE["text_light"], bg=PALETTE["panel_bg"]
        )
        self.mine_counter_label.grid(row=0, column=1, padx=14)

        self.restart_button = tk.Button(
            inner, text="\U0001F504  MAIN ULANG", font=self.info_font_bold,
            command=self.restart, bg=PALETTE["restart_btn"], fg="white",
            activebackground=PALETTE["restart_btn_hover"], activeforeground="white",
            relief=tk.RAISED, padx=14, pady=6, cursor="hand2", bd=4
        )
        self.restart_button.grid(row=0, column=2, padx=(14, 0))
        self.restart_button.bind("<Enter>", lambda e: self.restart_button.config(bg=PALETTE["restart_btn_hover"]))
        self.restart_button.bind("<Leave>", lambda e: self.restart_button.config(bg=PALETTE["restart_btn"]))
        self.restart_button.bind("<ButtonPress-1>", lambda e: self.restart_button.config(relief=tk.SUNKEN))
        self.restart_button.bind("<ButtonRelease-1>", lambda e: self.restart_button.config(relief=tk.RAISED))

        self.ai_button = tk.Button(
            inner, text="\U0001F916  AI SOLVE", font=self.info_font_bold,
            command=self.toggle_ai, bg=PALETTE["ai_btn"], fg="white",
            activebackground=PALETTE["ai_btn_hover"], activeforeground="white",
            relief=tk.RAISED, padx=14, pady=6, cursor="hand2", bd=4
        )
        self.ai_button.grid(row=0, column=3, padx=(14, 0))
        self.ai_button.bind("<Enter>", lambda e: self.ai_button.config(
            bg=PALETTE["ai_btn_stop_hover"] if self.ai_running else PALETTE["ai_btn_hover"]))
        self.ai_button.bind("<Leave>", lambda e: self.ai_button.config(
            bg=PALETTE["ai_btn_stop"] if self.ai_running else PALETTE["ai_btn"]))
        self.ai_button.bind("<ButtonPress-1>", lambda e: self.ai_button.config(relief=tk.SUNKEN))
        self.ai_button.bind("<ButtonRelease-1>", lambda e: self.ai_button.config(relief=tk.RAISED))

        self.ai_status_label = tk.Label(
            inner, text="AI siap membantu \u2014 tekan AI SOLVE", font=self.info_font,
            fg=PALETTE["text_dim"], bg=PALETTE["panel_bg"]
        )
        self.ai_status_label.grid(row=1, column=0, columnspan=4, pady=(8, 0))

        return control

    def _build_bezel_and_grid(self):
        self.bezel = tk.Frame(
            self.canvas, bg=PALETTE["bezel_bg"],
            highlightbackground=PALETTE["bezel_border"],
            highlightthickness=3, bd=6, relief=tk.RAISED
        )

        self.inner_pad = tk.Frame(
            self.bezel, bg=PALETTE["bezel_inset"],
            bd=4, relief=tk.SUNKEN
        )
        self.inner_pad.pack(padx=8, pady=8)

        self.grid_frame = tk.Frame(self.inner_pad, bg=PALETTE["bezel_inset"])
        self.grid_frame.pack(padx=8, pady=8)

        # Tombol-tombol sel dibuat SEKARANG (bukan di new_game()), supaya
        # tinggi bezel sudah final saat layout dihitung nanti. new_game()
        # cukup me-reset tampilan tombol yang sudah ada via refresh_board().
        self.buttons = {}
        for r in range(MinesweeperGame.SIZE):
            for c in range(MinesweeperGame.SIZE):
                btn = tk.Button(
                    self.grid_frame, text="", width=3, height=1,
                    font=self.cell_font, relief=tk.RAISED, bd=3,
                    bg=PALETTE["cell_unopened"], activebackground=PALETTE["cell_hover"],
                    cursor="hand2"
                )
                btn.grid(row=r, column=c, padx=2, pady=2)
                btn.bind("<Button-1>", lambda e, r=r, c=c: self.on_left_click(r, c))
                btn.bind("<Button-3>", lambda e, r=r, c=c: self.on_right_click(r, c))
                btn.bind("<Enter>", lambda e, r=r, c=c: self.on_hover(r, c, True))
                btn.bind("<Leave>", lambda e, r=r, c=c: self.on_hover(r, c, False))
                self.buttons[(r, c)] = btn

        return self.bezel

    def _build_instruction_panel(self):
        panel = tk.Frame(
            self.canvas, bg=PALETTE["panel_bg"],
            highlightbackground=PALETTE["panel_border"], highlightthickness=1,
            bd=3, relief=tk.RIDGE
        )

        self.remaining_label = tk.Label(
            panel, text="Sisa tertutup: -  |  Flag: -", font=self.info_font_bold,
            fg=PALETTE["accent"], bg=PALETTE["panel_bg"]
        )
        self.remaining_label.pack(padx=14, pady=(10, 8))

        legend = tk.Frame(panel, bg=PALETTE["panel_bg"])
        legend.pack(padx=14, pady=(0, 10))

        left_item = tk.Frame(legend, bg=PALETTE["panel_bg"])
        left_item.grid(row=0, column=0, padx=16)
        tk.Label(left_item, text="\U0001F5B1  Klik Kiri", font=self.info_font_bold,
                 fg=PALETTE["text_light"], bg=PALETTE["panel_bg"]).pack()
        tk.Label(left_item, text="Buka sel", font=self.info_font,
                 fg=PALETTE["text_dim"], bg=PALETTE["panel_bg"]).pack()

        right_item = tk.Frame(legend, bg=PALETTE["panel_bg"])
        right_item.grid(row=0, column=1, padx=16)
        tk.Label(right_item, text="\U0001F5B1  Klik Kanan", font=self.info_font_bold,
                 fg=PALETTE["text_light"], bg=PALETTE["panel_bg"]).pack()
        tk.Label(right_item, text=f"Pasang/lepas {FLAG_ICON}", font=self.info_font,
                 fg=PALETTE["text_dim"], bg=PALETTE["panel_bg"]).pack()

        return panel

    # ---------------- Game lifecycle ----------------

    def new_game(self):
        """Reset state game & tampilkan ulang papan TANPA membongkar-pasang
        tombol grid (tombol dibuat sekali saja di _build_bezel_and_grid)."""
        self._stop_ai(reset_status=True)
        self.game = MinesweeperGame(num_mines=self.num_mines)
        self._close_popup()

        self.face_label.config(text=FACE_NORMAL)
        self.mine_counter_label.config(text=f"{BOMB_ICON} {self.num_mines}")
        for btn in self.buttons.values():
            btn.config(highlightthickness=0)
        self.refresh_board()

    def restart(self):
        self.new_game()

    # ---------------- Interaction ----------------

    def on_hover(self, r, c, entering):
        cell = (r, c)
        if self.manual_locked or self.game.game_over or cell in self.game.revealed or cell in self.game.flagged:
            return
        btn = self.buttons[cell]
        btn.config(bg=PALETTE["cell_hover"] if entering else PALETTE["cell_unopened"])

    def on_left_click(self, r, c):
        if self.manual_locked or self.game.game_over:
            return
        result = self.game.open_cell(r, c)

        if result == "MINE":
            self.trigger_explosion_sequence()
            return

        self.refresh_board()

        if result == "WIN":
            self.face_label.config(text=FACE_WIN)
            self.root.after(300, self.show_win_popup)

    def on_right_click(self, r, c):
        if self.manual_locked or self.game.game_over:
            return
        self.game.flag_cell(r, c)
        self.refresh_board()

    # ---------------- AI Solver integration ----------------
    # Menghubungkan MinesweeperAI (minesweeper_ai.py) ke MinesweeperGame.
    # AI tidak pernah menyentuh self.game langsung -> ia hanya menerima
    # ('open'|'flag', r, c) lalu GUI ini yang menjalankannya di game
    # engine, sama seperti kalau manusia yang klik.
    #
    # Untuk presentasi, setiap langkah AI dicatat ke jendela log
    # terpisah dengan alasan dalam bahasa manusia, dan bisa dijalankan
    # dalam Mode Manual (tekan "Langkah Berikutnya" sendiri) atau Mode
    # Otomatis (berjalan sendiri dengan jeda).

    REASON_LABELS = {
        "start": "Langkah pembuka \u2014 belum ada info, mulai dari titik standar",
        "csp": "Constraint satisfaction \u2014 dua batasan angka dibandingkan (subset method)",
        "guess": "Menebak \u2014 tidak ada info logis tersisa, pilih sel di perbatasan",
    }

    def _reason_label(self, action, reason):
        if reason == "basic":
            if action == "open":
                return "Aturan dasar \u2014 jumlah bendera di sekitar sudah pas, sisanya pasti aman"
            return "Aturan dasar \u2014 sisa sel tersembunyi = sisa bom, pasti bom"
        return self.REASON_LABELS.get(reason, "")

    def _find_basic_trigger(self, r, c, action):
        """Cari sel BERNOMOR yang memicu aturan dasar untuk aksi di (r, c).
        HANYA untuk keperluan penjelasan di log (menampilkan 'bindings'
        ala tabel forward-chaining di slide) -- tidak mengubah logika
        AI sama sekali, cuma membaca ulang self.ai.grid yang sudah ada.
        """
        grid = self.ai.grid
        rows, cols = self.ai.rows, self.ai.cols
        for tr in range(rows):
            for tc in range(cols):
                number = grid[tr][tc]
                if number <= 0:
                    continue
                hidden = []
                flagged = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = tr + dr, tc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr][nc] == self.ai.HIDDEN:
                                hidden.append((nr, nc))
                            elif grid[nr][nc] == self.ai.FLAGGED:
                                flagged += 1
                if (r, c) not in hidden:
                    continue
                remaining = number - flagged
                if action == "open" and remaining == 0:
                    return (tr, tc, number, flagged, len(hidden))
                if action == "flag" and remaining == len(hidden):
                    return (tr, tc, number, flagged, len(hidden))
        return None

    def toggle_ai(self):
        if self.ai_running:
            self._stop_ai(reset_status=False)
        else:
            self._start_ai()

    def _start_ai(self):
        if self.game.game_over:
            return
        self.ai = TrackedMinesweeperAI(self.game.rows, self.game.cols, self.num_mines)
        self.ai_running = True
        self.ai_move_count = 0
        self.manual_locked = True
        self.ai_paused = False

        self.ai_button.config(text="\u23F9  HENTIKAN AI", bg=PALETTE["ai_btn_stop"])
        self.ai_status_label.config(
            text="AI mulai menganalisis papan...", fg=PALETTE["text_dim"]
        )

        self._open_log_window()

        if self.ai_mode_var.get() == "auto":
            self._ai_after_id = self.root.after(self.AI_STEP_DELAY_MS, self._ai_auto_tick)
        # Mode manual: tidak dijadwalkan otomatis, menunggu tombol
        # "Langkah Berikutnya" di jendela log.

    def _stop_ai(self, reset_status):
        if self._ai_after_id is not None:
            try:
                self.root.after_cancel(self._ai_after_id)
            except (ValueError, tk.TclError):
                pass
            self._ai_after_id = None
        self.ai_running = False
        self.ai = None
        self.manual_locked = False
        if self._last_highlighted_btn is not None:
            self._last_highlighted_btn.config(highlightthickness=0)
            self._last_highlighted_btn = None
        if hasattr(self, "ai_button"):
            self.ai_button.config(text="\U0001F916  AI SOLVE", bg=PALETTE["ai_btn"])
        if reset_status and hasattr(self, "ai_status_label"):
            self.ai_status_label.config(
                text="AI siap membantu \u2014 tekan AI SOLVE", fg=PALETTE["text_dim"]
            )
        self._set_log_controls_enabled(False)
        if reset_status and self.log_window is not None:
            try:
                self.log_window.destroy()
            except tk.TclError:
                pass
            self.log_window = None
            self.log_text = None

    # ---- Jendela log presentasi ----

    def _open_log_window(self):
        if self.log_window is not None:
            try:
                self.log_window.destroy()
            except tk.TclError:
                pass

        win = tk.Toplevel(self.root)
        win.title("AI Solver \u2014 Log Langkah")
        win.geometry("440x560")
        win.configure(bg=PALETTE["panel_bg"])
        win.protocol("WM_DELETE_WINDOW", self._on_log_window_close)
        self.log_window = win

        mode_frame = tk.Frame(win, bg=PALETTE["panel_bg"])
        mode_frame.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(mode_frame, text="Mode:", font=self.info_font_bold,
                 bg=PALETTE["panel_bg"], fg=PALETTE["text_light"]).pack(side=tk.LEFT)
        tk.Radiobutton(
            mode_frame, text="Manual (kontrol per langkah)", variable=self.ai_mode_var,
            value="manual", bg=PALETTE["panel_bg"], fg=PALETTE["text_light"],
            selectcolor=PALETTE["panel_bg"], command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(6, 0))
        tk.Radiobutton(
            mode_frame, text="Otomatis", variable=self.ai_mode_var,
            value="auto", bg=PALETTE["panel_bg"], fg=PALETTE["text_light"],
            selectcolor=PALETTE["panel_bg"], command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(6, 0))

        btn_frame = tk.Frame(win, bg=PALETTE["panel_bg"])
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.next_step_button = tk.Button(
            btn_frame, text="\u23ED  Langkah Berikutnya", font=self.info_font_bold,
            command=self._manual_next_step, bg=PALETTE["ai_btn"], fg="white",
            relief=tk.RAISED, padx=10, pady=6, cursor="hand2", bd=3
        )
        self.next_step_button.pack(side=tk.LEFT)

        self.pause_button = tk.Button(
            btn_frame, text="\u23F8  Pause", font=self.info_font_bold,
            command=self._toggle_pause, bg=PALETTE["ai_btn_stop"], fg="white",
            relief=tk.RAISED, padx=10, pady=6, cursor="hand2", bd=3
        )
        self.pause_button.pack(side=tk.LEFT, padx=(8, 0))

        text_frame = tk.Frame(win, bg=PALETTE["panel_bg"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        self.log_text = tk.Text(
            text_frame, wrap="word", font=("Consolas", 10),
            bg="#FFFFFF", fg=PALETTE["text_light"], yscrollcommand=scrollbar.set,
            state=tk.DISABLED, padx=8, pady=8
        )
        self.log_text.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("sure", foreground="#0E9E86", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("guess", foreground="#E07A00", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("mine", foreground="#E63946", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("win", foreground="#0E9E86", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("reason", foreground="#8A7A66")

        self._log("Solver dimulai. Pilih mode lalu tekan \u201cLangkah Berikutnya\u201d "
                   "(mode manual) atau tunggu berjalan sendiri (mode otomatis).", tag="reason")
        self._on_mode_change()

    def _on_log_window_close(self):
        self.log_window = None
        self.log_text = None
        self._stop_ai(reset_status=True)

    def _on_mode_change(self):
        manual = self.ai_mode_var.get() == "manual"
        self._set_log_controls_enabled(True, manual=manual)
        if not manual and self.ai_running and not self.ai_paused and self._ai_after_id is None:
            self._ai_after_id = self.root.after(self.AI_STEP_DELAY_MS, self._ai_auto_tick)

    def _set_log_controls_enabled(self, enabled, manual=True):
        if self.next_step_button is not None:
            state = tk.NORMAL if (enabled and manual and self.ai_running) else tk.DISABLED
            self.next_step_button.config(state=state)
        if self.pause_button is not None:
            state = tk.NORMAL if (enabled and not manual and self.ai_running) else tk.DISABLED
            self.pause_button.config(state=state)
            self.pause_button.config(text="\u25B6  Lanjutkan" if self.ai_paused else "\u23F8  Pause")

    def _toggle_pause(self):
        self.ai_paused = not self.ai_paused
        self.pause_button.config(text="\u25B6  Lanjutkan" if self.ai_paused else "\u23F8  Pause")
        if not self.ai_paused and self.ai_running and self.ai_mode_var.get() == "auto" \
                and self._ai_after_id is None:
            self._ai_after_id = self.root.after(self.AI_STEP_DELAY_MS, self._ai_auto_tick)

    def _manual_next_step(self):
        if self.ai_running and self.ai_mode_var.get() == "manual":
            self._advance_ai()

    def _ai_auto_tick(self):
        self._ai_after_id = None
        if not self.ai_running or self.ai_mode_var.get() != "auto" or self.ai_paused:
            return
        self._advance_ai()
        if self.ai_running and self.ai_mode_var.get() == "auto" and not self.ai_paused:
            self._ai_after_id = self.root.after(self.AI_STEP_DELAY_MS, self._ai_auto_tick)

    def _log(self, message, tag=None):
        if self.log_text is None:
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert("end", message + "\n", tag if tag else ())
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see("end")

    def _advance_ai(self):
        """Jalankan SATU langkah AI. Dipanggil oleh tombol manual atau
        oleh loop otomatis (_ai_auto_tick)."""
        if not self.ai_running or self.game.game_over:
            self._stop_ai(reset_status=False)
            return

        action, r, c = self.ai.get_action()
        is_guess = self.ai.last_action_was_guess
        reason = self.ai.last_reason
        self._highlight_ai_cell(r, c, is_guess)
        self.ai_move_count += 1
        step_no = self.ai_move_count
        reason_text = self._reason_label(action, reason)
        if reason == "basic":
            trigger = self._find_basic_trigger(r, c, action)
            if trigger:
                tr, tc, number, flagged, hidden_n = trigger
                reason_text += (
                    f"\n     Dipicu oleh sel ({tr},{tc})={number}  "
                    f"[flag di sekitarnya={flagged}, tetangga tersembunyi={hidden_n}]"
                )

        if action == "open":
            before = set(self.game.revealed)
            result = self.game.open_cell(r, c)

            if result == "MINE":
                self._log(f"#{step_no}  \U0001F4A5 OPEN ({r},{c}) \u2014 KENA BOM", tag="mine")
                self._log(f"     {reason_text}", tag="reason")
                self.refresh_board()
                self._stop_ai(reset_status=False)
                self.ai_status_label.config(
                    text=f"\U0001F4A5 AI kena bom di langkah ke-{step_no}!",
                    fg=PALETTE["cell_mine_hit"]
                )
                self.trigger_explosion_sequence()
                return

            # Laporkan SEMUA sel yang baru terbuka (penting untuk cascade
            # flood-fill, bukan hanya sel yang diklik AI).
            newly_opened = self.game.revealed - before
            for cell in newly_opened:
                self.ai.report_open(cell[0], cell[1], self.game.numbers.get(cell, 0))

            tag = "guess" if is_guess else "sure"
            extra = "" if len(newly_opened) <= 1 else f"  (+{len(newly_opened) - 1} sel ikut terbuka)"
            self._log(f"#{step_no}  OPEN ({r},{c}){extra}", tag=tag)
            self._log(f"     {reason_text}", tag="reason")

            self.refresh_board()

            if result == "WIN":
                self._log(f"\U0001F3C6 AI MENANG dalam {step_no} langkah!", tag="win")
                self._stop_ai(reset_status=False)
                self.ai_status_label.config(
                    text=f"\U0001F3C6 AI menang dalam {step_no} langkah!",
                    fg=PALETTE["accent"]
                )
                self.face_label.config(text=FACE_WIN)
                self.root.after(300, self.show_win_popup)
                return

        elif action == "flag":
            if (r, c) not in self.game.flagged:
                self.game.flag_cell(r, c)
                self.ai.report_flag(r, c)
            tag = "guess" if is_guess else "sure"
            self._log(f"#{step_no}  \U0001F6A9 FLAG ({r},{c})", tag=tag)
            self._log(f"     {reason_text}", tag="reason")
            self.refresh_board()

        mode_text = "menebak" if is_guess else "penalaran pasti"
        self.ai_status_label.config(
            text=f"Langkah {step_no}: {action.upper()} ({r},{c}) \u2014 {mode_text}",
            fg=PALETTE["ai_highlight_guess"] if is_guess else PALETTE["text_dim"]
        )

    def _highlight_ai_cell(self, r, c, is_guess=False):
        # Highlight sel sebelumnya dimatikan dulu, lalu sel baru
        # dinyalakan dan DIBIARKAN menyala (tidak auto-hilang) supaya
        # presenter punya waktu menjelaskan sebelum langkah berikutnya.
        if self._last_highlighted_btn is not None:
            self._last_highlighted_btn.config(highlightthickness=0)
        btn = self.buttons.get((r, c))
        if btn is None:
            return
        color = PALETTE["ai_highlight_guess"] if is_guess else PALETTE["ai_highlight_sure"]
        btn.config(highlightbackground=color, highlightthickness=6)
        self._last_highlighted_btn = btn

    # ---------------- Rendering ----------------

    def refresh_board(self):
        for (r, c), btn in self.buttons.items():
            cell = (r, c)
            if cell in self.game.revealed:
                n = self.game.numbers.get(cell, 0)
                text = "" if n == 0 else str(n)
                color = NUMBER_COLORS.get(n, "black")
                btn.config(
                    text=text, fg=color, bg=PALETTE["cell_revealed"],
                    relief=tk.SUNKEN, state=tk.DISABLED, disabledforeground=color
                )
            elif cell in self.game.flagged:
                btn.config(
                    text=FLAG_ICON, font=self.icon_font, fg="black",
                    bg=PALETTE["cell_flagged"], relief=tk.RAISED, state=tk.NORMAL
                )
            else:
                btn.config(
                    text="", font=self.cell_font, bg=PALETTE["cell_unopened"],
                    relief=tk.RAISED, state=tk.NORMAL
                )
        self._refresh_counters()

    def _refresh_counters(self):
        remaining = self.game.rows * self.game.cols - len(self.game.revealed)
        flagged = len(self.game.flagged)
        self.remaining_label.config(text=f"Sisa tertutup: {remaining}  |  Flag: {flagged}")

    # ---------------- Explosion effect ----------------

    def trigger_explosion_sequence(self):
        self.face_label.config(text=FACE_LOSE)

        for cell in self.game.mines:
            btn = self.buttons[cell]
            if cell == self.game.exploded_cell:
                btn.config(
                    text=EXPLOSION_ICON, font=self.icon_font,
                    bg=PALETTE["cell_mine_hit"], relief=tk.SUNKEN, state=tk.DISABLED
                )
            else:
                btn.config(
                    text=BOMB_ICON, font=self.icon_font,
                    bg=PALETTE["cell_mine_other"], relief=tk.SUNKEN, state=tk.DISABLED
                )

        for cell, btn in self.buttons.items():
            if cell not in self.game.mines and cell not in self.game.revealed:
                btn.config(state=tk.DISABLED)

        self._refresh_counters()
        flashes = 6
        self._flash_background(flashes)
        self.root.after(flashes * 120 + 200, self.show_gameover_popup)

    def _flash_background(self, flashes):
        colors = [PALETTE["cell_mine_hit"], PALETTE["bezel_bg"]]
        color = colors[flashes % 2]
        self.bezel.config(highlightbackground=color)
        if flashes > 0:
            self.root.after(120, lambda: self._flash_background(flashes - 1))
        else:
            self.bezel.config(highlightbackground=PALETTE["bezel_border"])

    # ---------------- Popup akhir game ----------------

    def _close_popup(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None

    def _build_popup_base(self, accent_color):
        self._close_popup()
        popup = tk.Toplevel(self.root)
        popup.configure(bg=PALETTE["popup_bg"])
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width() // 2 - 150
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 130
        popup.geometry(f"300x280+{max(x,0)}+{max(y,0)}")

        border = tk.Frame(popup, bg=accent_color, bd=4, relief=tk.RAISED)
        border.pack(fill="both", expand=True, padx=6, pady=6)

        inner = tk.Frame(border, bg=PALETTE["popup_bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        self.popup = popup
        return inner

    def show_gameover_popup(self):
        inner = self._build_popup_base(PALETTE["cell_mine_hit"])

        tk.Label(inner, text=EXPLOSION_ICON, font=("Segoe UI Emoji", 34),
                 bg=PALETTE["popup_bg"]).pack(pady=(24, 8))
        tk.Label(inner, text="GAME OVER", font=("Segoe UI", 16, "bold"),
                 fg=PALETTE["cell_mine_hit"], bg=PALETTE["popup_bg"]).pack()
        tk.Label(inner, text="Kamu menginjak bom.", font=self.info_font,
                 fg=PALETTE["text_dim"], bg=PALETTE["popup_bg"]).pack(pady=(2, 20))

        btn = tk.Button(
            inner, text="\U0001F504  Main Lagi", font=self.info_font_bold,
            command=self.restart, bg=PALETTE["restart_btn"], fg="white",
            activebackground=PALETTE["restart_btn_hover"], activeforeground="white",
            relief=tk.RAISED, padx=16, pady=8, cursor="hand2", bd=4
        )
        btn.pack(pady=(0, 24))
        btn.bind("<Enter>", lambda e: btn.config(bg=PALETTE["restart_btn_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=PALETTE["restart_btn"]))
        btn.bind("<ButtonPress-1>", lambda e: btn.config(relief=tk.SUNKEN))
        btn.bind("<ButtonRelease-1>", lambda e: btn.config(relief=tk.RAISED))

    def show_win_popup(self):
        inner = self._build_popup_base(PALETTE["accent"])

        tk.Label(inner, text=f"{PARTY_ICON} {TROPHY_ICON} {PARTY_ICON}", font=("Segoe UI Emoji", 26),
                 bg=PALETTE["popup_bg"]).pack(pady=(24, 8))
        tk.Label(inner, text="SELAMAT, MENANG!", font=("Segoe UI", 15, "bold"),
                 fg=PALETTE["accent"], bg=PALETTE["popup_bg"]).pack()
        tk.Label(inner, text="Semua sel aman berhasil dibuka.", font=self.info_font,
                 fg=PALETTE["text_dim"], bg=PALETTE["popup_bg"]).pack(pady=(2, 20))

        btn = tk.Button(
            inner, text="\U0001F504  Main Lagi", font=self.info_font_bold,
            command=self.restart, bg=PALETTE["accent"], fg="#FFFDF5",
            activebackground="#0AF0B0", activeforeground="#FFFDF5",
            relief=tk.RAISED, padx=16, pady=8, cursor="hand2", bd=4
        )
        btn.pack(pady=(0, 24))
        btn.bind("<Enter>", lambda e: btn.config(bg="#0AF0B0"))
        btn.bind("<Leave>", lambda e: btn.config(bg=PALETTE["accent"]))
        btn.bind("<ButtonPress-1>", lambda e: btn.config(relief=tk.SUNKEN))
        btn.bind("<ButtonRelease-1>", lambda e: btn.config(relief=tk.RAISED))


if __name__ == "__main__":
    root = tk.Tk()
    app = MinesweeperGUI(root, num_mines=6)
    root.mainloop()