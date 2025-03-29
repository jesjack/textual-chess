from typing import Optional

import chess
from chess import Board
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Label, DataTable, Button, Footer

from .components.chess_square import ChessSquare
from .components.promotion_screen import PromotionScreen
from .components.checkmate_screen import CheckmateScreen
from .utils.colors import Color

import numpy as np


class ChessApp(App):

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
    .checkmate-message {
        color: #ff0000;
        text-align: center;
        padding: 1;
        margin-bottom: 2;
    }
    .checkmate-button {
        margin: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_game", "New Game"),
    ]

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

    def action_new_game(self):
        self.reset_game()

    def reset_game(self):
        self.board.reset()
        self.selected_square = None
        self.moves = []
        self.move_table.clear()
        self.update_board()

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

    def check_game_end(self):
        if self.board.is_checkmate():
            winner = "White" if not self.board.turn else "Black"
            self.push_screen(CheckmateScreen(winner))
            return True
        return False

    def handle_promotion(self, from_square, to_square, promotion_piece):
        self.pop_screen()
        move = chess.Move(from_square, to_square, promotion_piece)
        self.moves.append(self.board.san_and_push(move))
        self.update_board()
        self.update_move_table()
        self.reset_board_colors()
        self.selected_square = None

        self.check_game_end()


if __name__ == "__main__":
    ChessApp().run()