import io
import sys
from dataclasses import dataclass, field
from singleton_decorator import singleton
from enum import Enum
from json.encoder import INFINITY
from typing import List, Any, Coroutine, Optional, Generator, Tuple
import rich
from rich import inspect as rich_inspect
from textual import events, log
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Label, DataTable

def inspect(
        obj: Any,
        *,
        console: Optional["rich.Console"] = None,
        title: Optional[str] = None,
        _help: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        _all: bool = False,
        value: bool = True,
):
    # Redirigir la salida estándar a un StringIO
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    # Inspeccionar el objeto
    rich_inspect(obj=obj, console=console, title=title, help=_help, methods=methods, docs=docs, private=private, dunder=dunder, sort=sort, all=_all, value=value)

    # Obtener el contenido capturado
    output = new_stdout.getvalue()

    # Restaurar la salida estándar original
    sys.stdout = old_stdout

    log(output)


class Color(Enum):
    GREEN = "#00ff00"
    BLUE = "#0000ff"
    LIGHT_GRAY = "#a9a9a9"
    DARK_GRAY = "#696969"
    WHITE = "#ffffff"
    BLACK = "#000000"
    RED = "#ff0000"


class PieceType(Enum):
    K = KING = ("♔", "♚")
    Q = QUEEN = ("♕", "♛")
    R = ROOK = ("♖", "♜")
    B = BISHOP = ("♗", "♝")
    N = KNIGHT = ("♘", "♞")
    P = PAWN = ("♙", "♟")

class MovementType(Enum):
    UNLIMITED = INFINITY
    FIXED = 0

class Col(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"

class Row(Enum):
    R1 = "1"
    R2 = "2"
    R3 = "3"
    R4 = "4"
    R5 = "5"
    R6 = "6"
    R7 = "7"
    R8 = "8"


@dataclass
class SpecialMoveConditions:
    only_move: bool = False # can't capture
    initial_only: bool = False # invalidate if isn't the first move
    only_capture: bool = False # only can move if enemy piece is in the target cell


@dataclass
class MoveVector:
    dx: int
    dy: int
    movement_type: MovementType
    special_conditions: Optional[SpecialMoveConditions] = field(default_factory=SpecialMoveConditions)

    def __mul__(self, scalar: int) -> "MoveVector":
        return MoveVector(self.dx * scalar, self.dy * scalar, self.movement_type, self.special_conditions)


@dataclass
class Piece:
    piece_type: PieceType
    color: Color
    row: Row
    col: Col
    movement_vectors: List[MoveVector] = field(default=list)

    def __post_init__(self):
        self.movement_vectors = self._get_piece_movement_vectors()

    def _get_piece_movement_vectors(self) -> List[MoveVector]:
        """Define los vectores de movimiento para cada tipo de pieza."""
        if self.piece_type == PieceType.K or self.piece_type == PieceType.Q:
            # El rey y la dama se mueven en línea recta (8 direcciones)
            vectors = [
                MoveVector(0, 1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),    # Norte
                MoveVector(1, 1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),    # Noreste
                MoveVector(1, 0, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),    # Este
                MoveVector(1, -1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),   # Sureste
                MoveVector(0, -1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),   # Sur
                MoveVector(-1, -1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),  # Suroeste
                MoveVector(-1, 0, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),   # Oeste
                MoveVector(-1, 1, MovementType.UNLIMITED if self.piece_type == PieceType.Q else MovementType.FIXED),   # Noroeste
            ]

        elif self.piece_type == PieceType.R:
            # La torre se mueve cualquier número de casillas en horizontal o vertical (4 direcciones)
            vectors = [
                MoveVector(0, 1, MovementType.UNLIMITED),    # Norte
                MoveVector(1, 0, MovementType.UNLIMITED),    # Este
                MoveVector(0, -1, MovementType.UNLIMITED),   # Sur
                MoveVector(-1, 0, MovementType.UNLIMITED),   # Oeste
            ]

        elif self.piece_type == PieceType.B:
            # El alfil se mueve cualquier número de casillas en diagonal (4 direcciones)
            vectors = [
                MoveVector(1, 1, MovementType.UNLIMITED),    # Noreste
                MoveVector(1, -1, MovementType.UNLIMITED),   # Sureste
                MoveVector(-1, -1, MovementType.UNLIMITED),  # Suroeste
                MoveVector(-1, 1, MovementType.UNLIMITED),   # Noroeste
            ]

        elif self.piece_type == PieceType.N:
            # El caballo se mueve en forma de "L" (8 posiciones)
            vectors = [
                MoveVector(1, 2, MovementType.FIXED),    # Dos arriba, uno a la derecha
                MoveVector(2, 1, MovementType.FIXED),    # Uno arriba, dos a la derecha
                MoveVector(2, -1, MovementType.FIXED),   # Uno abajo, dos a la derecha
                MoveVector(1, -2, MovementType.FIXED),   # Dos abajo, uno a la derecha
                MoveVector(-1, -2, MovementType.FIXED),  # Dos abajo, uno a la izquierda
                MoveVector(-2, -1, MovementType.FIXED),  # Uno abajo, dos a la izquierda
                MoveVector(-2, 1, MovementType.FIXED),   # Uno arriba, dos a la izquierda
                MoveVector(-1, 2, MovementType.FIXED),   # Dos arriba, uno a la izquierda
            ]

        elif self.piece_type == PieceType.P:
            # Para peones, los vectores dependen del color
            if self.color == Color.WHITE:
                # Peón blanco (se mueve hacia arriba)
                vectors = [
                    # Movimiento de avance normal (una casilla)
                    MoveVector(0, 1, MovementType.FIXED, SpecialMoveConditions(
                        only_move=True,
                    )),

                    # Movimiento inicial (dos casillas)
                    MoveVector(0, 2, MovementType.FIXED, SpecialMoveConditions(
                        initial_only=True,
                        only_move=True,
                    )),

                    # Captura en diagonal
                    MoveVector(1, 1, MovementType.FIXED, SpecialMoveConditions(
                        only_capture=True,
                    )),
                    MoveVector(-1, 1, MovementType.FIXED, SpecialMoveConditions(
                        only_capture=True,
                    )),
                ]
            else:
                # Peón negro (se mueve hacia abajo)
                vectors = [
                    # Movimiento de avance normal (una casilla)
                    MoveVector(0, -1, MovementType.FIXED, SpecialMoveConditions(
                        only_move=True,
                    )),

                    # Movimiento inicial (dos casillas)
                    MoveVector(0, -2, MovementType.FIXED, SpecialMoveConditions(
                        initial_only=True,
                        only_move=True,
                    )),

                    # Captura en diagonal
                    MoveVector(1, -1, MovementType.FIXED, SpecialMoveConditions(
                        only_capture=True,
                    )),
                    MoveVector(-1, -1, MovementType.FIXED, SpecialMoveConditions(
                        only_capture=True,
                    )),
                ]
        else:
            vectors = []

        return vectors


@dataclass
class Move:
    piece: Piece
    col: Col
    row: Row


@singleton
@dataclass
class Control:
    selected_piece: Optional[Piece] = None
    moves: List[Move] = field(default_factory=list)

control = Control()

pieces = {
    "white_king": Piece(PieceType.KING, Color.WHITE, Row.R1, Col.E),
    "white_queen": Piece(PieceType.QUEEN, Color.WHITE, Row.R1, Col.D),
    "white_rook1": Piece(PieceType.ROOK, Color.WHITE, Row.R1, Col.A),
    "white_rook2": Piece(PieceType.ROOK, Color.WHITE, Row.R1, Col.H),
    "white_bishop1": Piece(PieceType.BISHOP, Color.WHITE, Row.R1, Col.C),
    "white_bishop2": Piece(PieceType.BISHOP, Color.WHITE, Row.R1, Col.F),
    "white_knight1": Piece(PieceType.KNIGHT, Color.WHITE, Row.R1, Col.B),
    "white_knight2": Piece(PieceType.KNIGHT, Color.WHITE, Row.R1, Col.G),
    "white_pawn1": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.A),
    "white_pawn2": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.B),
    "white_pawn3": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.C),
    "white_pawn4": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.D),
    "white_pawn5": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.E),
    "white_pawn6": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.F),
    "white_pawn7": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.G),
    "white_pawn8": Piece(PieceType.PAWN, Color.WHITE, Row.R2, Col.H),
    "black_king": Piece(PieceType.KING, Color.BLACK, Row.R8, Col.E),
    "black_queen": Piece(PieceType.QUEEN, Color.BLACK, Row.R8, Col.D),
    "black_rook1": Piece(PieceType.ROOK, Color.BLACK, Row.R8, Col.A),
    "black_rook2": Piece(PieceType.ROOK, Color.BLACK, Row.R8, Col.H),
    "black_bishop1": Piece(PieceType.BISHOP, Color.BLACK, Row.R8, Col.C),
    "black_bishop2": Piece(PieceType.BISHOP, Color.BLACK, Row.R8, Col.F),
    "black_knight1": Piece(PieceType.KNIGHT, Color.BLACK, Row.R8, Col.B),
    "black_knight2": Piece(PieceType.KNIGHT, Color.BLACK, Row.R8, Col.G),
    "black_pawn1": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.A),
    "black_pawn2": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.B),
    "black_pawn3": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.C),
    "black_pawn4": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.D),
    "black_pawn5": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.E),
    "black_pawn6": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.F),
    "black_pawn7": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.G),
    "black_pawn8": Piece(PieceType.PAWN, Color.BLACK, Row.R7, Col.H),
}


class Cell(Label):
    def __init__(self, col: Col, row: Row, **kwargs):
        super().__init__(**kwargs)
        self._prev_background = None
        self._piece: Optional[Piece] = None
        self.col = col
        self.row = row
        self.styles.background = Color.LIGHT_GRAY.value if (ord(row.value) + ord(col.value)) % 2 == 0 else Color.DARK_GRAY.value
        self.styles.color = Color.BLACK.value
        self.classes = "cell"

    def add_piece(self, piece: Piece):
        self._piece = piece
        self.update(piece.piece_type.value[0 if piece.color == Color.WHITE else 1])

    def on_event(self, event: events.Event) -> Coroutine[Any, Any, None]:
        if isinstance(event, events.Enter):
            self._prev_background = self.styles.background
            self.styles.background = Color.RED.value

        if isinstance(event, events.Leave):
            self.styles.background = self._prev_background

        if isinstance(event, events.Click):
            for sibling in self.visible_siblings:
                if isinstance(sibling, Cell):
                    sibling.styles.background = Color.LIGHT_GRAY.value if (ord(sibling.row.value) + ord(sibling.col.value)) % 2 == 0 else Color.DARK_GRAY.value
            if self._piece is not None:
                if (control.moves and self._piece.color != control.moves[-1].piece.color) or (not control.moves and self._piece.color == Color.WHITE):
                    self._prev_background = self.styles.background = Color.GREEN.value
                    for vector in self._piece.movement_vectors:
                        siblings = self.possible_cells(vector)
                        for sibling in siblings:
                            sibling.styles.background = Color.BLUE.value

        return super().on_event(event)

    def possible_cells(self, vector: MoveVector) -> Generator['Cell', Any, None]:
        if vector.special_conditions is not None and vector.special_conditions.initial_only and self._piece in [move.piece for move in control.moves]:
            return
        i = 1
        while True:
            actual_vector = vector * i
            chr_col = chr(ord(self.col.value) + actual_vector.dx)
            chr_row = chr(ord(self.row.value) + actual_vector.dy)
            if chr_col not in [col.value for col in Col] or chr_row not in [row.value for row in Row]:
                break
            for sibling in self.visible_siblings:
                if not isinstance(sibling, Cell):
                    continue
                if sibling.col.value == chr_col and sibling.row.value == chr_row:
                    if sibling._piece is not None:
                        if sibling._piece.color != self._piece.color:
                            if vector.special_conditions is not None and not vector.special_conditions.only_move:
                                yield sibling
                            return
                        else:
                            return
                    if vector.special_conditions is not None and not vector.special_conditions.only_capture:
                        yield sibling
            if vector.movement_type == MovementType.FIXED:
                break
            i += 1

    def __rich_repr__(self):
        yield self.col.value + self.row.value


class MyApp(App):
    CSS_PATH = "textual.css"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Container(classes="main"):
            with Container(classes="board"):
                for i in range(7, -1, -1):
                    for j in range(8):
                        col: Col = list(Col)[j]
                        row: Row = list(Row)[i]
                        cell = Cell(col, row)
                        for key, value in pieces.items():
                            if value.row == row and value.col == col:
                                cell.add_piece(value)
                                break
                        yield cell

            with Container(classes="table_container"):

                moves_table = DataTable()
                moves_table.add_columns("Move", "White", "Black")
                moves_table.add_row("1", "e4", "e5")
                moves_table.add_row("2", "Nf3", "Nc6")
                moves_table.add_row("3", "Bb5", "a6")
                moves_table.add_row("4", "Ba4", "Nf6")
                yield moves_table

MyApp().run()