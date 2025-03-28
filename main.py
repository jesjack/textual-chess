from enum import Enum
from typing import Optional

import chess
import numpy as np
from chess import Board
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, DataTable, Button, Footer


class Color(Enum):
    LIGHT_GRAY = "#a9a9a9"
    DARK_GRAY = "#696969"
    GREEN = "#00ff00"
    BLUE = "#0000ff"
    RED = "#ff0000"
    WHITE = "#ffffff"
    BLACK = "#000000"


class PromotionScreen(ModalScreen):
    def __init__(self, color: bool, on_select):
        """
        Initialize the promotion screen.

        Args:
            color (bool): Color of the pawn being promoted (True for white, False for black)
            on_select (callable): Callback function to handle piece selection
        """
        super().__init__()
        self.color = color
        self.on_select = on_select

    def compose(self) -> ComposeResult:
        """
        Compose the promotion screen with piece selection buttons.
        """
        with Container():
            with Horizontal() as buttons:
                buttons.styles.align = "center", "middle"
                buttons.styles.justify = "center"

                # Define promotion pieces based on color
                if self.color:  # White promotion
                    pieces = [
                        Button("♕ Queen", id="queen-promo"),
                        Button("♖ Rook", id="rook-promo"),
                        Button("♗ Bishop", id="bishop-promo"),
                        Button("♘ Knight", id="knight-promo")
                    ]
                else:  # Black promotion
                    pieces = [
                        Button("♛ Queen", id="queen-promo"),
                        Button("♜ Rook", id="rook-promo"),
                        Button("♝ Bishop", id="bishop-promo"),
                        Button("♞ Knight", id="knight-promo")
                    ]

                for button in pieces:
                    yield button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle piece selection for promotion.
        """
        piece_map = {
            "queen-promo": chess.QUEEN,
            "rook-promo": chess.ROOK,
            "bishop-promo": chess.BISHOP,
            "knight-promo": chess.KNIGHT
        }

        # Call the callback with the selected piece type
        self.on_select(piece_map[event.button.id])
        self.dismiss()


class ChessApp(App):

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]
    CSS = """
    .main {
        layout: horizontal;
        height: 100%;
    }
    .board {
        layout: grid;
        grid-size: 8 8;
        width: 16;
        height: 8;
    }
    
    .cell {
        height: 100%;
        width: 100%;
    }
    .move_history {
        width: auto;
        height: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.board = Board()
        self.selected_square: Optional[int] = None
        self.move_table = DataTable(classes="move_history")
        self.moves = []
        self.promotion_move = None

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="board"):
                for square in np.flipud(np.array(chess.SQUARES).reshape(8,8)).flatten():
                    yield ChessSquare(square, self.board)
            with Container():
                self.move_table.add_columns("Move", "White", "Black")
                yield self.move_table

        yield Footer()

    def update_board(self):
        for square in chess.SQUARES:
            self.query_one(f"#square-{square}", ChessSquare).update_piece()

    def update_move_table(self):
        self.move_table.clear()
        moves = list(self.board.move_stack)
        for i in range(0, len(moves), 2):
            white = self.moves[i] if i < len(self.moves) else ""
            black = self.moves[i + 1] if i+1 < len(self.moves) else ""
            self.move_table.add_row(str(i//2 + 1), white, black)

    def reset_board_colors(self):
        for square in chess.SQUARES:
            self.query_one(f"#square-{square}", ChessSquare).styles.background = self.query_one(f"#square-{square}", ChessSquare)._get_bg_color()

    def handle_promotion(self, from_square, to_square, promotion_piece):
        """
        Handle pawn promotion by creating a move with the selected piece.
        """
        self.pop_screen()
        move = chess.Move(from_square, to_square, promotion_piece)
        self.moves.append(self.board.san_and_push(move))
        self.update_board()
        self.update_move_table()
        self.reset_board_colors()
        self.selected_square = None


class ChessSquare(Label):
    def __init__(self, square: int, board: Board):
        super().__init__(id=f"square-{square}", classes="cell")
        self.square = square
        self.board = board
        self.styles.background = self._get_bg_color()
        self.update_piece()

    @property
    def app(self) -> ChessApp:
        app = super().app
        if not isinstance(app, ChessApp):
            raise ValueError("ChessSquare must be a child of ChessApp")
        return app

    def _get_bg_color(self):
        file, rank = chess.square_file(self.square), chess.square_rank(self.square)
        return Color.LIGHT_GRAY.value if (file + rank) % 2 == 0 else Color.DARK_GRAY.value

    def update_piece(self):
        symbol_dict = {
            "p": "♟",
            "r": "♜",
            "n": "♞",
            "b": "♝",
            "q": "♛",
            "k": "♚",
            "P": "♙",
            "R": "♖",
            "N": "♘",
            "B": "♗",
            "Q": "♕",
            "K": "♔",
        }
        piece = self.board.piece_at(self.square)
        self.update(symbol_dict[piece.symbol()] if piece else " ")
        self.styles.color = Color.WHITE.value if piece and piece.color else Color.BLACK.value

    def on_click(self):
        if self.app.selected_square is None:
            if self.board.color_at(self.square) == self.board.turn:
                self._select_square()
        else:
            self._try_move()

    def _select_square(self):
        self.styles.background = Color.GREEN.value
        self.app.selected_square = self.square
        for move in self.board.legal_moves:
            if move.from_square == self.square:
                self.app.query_one(f"#square-{move.to_square}").styles.background = Color.BLUE.value

    def _try_move(self):
        try:
            moves = list(filter(
                lambda move: move.from_square == self.app.selected_square and
                             move.to_square == self.square,
                self.board.legal_moves
            ))

            if moves:
                move = moves[0]

                # Check if this is a promotion move
                if move.promotion:
                    # Show promotion screen
                    self.app.push_screen(
                        PromotionScreen(
                            self.board.turn,
                            lambda piece: self.app.handle_promotion(
                                self.app.selected_square,
                                self.square,
                                piece
                            )
                        )
                    )
                else:
                    # Regular move
                    self.app.moves.append(self.board.san_and_push(move))
                    self.app.update_board()
                    self.app.update_move_table()
                    self.app.reset_board_colors()
                    self.app.selected_square = None
        finally:
            pass

    def reset_board_colors(self):
        for square in chess.SQUARES:
            self.app.query_one(f"#square-{square}").styles.background = self._get_bg_color()

if __name__ == "__main__":
    ChessApp().run()