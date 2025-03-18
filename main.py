import io
import sys
from dataclasses import dataclass, field

from viztracer import VizTracer
from singleton_decorator import singleton
from enum import Enum
from json.encoder import INFINITY
from typing import List, Any, Coroutine, Optional, Generator, Tuple, Annotated, Dict
import rich
from rich import inspect as rich_inspect
from textual import events, log
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Label, DataTable

# tracer = VizTracer()
# tracer.start()

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
    capture_in_passing: bool = False # only can move if enemy piece is in the target cell


@dataclass
class MoveVector:
    dx: int
    dy: int
    movement_type: MovementType
    special_conditions: SpecialMoveConditions = field(default_factory=SpecialMoveConditions)

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
            direction = 1 if self.color == Color.WHITE else -1

            vectors = [
                # Movimiento de avance normal (una casilla)
                MoveVector(0, direction, MovementType.FIXED, SpecialMoveConditions(
                    only_move=True,
                )),

                # Movimiento inicial (dos casillas)
                MoveVector(0, 2 * direction, MovementType.FIXED, SpecialMoveConditions(
                    initial_only=True,
                    only_move=True,
                )),

                # Captura en diagonal
                MoveVector(1, direction, MovementType.FIXED, SpecialMoveConditions(
                    only_capture=True,
                )),
                MoveVector(-1, direction, MovementType.FIXED, SpecialMoveConditions(
                    only_capture=True,
                )),

                # Captura al paso
                MoveVector(1, direction, MovementType.FIXED, SpecialMoveConditions(
                    capture_in_passing=True,
                )),
                MoveVector(-1, direction, MovementType.FIXED, SpecialMoveConditions(
                    capture_in_passing=True,
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
    last_col: Col
    last_row: Row
    ate_piece: Optional[Piece] = None


@singleton
@dataclass
class Control:
    selected_cell: Optional['Cell'] = None
    moves: List[Move] = field(default_factory=list)
    en_passant_target: Optional['Cell'] = None
    cells: Dict[Tuple[Col, Row], Tuple['Cell', List['Cell']]] = field(default_factory=dict)

    def append_cell(self, cell: 'Cell'):
        self.cells[(cell.col, cell.row)] = cell, []

    def undo_last_move(self):
        if self.moves:
            last_move = self.moves.pop()
            target_cell = self.get_cell(last_move.col, last_move.row)
            original_cell = self.get_cell(last_move.last_col, last_move.last_row)
            if target_cell and original_cell:
                # Move the piece back to the original cell
                original_cell.add_piece(last_move.piece)
                # Remove the piece from the target cell
                if last_move.ate_piece:
                    target_cell.add_piece(last_move.ate_piece)
                else:
                    target_cell._piece = None
                    target_cell.update("")
                # Reset en_passant_target if necessary
                self.en_passant_target = None

    def get_cell(self, col, row):
        return self.cells.get((col, row))[0]

    def get_moves(self, col, row):
        return self.cells.get((col, row))[1]

    def reset_colors(self):
        for cell, _ in self.cells.values():
            cell.styles.background = Color.LIGHT_GRAY.value if (ord(cell.row.value) + ord(cell.col.value)) % 2 == 0 else Color.DARK_GRAY.value


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
        control.append_cell(self)

    def add_piece(self, piece: Piece):
        self._piece = piece
        # Update the piece's current position to this cell's position
        piece.col = self.col
        piece.row = self.row
        self.update(piece.piece_type.value[0 if piece.color == Color.WHITE else 1])

    def on_event(self, event: events.Event) -> Coroutine[Any, Any, None]:
        if isinstance(event, events.Enter):
            self._prev_background = self.styles.background
            self.styles.background = Color.RED.value

        if isinstance(event, events.Leave):
            self.styles.background = self._prev_background

        if isinstance(event, events.Click):
            def try_move():
                if control.selected_cell is not None:
                    for possible_cell in control.get_moves(self.col, self.row):
                        if possible_cell == control.selected_cell:
                            control.selected_cell.move_piece(self)
                            control.selected_cell = None
                            return
                    control.selected_cell = None

            control.reset_colors()

            if self._piece is not None and ( # jugador selecciona su propia pieza
                (
                    control.moves
                    and self._piece.color != control.moves[-1].piece.color
                ) or
                (
                    not control.moves
                    and self._piece.color == Color.WHITE
                )
            ):
                self._prev_background = self.styles.background = Color.GREEN.value
                control.selected_cell = self
                for cell in control.get_moves(self.col, self.row):
                    cell.styles.background = Color.BLUE.value
            else:
                try_move()


        return super().on_event(event)

    def computing_1(self, vector: MoveVector):
        # Verificar condición de movimiento inicial
        if (
                vector.special_conditions.initial_only
                and self._piece in [move.piece for move in control.moves]
        ):
            return

        i = 1
        while True:
            actual_vector = vector * i
            chr_col = chr(ord(self.col.value) + actual_vector.dx)
            chr_row = chr(ord(self.row.value) + actual_vector.dy)

            # Validar límites del tablero
            if (
                    chr_col not in [col.value for col in Col]
                    or chr_row not in [row.value for row in Row]
            ):
                break

            # Buscar celdas hermanas visibles
            for sibling in self.visible_siblings:
                if not isinstance(sibling, Cell):
                    continue

                if sibling.col.value == chr_col and sibling.row.value == chr_row:
                    # Caso 1: Celda ocupada
                    if sibling._piece is not None:
                        if sibling._piece.color != self._piece.color:
                            # Permitir captura si no es only_move
                            if (
                                    not vector.special_conditions.only_move
                            ):
                                yield sibling
                        return  # Bloquear más movimiento en esta dirección

                    # Caso 2: Celda vacía
                    else:
                        # Caso especial: Captura al paso
                        if vector.special_conditions.capture_in_passing:
                            if sibling == control.en_passant_target:
                                yield sibling
                        # Movimiento normal si no es only_capture
                        elif not vector.special_conditions.only_capture:
                            yield sibling

            # Controlar tipo de movimiento
            if vector.movement_type == MovementType.FIXED:
                break
            i += 1

    def compute_movements(self, vector: MoveVector, ignore_king=False):
        for cell in self.computing_1(vector):
            self.move_piece(cell)
            if ignore_king or king_is_safe():
                control.undo_last_move()
                yield cell
            else:
                control.undo_last_move()
                break


    def __rich_repr__(self):
        yield self.col.value + self.row.value

    def move_piece(self, target):
        piece = self._piece
        original_col = self.col
        original_row = self.row
        ate_piece = target.get_piece()
        control.moves.append(Move(piece, target.col, target.row, original_col, original_row, ate_piece))
        target.add_piece(piece)
        self._piece = None
        self.update("")

        # Manejar captura al paso
        if piece.piece_type == PieceType.PAWN and target == control.en_passant_target:
            # Calcular fila del peón capturado
            captured_row = str(int(target.row.value) - 1) if piece.color == Color.WHITE else str(int(target.row.value) + 1)

            # Buscar y eliminar el peón capturado
            for sibling in self.visible_siblings:
                if (isinstance(sibling, Cell) and
                        sibling.col.value == target.col.value and
                        sibling.row.value == captured_row):
                    sibling._piece = None
                    sibling.update("")
                    break

        # Resetear en_passant_target
        control.en_passant_target = None

        # Configurar nuevo en_passant_target si es movimiento doble
        if piece.piece_type == PieceType.PAWN:
            current_row = int(self.row.value)
            target_row = int(target.row.value)

            if abs(target_row - current_row) == 2:
                en_passant_row = str(current_row + (1 if piece.color == Color.WHITE else -1))
                for sibling in self.visible_siblings:
                    if (isinstance(sibling, Cell) and
                            sibling.col.value == self.col.value and
                            sibling.row.value == en_passant_row):
                        control.en_passant_target = sibling
                        break

    def get_piece(self):
        return self._piece


def king_is_safe() -> bool:
    return True
    # Si no hay movimientos, el rey está seguro
    if not control.moves:
        return True

    last_move = control.moves[-1]
    king_color = last_move.piece.color
    opponent_color = Color.WHITE if king_color == Color.BLACK else Color.BLACK

    # Encontrar la posición del rey actual
    king_position: Optional[Cell] = None
    for cell, _ in control.cells.values():
        piece = cell.get_piece()
        if piece and piece.piece_type == PieceType.KING and piece.color == king_color:
            king_position = cell
            break

    if not king_position:
        return False  # No debería ocurrir en un juego válido

    # Verificar si alguna pieza del oponente puede atacar al rey
    for cell, _ in control.cells.values():
        piece = cell.get_piece()
        if piece and piece.color == opponent_color:
            # Calcular movimientos posibles sin considerar la seguridad del rey oponente
            for vector in piece.movement_vectors:
                for target_cell in cell.compute_movements(vector, ignore_king=True):
                    if target_cell == king_position:
                        return False

    return True


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

                    for cell, moves in control.cells.values():
                        if cell.get_piece() is not None:
                            for vector in cell.get_piece().movement_vectors:
                                moves.extend(cell.compute_movements(vector))
                                log(moves) # porque en este segmento de codigo moves es una lista vacia?

            with Container(classes="table_container"):

                moves_table = DataTable()
                moves_table.add_columns("Move", "White", "Black")
                moves_table.add_row("1", "e4", "e5")
                moves_table.add_row("2", "Nf3", "Nc6")
                moves_table.add_row("3", "Bb5", "a6")
                moves_table.add_row("4", "Ba4", "Nf6")
                yield moves_table

MyApp().run()
# tracer.stop()
# tracer.save("trace.json")