import chess
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button


class PromotionScreen(ModalScreen):
    def __init__(self, color: bool, on_select):
        super().__init__()
        self.color = color
        self.on_select = on_select

    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal() as buttons:
                buttons.styles.align = "center", "middle"
                buttons.styles.justify = "center"

                if self.color:
                    pieces = [
                        Button("♕ Queen", id="queen-promo"),
                        Button("♖ Rook", id="rook-promo"),
                        Button("♗ Bishop", id="bishop-promo"),
                        Button("♘ Knight", id="knight-promo")
                    ]
                else:
                    pieces = [
                        Button("♛ Queen", id="queen-promo"),
                        Button("♜ Rook", id="rook-promo"),
                        Button("♝ Bishop", id="bishop-promo"),
                        Button("♞ Knight", id="knight-promo")
                    ]

                for button in pieces:
                    yield button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        piece_map = {
            "queen-promo": chess.QUEEN,
            "rook-promo": chess.ROOK,
            "bishop-promo": chess.BISHOP,
            "knight-promo": chess.KNIGHT
        }

        self.on_select(piece_map[event.button.id])
        self.dismiss()