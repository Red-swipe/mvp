"""SPREADSHEET-mode engine for the CASIO fx-991EX-style calculator.

Implements a small in-memory spreadsheet (45 rows x 5 columns, A1..E45)
with =-formula support and safe, self-contained evaluation.  Formulas are
validated at set time and evaluated lazily on demand.  Only the Python
standard library is used and expressions are parsed with a restricted
recursive-descent parser (no eval/exec).
"""


class SpreadsheetEngine:
    """Evaluate a 45x5 grid of literal or formula cells.

    Cells store raw text.  A value is either a numeric literal ("2",
    "3.14", "-2") or a formula beginning with "=".  Formulas support the
    four arithmetic operators with normal precedence, parentheses, unary
    minus, cell references and the SUM(A1:A5) / MEAN(A1:A5) range
    functions.  References to empty cells evaluate to 0.0.  Circular
    references raise ValueError at evaluation time and divide-by-zero
    raises ZeroDivisionError.  Empty cells report None via
    get_cell_value/get_cell_raw.
    """

    ROWS = 45
    COLS = 5
    COL_NAMES = ["A", "B", "C", "D", "E"]

    def __init__(self):
        self._cells = {}

    def _parse_cell_ref(self, cell_ref):
        """Return (row, col) 0-indexed, or raise ValueError."""
        if not isinstance(cell_ref, str) or len(cell_ref) < 2:
            raise ValueError("Invalid cell reference: {!r}".format(cell_ref))
        col_char = cell_ref[0]
        if col_char not in self.COL_NAMES:
            raise ValueError("Invalid cell reference: {!r}".format(cell_ref))
        row_str = cell_ref[1:]
        if not row_str.isdigit():
            raise ValueError("Invalid cell reference: {!r}".format(cell_ref))
        row = int(row_str)
        if row < 1 or row > self.ROWS:
            raise ValueError("Invalid cell reference: {!r}".format(cell_ref))
        return (row - 1, self.COL_NAMES.index(col_char))

    def _tokenize(self, formula):
        """Split a formula body into (type, value) tokens."""
        tokens = []
        i = 0
        n = len(formula)
        while i < n:
            ch = formula[i]
            if ch in "+-*/:()":
                tokens.append((ch, ch))
                i += 1
            elif ch.isdigit():
                j = i
                while j < n and formula[j].isdigit():
                    j += 1
                if j < n and formula[j] == ".":
                    k = j + 1
                    while k < n and formula[k].isdigit():
                        k += 1
                    if k > j + 1:
                        j = k
                tokens.append(("num", formula[i:j]))
                i = j
            elif ch.isalpha():
                j = i
                while j < n and (formula[j].isalpha() or formula[j].isdigit()):
                    j += 1
                tokens.append(("ident", formula[i:j]))
                i = j
            else:
                raise ValueError("Invalid character in formula")
        return tokens

    def _parse_formula(self, formula):
        """Parse a formula body into an AST node, raising on syntax errors."""
        tokens = self._tokenize(formula)
        if not tokens:
            raise ValueError("Empty formula")
        pos = [0]
        node = self._parse_expr(tokens, pos)
        if pos[0] != len(tokens):
            raise ValueError("Unexpected token after expression")
        return node

    def _parse_expr(self, tokens, pos):
        node = self._parse_term(tokens, pos)
        while pos[0] < len(tokens) and tokens[pos[0]][0] in ("+", "-"):
            op = tokens[pos[0]][0]
            pos[0] += 1
            node = ("binop", op, node, self._parse_term(tokens, pos))
        return node

    def _parse_term(self, tokens, pos):
        node = self._parse_unary(tokens, pos)
        while pos[0] < len(tokens) and tokens[pos[0]][0] in ("*", "/"):
            op = tokens[pos[0]][0]
            pos[0] += 1
            node = ("binop", op, node, self._parse_unary(tokens, pos))
        return node

    def _parse_unary(self, tokens, pos):
        if pos[0] < len(tokens) and tokens[pos[0]][0] == "-":
            pos[0] += 1
            return ("neg", self._parse_unary(tokens, pos))
        return self._parse_primary(tokens, pos)

    def _parse_primary(self, tokens, pos):
        if pos[0] >= len(tokens):
            raise ValueError("Unexpected end of formula")
        ttype, tval = tokens[pos[0]]
        if ttype == "num":
            pos[0] += 1
            return ("num", float(tval))
        if ttype == "ident":
            pos[0] += 1
            if tval in ("SUM", "MEAN"):
                self._expect(tokens, pos, "(")
                start_ref = self._expect_ident(tokens, pos)
                self._expect(tokens, pos, ":")
                end_ref = self._expect_ident(tokens, pos)
                self._expect(tokens, pos, ")")
                sr, sc = self._parse_cell_ref(start_ref)
                er, ec = self._parse_cell_ref(end_ref)
                if sr > er or sc > ec:
                    raise ValueError("Range end precedes range start")
                return ("range", tval, start_ref, end_ref)
            self._parse_cell_ref(tval)
            return ("ref", tval)
        if ttype == "(":
            pos[0] += 1
            node = self._parse_expr(tokens, pos)
            self._expect(tokens, pos, ")")
            return node
        raise ValueError("Unexpected token: {!r}".format(tval))

    def _expect(self, tokens, pos, token):
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != token:
            raise ValueError("Expected {!r}".format(token))
        pos[0] += 1

    def _expect_ident(self, tokens, pos):
        if pos[0] >= len(tokens) or tokens[pos[0]][0] != "ident":
            raise ValueError("Expected cell reference")
        tval = tokens[pos[0]][1]
        pos[0] += 1
        return tval

    def _eval_ast(self, node, visited):
        """Evaluate a parsed AST node against the current grid."""
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "ref":
            return self._resolve(node[1], visited)
        if kind == "neg":
            return -self._eval_ast(node[1], visited)
        if kind == "binop":
            _, op, left, right = node
            lval = self._eval_ast(left, visited)
            rval = self._eval_ast(right, visited)
            if op == "+":
                return lval + rval
            if op == "-":
                return lval - rval
            if op == "*":
                return lval * rval
            return lval / rval
        if kind == "range":
            _, func, start_ref, end_ref = node
            sr, sc = self._parse_cell_ref(start_ref)
            er, ec = self._parse_cell_ref(end_ref)
            total = 0.0
            count = 0
            populated = 0
            for r in range(sr, er + 1):
                for c in range(sc, ec + 1):
                    if (r, c) in self._cells:
                        populated += 1
                    ref_str = self.COL_NAMES[c] + str(r + 1)
                    total += self._resolve(ref_str, visited)
                    count += 1
            if func == "SUM":
                return total
            if populated == 0:
                raise ValueError("MEAN over a range with no populated cells")
            return total / count
        raise ValueError("Unknown node")

    def _resolve(self, ref, visited):
        """Return the numeric value of a cell reference, following formulas."""
        row, col = self._parse_cell_ref(ref)
        key = (row, col)
        if key in visited:
            raise ValueError("Circular reference: {!r}".format(ref))
        raw = self._cells.get(key)
        if raw is None:
            return 0.0
        if not raw.startswith("="):
            return float(raw)
        visited.add(key)
        try:
            return self._eval_ast(self._parse_formula(raw[1:]), visited)
        finally:
            visited.discard(key)

    def set_cell(self, cell_ref, value):
        """Store a literal or formula value, validating it first."""
        row, col = self._parse_cell_ref(cell_ref)
        value = str(value)
        if value.startswith("="):
            if len(value) == 1:
                raise ValueError("Empty formula")
            self._parse_formula(value[1:])
        else:
            try:
                float(value)
            except ValueError:
                raise ValueError("Invalid cell value: {!r}".format(value))
        self._cells[(row, col)] = value

    def get_cell_value(self, cell_ref):
        """Return the evaluated numeric value, or None for empty cells."""
        row, col = self._parse_cell_ref(cell_ref)
        raw = self._cells.get((row, col))
        if raw is None:
            return None
        if not raw.startswith("="):
            return float(raw)
        visited = set()
        visited.add((row, col))
        try:
            return self._eval_ast(self._parse_formula(raw[1:]), visited)
        finally:
            visited.discard((row, col))

    def get_cell_raw(self, cell_ref):
        """Return the stored raw value, or None for empty cells."""
        row, col = self._parse_cell_ref(cell_ref)
        return self._cells.get((row, col))

    def clear_cell(self, cell_ref):
        """Remove a cell's value; clearing an empty cell is a no-op."""
        row, col = self._parse_cell_ref(cell_ref)
        self._cells.pop((row, col), None)

    def clear_all(self):
        """Remove all cell values."""
        self._cells.clear()

    def evaluate_all(self):
        """Evaluate every cell and return a {cell_ref: value} dict."""
        result = {}
        for (row, col), raw in sorted(self._cells.items()):
            ref = self.COL_NAMES[col] + str(row + 1)
            if not raw.startswith("="):
                result[ref] = float(raw)
                continue
            visited = set()
            visited.add((row, col))
            try:
                result[ref] = self._eval_ast(
                    self._parse_formula(raw[1:]), visited
                )
            finally:
                visited.discard((row, col))
        return result

    def _range_cells(self, start_cell: str, end_cell: str) -> list:
        """
        Expand a range string like 'A1':'C3' into all cell names in that block.
        Iterates columns first, then rows within each column.
        """
        col_s = start_cell[0].upper()
        row_s = int(start_cell[1:])
        col_e = end_cell[0].upper()
        row_e = int(end_cell[1:])
        col_start = ord(col_s) - ord('A')
        col_end = ord(col_e) - ord('A')
        cells = []
        for c in range(col_start, col_end + 1):
            for r in range(row_s, row_e + 1):
                cells.append(chr(ord('A') + c) + str(r))
        return cells

    def fill_value(self, start_cell: str, end_cell: str, value: float) -> None:
        """Fill every cell in the range [start_cell:end_cell] with value."""
        for cell in self._range_cells(start_cell, end_cell):
            self.set_cell(cell, str(value))

    def fill_formula(
        self, start_cell: str, end_cell: str, formula: str
    ) -> None:
        """Fill every cell in [start_cell:end_cell] with the same formula."""
        for cell in self._range_cells(start_cell, end_cell):
            self.set_cell(cell, formula)

    def min_val(self, start_cell: str, end_cell: str) -> float:
        """Return the minimum numeric value over the range."""
        values = []
        for cell in self._range_cells(start_cell, end_cell):
            try:
                v = self.get_cell_value(cell)
                if v is not None:
                    fv = float(v)
                    if fv == fv:
                        values.append(fv)
            except (TypeError, ValueError):
                pass
        if not values:
            raise ValueError("min_val: no numeric values found in range")
        return min(values)

    def max_val(self, start_cell: str, end_cell: str) -> float:
        """Return the maximum numeric value over the range."""
        values = []
        for cell in self._range_cells(start_cell, end_cell):
            try:
                v = self.get_cell_value(cell)
                if v is not None:
                    fv = float(v)
                    if fv == fv:
                        values.append(fv)
            except (TypeError, ValueError):
                pass
        if not values:
            raise ValueError("max_val: no numeric values found in range")
        return max(values)