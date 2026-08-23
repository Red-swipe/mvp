import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from engine.engine import Engine


class DPad(QWidget):
    def __init__(self, key_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(86, 67)

        self.setAutoFillBackground(False)

        btn_up = QPushButton("▲", self)
        btn_left = QPushButton("◀", self)
        btn_ctr = QPushButton("", self)
        btn_right = QPushButton("▶", self)
        btn_down = QPushButton("▼", self)

        btn_up.setGeometry(27, 2, 32, 22)
        btn_left.setGeometry(2, 22, 28, 23)
        btn_ctr.setGeometry(30, 22, 26, 23)
        btn_right.setGeometry(56, 22, 28, 23)
        btn_down.setGeometry(27, 43, 32, 22)

        arrow_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: #d8d8d8;
                font-size: 9px;
            }
            QPushButton:pressed { color: #ffffff; }
        """
        for btn in [btn_up, btn_left, btn_ctr, btn_right, btn_down]:
            btn.setStyleSheet(arrow_style)

        btn_up.clicked.connect(lambda: key_callback("dpad_up"))
        btn_left.clicked.connect(lambda: key_callback("dpad_left"))
        btn_ctr.clicked.connect(lambda: key_callback("dpad_center"))
        btn_right.clicked.connect(lambda: key_callback("dpad_right"))
        btn_down.clicked.connect(lambda: key_callback("dpad_down"))

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QLinearGradient, QColor
        from PySide6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#606063"))
        grad.setColorAt(1, QColor("#454548"))
        painter.setBrush(grad)
        painter.setPen(QColor("#1a1a1b"))
        painter.drawRoundedRect(QRectF(0, 4, 86, 58), 29, 29)
        painter.end()


class CalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mentis ClassWiz")
        self.setFixedSize(340, 760)
        self.setObjectName("outerRim")
        self.engine = Engine()
        self.expr = ""
        self.last_result = "0"
        self.shift = False
        self.alpha = False
        self.menu_page = 0
        self.build_ui()
        self.update_lcd()
        self.update_indicators()

    def build_ui(self):
        body = QWidget()
        body.setObjectName("body")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 14)
        outer.addWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(14, 12, 14, 13)
        layout.setSpacing(5)

        header = QWidget()
        header.setFixedHeight(36)
        mentis = QLabel("MENTIS", header)
        mentis.setObjectName("mentis")
        mentis.move(2, 0)
        classwiz = QLabel("CLASSWIZ", header)
        classwiz.setObjectName("classwiz")
        classwiz.setAlignment(Qt.AlignCenter)
        classwiz.setGeometry(0, 25, 280, 12)
        layout.addWidget(header)

        self.build_lcd(layout)
        self.build_controls(layout)
        self.add_scientific_keypad(layout)
        self.add_numeric_keypad(layout)

    def build_lcd(self, parent_layout):
        bezel = QWidget()
        bezel.setObjectName("bezel")
        bezel.setFixedHeight(129)
        bezel_layout = QVBoxLayout(bezel)
        bezel_layout.setContentsMargins(11, 12, 11, 11)

        lcd = QWidget()
        lcd.setObjectName("lcd")
        lcd_layout = QVBoxLayout(lcd)
        lcd_layout.setContentsMargins(4, 3, 4, 3)
        lcd_layout.setSpacing(1)

        display = QHBoxLayout()
        display.setContentsMargins(2, 0, 2, 0)
        self.expr_label = QLabel()
        self.expr_label.setObjectName("exprLine")
        self.result_label = QLabel()
        self.result_label.setObjectName("resultLine")
        self.result_label.setAlignment(Qt.AlignRight)
        display.addWidget(self.expr_label, 1)
        display.addWidget(self.result_label)
        lcd_layout.addLayout(display)

        self.menu_grid = QGridLayout()
        self.menu_grid.setContentsMargins(0, 0, 0, 0)
        self.menu_grid.setSpacing(0)
        self.menu_grid.setRowMinimumHeight(0, 56)
        self.menu_grid.setRowMinimumHeight(1, 0)
        lcd_layout.addLayout(self.menu_grid)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(1, 0, 1, 0)
        self.mode_label = QLabel("1:Calculate")
        self.mode_label.setObjectName("modeName")
        self.mode_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.indicators = QLabel()
        self.indicators.setObjectName("lcdIndicators")
        self.indicators.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom_bar.addWidget(self.mode_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.indicators)
        lcd_layout.addLayout(bottom_bar)

        bezel_layout.addWidget(lcd)
        parent_layout.addWidget(bezel)
        self.refresh_menu()

    def refresh_menu(self):
        while self.menu_grid.count():
            item = self.menu_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.menu_page == 0:
            items = [
                ("×÷\n+−", "1", "Calculate"),
                ("a+bi", "2", "Complex"),
                ("2 8\n10 16", "3", "Base-N"),
                ("[■]", "4", "Matrix"),
                ("↗", "5", "Vector"),
                ("▥", "6", "Statistics"),
                ("⌒", "7", "Distribution"),
                ("▦", "8", "Spreadsheet"),
            ]
        else:
            items = [
                ("x y", "9", "Table"),
                ("=ƒ", "10", "Equation/Func"),
                ("≶", "11", "Inequality"),
                ("a:b", "12", "Ratio"),
            ]

        for index, (icon, number, name) in enumerate(items):
            tile = QPushButton()
            tile.setObjectName("menuIcon")
            tile.setFixedSize(68, 44)
            tile.setToolTip(name)
            glyph = QLabel(tile)
            glyph.setObjectName("menuGlyph")
            glyph.setText(icon)
            glyph.setTextFormat(Qt.PlainText)
            glyph.setAlignment(Qt.AlignCenter)
            glyph.setWordWrap(True)
            glyph.setGeometry(0, 0, 68, 44)
            small = QLabel(number, tile)
            small.setObjectName("menuNumber")
            small.setAlignment(Qt.AlignRight | Qt.AlignBottom)
            small.setGeometry(0, 0, 64, 41)
            tile.clicked.connect(lambda checked=False, n=number, mode=name: self.select_menu(n, mode))
            self.menu_grid.addWidget(tile, index // 4, index % 4)
        self.mode_label.setText("1:Calculate" if self.menu_page == 0 else "9:Table")
        self.update_indicators()

    def select_menu(self, number, mode):
        self.mode_label.setText(f"{number}:{mode}")

    def build_controls(self, parent_layout):
        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.setContentsMargins(4, 0, 4, 0)
        controls.addWidget(self.make_control("SHIFT", "shift", "shiftControl", 35))
        controls.addWidget(self.make_control("ALPHA", "alpha", "alphaControl", 35))
        controls.addWidget(DPad(self.on_key))
        controls.addWidget(self.make_control("MENU<br>+SETUP", "menu", "menuControl", 55))
        controls.addWidget(self.make_control("ON", "on", "onControl", 35))
        parent_layout.addLayout(controls)

    def make_control(self, text, key, kind, width):
        holder = QWidget()
        holder.setObjectName("controlHolder")
        holder.setProperty("kind", kind)
        holder.setFixedSize(width, 49)
        label = QLabel(holder)
        label.setObjectName("controlLabel")
        label.setTextFormat(Qt.RichText)
        label.setText(text)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(0, 0, width, 18)
        button = self.make_button("", key, "top")
        button.setParent(holder)
        button.setGeometry((width - 28) // 2, 18, 28, 28)
        return holder

    def make_button(self, text, key, kind):
        button = QPushButton(text)
        button.setProperty("data-key", key)
        button.setProperty("kind", kind)
        button.clicked.connect(lambda checked=False, k=key: self.on_key(k))
        return button

    def make_key_holder(self, text, key, kind, label_html, width=None):
        holder = QWidget()
        if width:
            holder.setMinimumWidth(width)
        stack = QVBoxLayout(holder)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)
        label = QLabel()
        label.setObjectName("keyLabel")
        label.setTextFormat(Qt.RichText)
        label.setText(label_html)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(10)
        stack.addWidget(label)
        button = self.make_button(text, key, kind)
        stack.addWidget(button)
        return holder, button

    def make_special_numeric_holder(self, text, key, kind):
        holder = QWidget()
        stack = QVBoxLayout(holder)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)

        if key == "del":
            del_label = QLabel('<span style="color:#d7517f;">INS</span>')
            del_label.setTextFormat(Qt.RichText)
            del_label.setAlignment(Qt.AlignCenter)
            del_label.setFixedHeight(10)
            del_label.setStyleSheet("font-size: 6px;")
            stack.addWidget(del_label)
        else:
            ac_label = QLabel('<span style="color:#d8a527;">OFF</span>')
            ac_label.setTextFormat(Qt.RichText)
            ac_label.setAlignment(Qt.AlignCenter)
            ac_label.setFixedHeight(10)
            ac_label.setStyleSheet("font-size: 6px;")
            stack.addWidget(ac_label)

        stack.addWidget(self.make_button(text, key, kind))
        return holder

    def add_scientific_keypad(self, parent_layout):
        special = QHBoxLayout()
        special.setSpacing(3)
        special.setContentsMargins(0, 0, 0, 0)
        holder, self.optn_btn = self.make_key_holder("OPTN", "optn", "scientific", self.legend("QR"), 52)
        special.addWidget(holder)
        holder, self.calc_btn = self.make_key_holder("CALC", "calc", "scientific", self.legend("SOLVE ="), 52)
        special.addWidget(holder)
        gap = QWidget()
        gap.setFixedWidth(18)
        special.addWidget(gap)
        holder, _ = self.make_key_holder("∫", "integral", "scientific", self.legend("Σ :"))
        special.addWidget(holder)
        holder, _ = self.make_key_holder("x", "variable", "scientific", self.legend("d/dx"))
        special.addWidget(holder)
        special.addStretch()
        parent_layout.addLayout(special)

        rows = [
            [("□/□", "fraction", "a b/c"), ("√□", "sqrt", "∛"), ("x²", "square", "x³ DEC"), ("x□", "power", "ˣ√ HEX"), ("log□", "log", "10ˣ BIN"), ("ln", "ln", "eˣ OCT")],
            [("(-)", "negate", "logₐ A"), ("°′″", "ellipsis", "FACT B"), ("x⁻¹", "inverse", "x! C"), ("sin", "sin", "sin⁻¹ D"), ("cos", "cos", "cos⁻¹ E"), ("tan", "tan", "tan⁻¹ F")],
            [("STO", "sto", "RECALL"), ("ENG", "eng", "←→"), ("(", "left_paren", "Abs"), (")", "right_paren", "x"), ("S⇔D", "s_to_d", "a b/c↔d/c y"), ("M+", "m_plus", "M− M")],
        ]
        for row in rows:
            grid = QHBoxLayout()
            grid.setSpacing(3)
            grid.setContentsMargins(0, 0, 0, 0)
            for text, key, label in row:
                holder, _ = self.make_key_holder(text, key, "scientific", self.legend(label))
                grid.addWidget(holder)
            parent_layout.addLayout(grid)

    def legend(self, text):
        if " " not in text:
            return f"<span style='color:#d8a527'>{text}</span>"
        parts = text.split(" ", 1)
        return f"<span style='color:#d8a527'>{parts[0]}</span> <span style='color:#d7517f'>{parts[1]}</span>"

    def add_numeric_keypad(self, parent_layout):
        rows = [
            [("7", "7", "CONST", "numeric"), ("8", "8", "CONV", "numeric"), ("9", "9", "RESET", "numeric"), ("DEL", "del", "<span style='color:#d7517f'>INS</span>", "delete"), ("AC", "ac", "<span style='color:#d8a527'>OFF</span>", "delete")],
            [("4", "4", "", "numeric"), ("5", "5", "", "numeric"), ("6", "6", "", "numeric"), ("×", "multiply", "", "operator"), ("÷", "divide", "", "operator")],
            [("1", "1", "", "numeric"), ("2", "2", "", "numeric"), ("3", "3", "", "numeric"), ("+", "plus", "", "operator"), ("−", "minus", "", "operator")],
            [("0", "0", "", "numeric"), (".", "decimal", "", "numeric"), ("×10ˣ", "scientific", "", "operator"), ("Ans", "ans", "", "operator"), ("=", "equals", "", "operator")],
        ]
        for row in rows:
            grid = QHBoxLayout()
            grid.setSpacing(5)
            grid.setContentsMargins(0, 0, 0, 0)
            for text, key, label, kind in row:
                if key in ("del", "ac"):
                    holder = self.make_special_numeric_holder(text, key, kind)
                else:
                    holder, _ = self.make_key_holder(
                        text,
                        key,
                        kind,
                        self.legend(label) if label else "&nbsp;",
                    )
                grid.addWidget(holder)
            parent_layout.addLayout(grid)

    def resolve_token(self, key):
        if self.shift:
            shifted = {"sin": "asin(", "cos": "acos(", "tan": "atan(", "log": "10^(", "ln": "e^(", "sqrt": "cbrt(", "square": "^3", "power": "xroot(", "scientific": "π", "0": "round(", "decimal": "rand()"}
            return shifted.get(key, "")
        if self.alpha:
            alpha = {"negate": "A", "ellipsis": "B", "inverse": "C", "sin": "D", "cos": "E", "tan": "F", "right_paren": "x", "s_to_d": "y", "m_plus": "M", "scientific": "e", "decimal": "RanInt("}
            return alpha.get(key, "")
        normal = {**{str(n): str(n) for n in range(10)}, "decimal": ".", "plus": "+", "minus": "-", "multiply": "*", "divide": "/", "left_paren": "(", "right_paren": ")", "negate": "(-", "sin": "sin(", "cos": "cos(", "tan": "tan(", "log": "log(", "ln": "ln(", "sqrt": "sqrt(", "square": "^2", "power": "^", "inverse": "^(-1)", "scientific": "*10^", "ans": str(self.last_result), "fraction": "/", "variable": "x", "integral": "∫("}
        return normal.get(key, "")

    def on_key(self, key):
        if key == "shift":
            self.shift = not self.shift
            self.alpha = False
            self.update_indicators()
            return
        if key == "alpha":
            self.alpha = not self.alpha
            self.shift = False
            self.update_indicators()
            return
        if key == "equals":
            self.do_evaluate()
        elif key == "ac":
            self.expr = ""
            self.last_result = "0"
            self.update_lcd()
        elif key == "del":
            self.expr = self.expr[:-1]
            self.update_lcd()
        elif key == "menu":
            self.menu_page = 1 - self.menu_page
            self.refresh_menu()
        elif key == "dpad_left":
            self.menu_page = 0
            self.refresh_menu()
        elif key == "dpad_right":
            self.menu_page = 1
            self.refresh_menu()
        else:
            token = self.resolve_token(key)
            if token:
                self.expr += token
                self.update_lcd()
        self.shift = False
        self.alpha = False
        self.update_indicators()

    def do_evaluate(self):
        try:
            result = self.engine.evaluate(self.expr)
            if result == int(result):
                self.last_result = str(int(result))
            else:
                self.last_result = str(round(result, 10)).rstrip("0")
            self.update_lcd()
        except Exception:
            self.last_result = "Math ERROR"
            self.update_lcd()

    def update_lcd(self):
        self.expr_label.setText(self.expr or "")
        self.result_label.setText(self.last_result)

    def update_indicators(self):
        if hasattr(self, "indicators"):
            self.indicators.setText(("S" if self.shift else "") + ("  A" if self.alpha else ""))


STYLE = """
QWidget#outerRim { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #777978, stop:0.07 #e4e5e3, stop:0.17 #c7c8c6, stop:0.84 #a7a8a7, stop:1 #747675); border-radius:38px 38px 31px 31px; }
QWidget#body { background:qlineargradient(y1:0,y2:1, stop:0 #303031, stop:0.55 #29292a, stop:1 #262627); border-radius:31px 31px 24px 24px; border:1px solid #3b3b3d; }
QLabel#mentis { color:white; font-family:Arial; font-size:22px; font-weight:900; }
QLabel#classwiz { color:#d95c7f; font-family:Arial; font-size:10px; font-weight:700; }
QWidget#bezel { background:#0e0f10; border-radius:13px; }
QWidget#lcd { background:qlineargradient(y1:0,y2:1, stop:0 #dce6c2, stop:1 #cedab0); border:1px solid #83877d; border-radius:3px; }
QLabel#exprLine { color:#454b3b; font-family:Consolas; font-size:7px; }
QLabel#resultLine { color:#1b2119; font-family:Consolas; font-size:11px; font-weight:bold; }
QLabel#menuGlyph { color:#141614; font-family:Arial; font-size:9px; font-weight:bold; }
QLabel#menuNumber { color:#141614; font-family:Arial; font-size:7px; padding-right:2px; padding-bottom:1px; }
QPushButton#menuIcon { background:rgba(255,255,255,0.15); border:1px solid #353735; padding:0; }
QLabel#modeName { color:#141614; font-family:Arial; font-size:14px; font-weight:bold; }
QLabel#lcdIndicators { color:#141614; font-family:Arial; font-size:8px; font-weight:bold; }
QLabel#controlLabel { color:#d8a527; font-family:Arial; font-size:6px; font-weight:bold; }
QWidget#controlHolder[kind="alphaControl"] QLabel { color:#d7517f; }
QWidget#controlHolder[kind="menuControl"] QLabel, QWidget#controlHolder[kind="onControl"] QLabel { color:#d8a527; }
QLabel#keyLabel { color:#d8a527; font-family:Arial; font-size:6px; font-weight:bold; }
QPushButton { border:none; }
QPushButton[kind="scientific"] { background:qlineargradient(y1:0,y2:1, stop:0 #222225, stop:1 #121214); color:white; border-radius:4px; font-size:10px; font-weight:bold; min-height:27px; max-height:27px; }
QPushButton[kind="numeric"] { background:qlineargradient(y1:0,y2:1, stop:0 #fbfbfa, stop:1 #dededb); color:#121212; border-radius:4px; font-size:18px; font-weight:800; min-height:34px; max-height:34px; }
QPushButton[kind="operator"] { background:qlineargradient(y1:0,y2:1, stop:0 #f5f5f4, stop:1 #d7d7d4); color:#111; border-radius:4px; font-size:17px; min-height:34px; max-height:34px; }
QPushButton[kind="delete"] { background:qlineargradient(y1:0,y2:1, stop:0 #3d8df5, stop:1 #175ec7); color:white; border-radius:4px; font-size:13px; font-weight:800; min-height:34px; max-height:34px; }
QPushButton[kind="top"] { background:qlineargradient(y1:0,y2:1, stop:0 #858587, stop:1 #69696b); color:white; border-radius:14px; min-width:28px; max-width:28px; min-height:28px; max-height:28px; }
QWidget#dpad { background:qlineargradient(y1:0,y2:1, stop:0 #606063, stop:1 #454548); border-radius:33px; }
QPushButton#dpadButton { background:transparent; border:none; color:#d8d8d8; font-size:9px; }
"""


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = CalculatorWindow()
    if "--smoke-test" in sys.argv:
        window.on_key("2")
        window.on_key("plus")
        window.on_key("3")
        window.on_key("equals")
        sys.exit(0 if window.last_result == "5" else 1)
    window.show()
    sys.exit(app.exec())
