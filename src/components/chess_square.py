import chess
from chess import Board
from textual.widgets import Label

from .promotion_screen import PromotionScreen
from ..utils.colors import Color


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

                if move.promotion:
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
                    self.app.moves.append(self.board.san_and_push(move))
                    self.app.update_board()
                    self.app.update_move_table()
                    self.app.reset_board_colors()
                    self.app.selected_square = None
                    self.app.check_game_end()
        finally:
            pass

    def reset_board_colors(self):
        for square in chess.SQUARES:
            self.app.query_one(f"#square-{square}").styles.background = self._get_bg_color()