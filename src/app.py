import tracemalloc
from typing import Optional

import chess
from chess import Board
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Footer

from src.components.chess_board import ChessBoard
from src.utils.debug import timeit
from .components.chess_square import ChessSquare
from .components.checkmate_screen import CheckmateScreen

class ChessApp(App):

    CSS = """
    #main {
        layout: horizontal;
        height: 100%;
    }
    .chess_board {
        layout: grid;
        grid-size: 8 8;
        width: 16;
        height: 8;
        background: red;
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
        self.white_board_container = ChessBoard(self.board, invert=False)
        self.black_board_container = ChessBoard(self.board, invert=True)
        self.white_board_container.display = True
        self.black_board_container.display = False

    def compose(self) -> ComposeResult:
        with Container(id="main"):
            yield self.white_board_container
            yield self.black_board_container
            with Container():
                self.move_table.add_columns("Move", "White", "Black")
                yield self.move_table

        yield Footer()

    def action_new_game(self):
        self.reset_game()

    async def reset_game(self):
        self.board.reset()
        self.selected_square = None
        self.moves = []
        self.move_table.clear()
        await self.update_board()

    @timeit
    async def update_board(self):
        self.update_board_layout()
        squares = self.query(ChessSquare)
        for square in squares:
            square.update_piece()

    @timeit
    def update_board_layout(self):
        self.white_board_container.display = not self.white_board_container.display
        self.black_board_container.display = not self.black_board_container.display


    @timeit
    def update_move_table(self):
        self.move_table.clear()
        moves = list(self.board.move_stack)
        for i in range(0, len(moves), 2):
            white = self.moves[i] if i < len(self.moves) else ""
            black = self.moves[i + 1] if i+1 < len(self.moves) else ""
            self.move_table.add_row(str(i//2 + 1), white, black)

    @timeit
    def reset_board_colors(self):
        squares = self.query(ChessSquare)
        for square in squares:
            square.styles.background = square._get_bg_color()

    @timeit
    def check_game_end(self):
        if self.board.is_checkmate():
            winner = "White" if not self.board.turn else "Black"
            self.push_screen(CheckmateScreen(winner))
            return True
        return False

    async def handle_promotion(self, from_square, to_square, promotion_piece):
        await self.pop_screen()
        move = chess.Move(from_square, to_square, promotion_piece)
        self.moves.append(self.board.san_and_push(move))
        await self.update_board()
        self.update_move_table()
        self.reset_board_colors()
        self.selected_square = None

        self.check_game_end()


if __name__ == "__main__":
    tracemalloc.start()
    ChessApp().run()
    # show_execution_times()

