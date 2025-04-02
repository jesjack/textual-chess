import chess
from chess import Board
from textual import events
from textual.widgets import Label

from .promotion_screen import PromotionScreen
from ..utils.colors import Color
from ..utils.debug import timeit


class ChessSquare(Label):
    def __init__(self, square: int, board: Board):
        super().__init__(id=f"square-{square}", classes="cell")
        self.square = square
        self.board = board
        self.styles.background = self._get_bg_color()
        self.update_piece()

    @property
    def app(self) -> 'ChessApp':
        app = super().app
        if app.__class__.__name__ != "ChessApp":
            raise ValueError("ChessSquare must be a child of ChessApp")
        return app

    @timeit
    def swap(self, other: 'ChessSquare'):
        self.styles.background, other.styles.background = other.styles.background, self.styles.background
        self.styles.color, other.styles.color = other.styles.color, self.styles.color
        self.square, other.square = other.square, self.square
        self.id, other.id = other.id, self.id
        self.update_piece()
        other.update_piece()

    def _get_bg_color(self):
        file, rank = chess.square_file(self.square), chess.square_rank(self.square)
        return Color.LIGHT_GRAY.value if (file + rank) % 2 == 0 else Color.DARK_GRAY.value

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

    @timeit
    def update_piece(self):
        piece = self.board.piece_at(self.square)
        if piece:
            self.update(self.symbol_dict[piece.symbol()])
            self.styles.color = Color.WHITE.value if piece.color else Color.BLACK.value
        else:
            self.update(" ")
            # self.styles.color = Color.BLACK.value

    # async def on_event(self, event: events.Event):
    #     if isinstance(event, events.Click):
    #         if self.app.selected_square is None:
    #             if self.board.color_at(self.square) == self.board.turn:
    #                 self._select_square()
    #         else:
    #             await self._try_move()
    #     return super().on_event(event)

    @timeit
    def on_click(self):
        @timeit
        async def process():
            if self.app.selected_square is None:
                if self.board.color_at(self.square) == self.board.turn:
                    self._select_square()
            else:
                await self._try_move()

        self.call_after_refresh(process)

    def _select_square(self):
        self.styles.background = Color.GREEN.value
        self.app.selected_square = self.square
        for move in self.board.legal_moves:
            if move.from_square == self.square:
                self.app.query_one(f"#square-{move.to_square}").styles.background = Color.BLUE.value

    @timeit
    async def _try_move(self):
        try:
            moves = list(filter(
                lambda move: move.from_square == self.app.selected_square and
                             move.to_square == self.square,
                self.board.legal_moves
            ))

            if moves:
                move = moves[0]

                if move.promotion:
                    async def handle_promotion(p):
                        await self.app.handle_promotion(self.app.selected_square, self.square, p)
                    self.app.push_screen(PromotionScreen(self.board.turn, handle_promotion))
                else:
                    self.app.moves.append(self.board.san_and_push(move))
                    await self.app.update_board()
                    self.app.update_move_table()
                    self.app.reset_board_colors()
                    self.app.selected_square = None
                    self.app.check_game_end()
        finally:
            pass