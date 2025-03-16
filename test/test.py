from typing import Literal

MiVariable = Literal["val1", "val2"]

def asignar_valor(variable: MiVariable, valor: MiVariable) -> MiVariable:
    return valor

mi_variable: MiVariable = "val1"
mi_variable = asignar_valor(mi_variable, "val2")  # Válido

mi_variable = asignar_valor(mi_variable, "val3")  # MyPy detectará un error aquí