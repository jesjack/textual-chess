import tracemalloc
from typing import Optional

import chess
from chess import Board
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Footer
from typing_extensions import override

from src.utils.debug import timeit
from .components.chess_square import ChessSquare
from .components.checkmate_screen import CheckmateScreen

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
                # Se usa la orientación blanca por defecto (turno de blancas)
                for square in np.flipud(np.array(chess.SQUARES).reshape(8, 8)).flatten():
                    yield ChessSquare(square, self.board)
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

    @override
    @timeit
    def query_one(self, *args, **kwargs):
        return super().query_one(*args, **kwargs)

    @timeit
    async def update_board(self):
        await self.update_board_layout()
        last_move = self.board.peek() if self.board.move_stack else None
        if last_move is None: return
        castling = self.board.is_castling(last_move)
        en_passant = self.board.is_en_passant(last_move)
        if castling or en_passant:
            # Obtener todos los cuadros de una sola vez
            squares = self.query(ChessSquare)
            for square in squares:
                square.update_piece()
            return

        # Actualizar solo los cuadros afectados por el último movimiento
        from_square = last_move.from_square
        to_square = last_move.to_square
        square1 = self.query_one(f"#square-{from_square}", ChessSquare)
        square2 = self.query_one(f"#square-{to_square}", ChessSquare)
        square1.update_piece()
        square2.update_piece()

    @timeit
    async def update_board_layout(self):
        @timeit
        def get_current_mapping():
            return {widget.square: widget for widget in self.app.query(ChessSquare)}

        @timeit
        def calculate_desired_order():
            if not hasattr(self, "_white_order"):
                white_order = np.flipud(np.array(chess.SQUARES).reshape(8, 8)).flatten()
                self._white_order = white_order
                self._black_order = white_order[::-1]
            return self._white_order if self.board.turn else self._black_order

        @timeit
        async def reorder_squares(board_container, desired_order, current_mapping):
            # Create new ordered list of widgets
            new_order = []
            for square_num in desired_order:
                widget = current_mapping[square_num]
                new_order.append(widget)
            
            # Remove all squares from container
            squares = list(self.query(ChessSquare))
            await board_container.remove(*squares)
            
            # Add them back in the correct order
            await board_container.mount(*new_order)
            
            return len(squares)

        # Main execution
        board_container = self.query_one(".board")
        desired_order = calculate_desired_order()
        current_mapping = get_current_mapping()
        
        squares_count = await reorder_squares(board_container, desired_order, current_mapping)
        print(f"Tablero reordenado con {squares_count} cuadrados")

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
