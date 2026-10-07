"""Clasificación de lecturas en normal / anómalo (RF04)."""

from dataclasses import dataclass, field

from hsf_app.config import RANGOS_NORMALES


@dataclass
class ResultadoClasificacion:
    estado: str  # "normal" | "anomalo"
    variables_anomalas: list[str] = field(default_factory=list)


def clasificar_lectura(lectura: dict) -> ResultadoClasificacion:
    variables_anomalas = []
    for campo, (minimo, maximo) in RANGOS_NORMALES.items():
        valor = lectura[campo]
        if not (minimo <= valor <= maximo):
            variables_anomalas.append(campo)

    estado = "anomalo" if variables_anomalas else "normal"
    return ResultadoClasificacion(estado=estado, variables_anomalas=variables_anomalas)
