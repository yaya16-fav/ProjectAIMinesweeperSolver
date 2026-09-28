"""
Minesweeper AI Solver — Knowledge-Based (tanpa ML/DL)
=====================================================
Modul ini HANYA berisi algoritma solver.
Tidak ada GUI, tidak ada game logic, tidak ada generator bom.

CARA INTEGRASI:
    1. Import class MinesweeperAI
    2. Buat instance: ai = MinesweeperAI(rows, cols, total_bombs)
    3. Loop:
        a. action, r, c = ai.get_action()
        b. Jalankan action tersebut di simulator
        c. Laporkan hasilnya ke AI via ai.report_open(r, c, value)
           atau ai.report_flag(r, c)
        d. Jika cascade (buka banyak sel sekaligus), panggil
           ai.report_open() untuk SETIAP sel yang terbuka
    4. Ulangi sampai game selesai

CONTOH INTEGRASI MINIMAL:
    ai = MinesweeperAI(6, 6, total_bombs=6)

    while not game_over:
        action, r, c = ai.get_action()

        if action == 'open':
            result = game.open(r, c)       # buka di simulator
            for cell in result.opened:      # laporkan semua sel terbuka
                ai.report_open(cell.r, cell.c, cell.value)
        elif action == 'flag':
            game.flag(r, c)                # tandai di simulator
            ai.report_flag(r, c)
"""

import random


class MinesweeperAI:

    HIDDEN = -2
    FLAGGED = -1

    def __init__(self, rows: int, cols: int, total_bombs: int):
        self.rows = rows
        self.cols = cols
        self.total_bombs = total_bombs
        self.grid = [[self.HIDDEN] * cols for _ in range(rows)]
        self._queue: list[tuple[str, int, int]] = []
        self._queue.append(('open', 0, 0))

    # === INTERFACE UNTUK SIMULATOR ===

    def get_action(self) -> tuple[str, int, int]:
        """Kembalikan aksi berikutnya: ('open', r, c) atau ('flag', r, c)."""
        # Buang aksi basi (sel sudah terbuka/diflag)
        while self._queue:
            action, r, c = self._queue[0]
            if action == 'open' and self.grid[r][c] != self.HIDDEN:
                self._queue.pop(0)
                continue
            if action == 'flag' and self.grid[r][c] != self.HIDDEN:
                self._queue.pop(0)
                continue
            break

        if not self._queue:
            self._think()

        # Buang lagi setelah think
        while self._queue:
            action, r, c = self._queue[0]
            if self.grid[r][c] != self.HIDDEN:
                self._queue.pop(0)
                continue
            return self._queue.pop(0)

        # Benar-benar buntu
        return self._guess()

    def report_open(self, r: int, c: int, value: int):
        """Simulator melaporkan: sel (r,c) terbuka, isinya value (0-8)."""
        self.grid[r][c] = value

    def report_flag(self, r: int, c: int):
        """Simulator melaporkan: sel (r,c) berhasil di-flag."""
        self.grid[r][c] = self.FLAGGED

    # === OTAK AI ===

    def _think(self):
        """Jalankan basic rules, lalu CS jika masih buntu."""
        self._apply_basic_rules()
        if not self._queue:
            self._apply_constraint_satisfaction()

    def _apply_basic_rules(self):
        """Scan seluruh grid, terapkan aturan FLAG dan OPEN."""
        actions = set()

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] <= 0:
                    continue

                number = self.grid[r][c]
                hidden, flagged_count = self._analyze(r, c)
                remaining = number - flagged_count

                if not hidden:
                    continue

                if remaining == 0:
                    for nr, nc in hidden:
                        actions.add(('open', nr, nc))

                elif remaining == len(hidden):
                    for nr, nc in hidden:
                        actions.add(('flag', nr, nc))

        self._queue.extend(actions)

    def _apply_constraint_satisfaction(self):
        """Bandingkan constraint antar-sel (subset method)."""
        constraints = []
        seen_sets: set[tuple[frozenset, int]] = set()

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] <= 0:
                    continue
                hidden, flagged_count = self._analyze(r, c)
                if not hidden:
                    continue
                k = self.grid[r][c] - flagged_count
                s = frozenset(hidden)
                entry = (s, k)
                if entry not in seen_sets:
                    seen_sets.add(entry)
                    constraints.append(entry)

        actions = set()

        for _round in range(10):
            new_constraints = []

            for i in range(len(constraints)):
                s_a, k_a = constraints[i]
                for j in range(len(constraints)):
                    if i == j:
                        continue
                    s_b, k_b = constraints[j]
                    if len(s_a) >= len(s_b):
                        continue
                    if s_a <= s_b:
                        diff = s_b - s_a
                        k_diff = k_b - k_a
                        if k_diff == 0:
                            for cell in diff:
                                actions.add(('open', *cell))
                        elif k_diff == len(diff):
                            for cell in diff:
                                actions.add(('flag', *cell))

                        entry = (frozenset(diff), k_diff)
                        if entry not in seen_sets:
                            seen_sets.add(entry)
                            new_constraints.append(entry)

            if actions:
                break
            if not new_constraints:
                break
            constraints.extend(new_constraints)

        self._queue.extend(actions)

    def _guess(self) -> tuple[str, int, int]:
        """Tebak acak — prioritaskan sel di perbatasan."""
        candidates = []
        border = []

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == self.HIDDEN:
                    candidates.append((r, c))
                    for nr, nc in self._neighbors(r, c):
                        if self.grid[nr][nc] >= 0:
                            border.append((r, c))
                            break

        pool = border if border else candidates
        if not pool:
            return ('open', 0, 0)
        r, c = random.choice(pool)
        return ('open', r, c)

    # === UTILITAS ===

    def _neighbors(self, r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield (nr, nc)

    def _analyze(self, r: int, c: int):
        """Return (list hidden neighbors, flagged count)."""
        hidden = []
        flagged = 0
        for nr, nc in self._neighbors(r, c):
            if self.grid[nr][nc] == self.HIDDEN:
                hidden.append((nr, nc))
            elif self.grid[nr][nc] == self.FLAGGED:
                flagged += 1
        return hidden, flagged
