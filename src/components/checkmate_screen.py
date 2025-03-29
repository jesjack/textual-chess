from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Static


class CheckmateScreen(ModalScreen):
    def __init__(self, winner: str):
        super().__init__()
        self.winner = winner

    @property
    def app(self) -> 'ChessApp':
        app = super().app
        if app.__class__.__name__ != "ChessApp":
            raise ValueError("ChessSquare must be a child of ChessApp")
        return app

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Checkmate! {self.winner} wins!", classes="checkmate-message"),
            Button("New Game", id="new-game", classes="checkmate-button"),
            Button("Quit", id="quit", classes="checkmate-button")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-game":
            self.app.pop_screen()
            self.app.reset_game()
        elif event.button.id == "quit":
            self.app.exit()