from enum import Enum
from typing import Optional

import chess
import numpy as np
from chess import Board
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Label, DataTable


class Color(Enum):
    LIGHT_GRAY = "#a9a9a9"
    DARK_GRAY = "#696969"
    GREEN = "#00ff00"
    BLUE = "#0000ff"
    RED = "#ff0000"
    WHITE = "#ffffff"
    BLACK = "#000000"

class ChessApp(App):
    CSS = """
    .main {
        layout: horizontal;
        height: 8;
    }
    .board {
        layout: grid;
        grid-size: 8 8;
        width: 16;
        height: 100%;
        /*border: solid $secondary;*/
    }
    
    .cell {
        height: 100%;
        width: 100%;
        /*border: solid $secondary;*/
    }
    .move_history {
        width: auto;/* Ajusta según sea necesario */
        height: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.board = Board()
        self.selected_square: Optional[int] = None
        self.move_table = DataTable()
        self.moves = []

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="board"):
                for square in np.flipud(np.array(chess.SQUARES).reshape(8,8)).flatten():
                    yield ChessSquare(square, self.board)
            with Container(classes="move_history"):
                self.move_table.add_columns("Move", "White", "Black")
                yield self.move_table

    def update_board(self):
        for square in chess.SQUARES:
            self.query_one(f"#square-{square}", ChessSquare).update_piece()

    def update_move_table(self):
        self.move_table.clear()
        moves = list(self.board.move_stack)
        for i in range(0, len(moves), 2):
            white = self.moves[i]
            black = self.moves[i + 1] if i+1 < len(moves) else ""
            self.move_table.add_row(str(i//2 + 1), white, black)

    def reset_board_colors(self):
        for square in chess.SQUARES:
            self.query_one(f"#square-{square}", ChessSquare).styles.background = self.query_one(f"#square-{square}", ChessSquare)._get_bg_color()


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
            move = chess.Move(self.app.selected_square, self.square)
            if self.board.is_legal(move):
                self.app.moves.append(self.board.san_and_push(move))
                # self.board.push(move)
                self.app.update_board()
                self.app.update_move_table()
        finally:
            self.app.reset_board_colors()
            self.app.selected_square = None

    def reset_board_colors(self):
        for square in chess.SQUARES:
            self.app.query_one(f"#square-{square}").styles.background = self._get_bg_color()

if __name__ == "__main__":
    ChessApp().run()