import numpy as np
from chess import Board, SQUARES
from textual.containers import Container

from src.components.chess_square import ChessSquare


class ChessBoard(Container):
    """
    ChessBoard is a container that represents the chessboard in the chess game.
    It is a grid layout that contains 64 squares, each represented by a ChessSquare widget.
    """

    def __init__(self, board: Board, invert=False):
        super().__init__(classes="chess_board")
        self.board = board
        self.squares = np.flipud(np.array(SQUARES).reshape(8, 8)).flatten()
        if invert:
            self.squares = np.flip(self.squares)

    def compose(self):
        """
        Compose the chessboard by yielding ChessSquare widgets for each square.
        """
        for square in self.squares:
            yield ChessSquare(square, self.board)