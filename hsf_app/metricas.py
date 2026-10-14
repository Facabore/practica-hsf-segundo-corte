"""Métricas de una ejecución y las fórmulas de sus indicadores (Anexo 3 §12)."""

import time
from dataclasses import dataclass, field


@dataclass
class MetricasEjecucion:
    lecturas_recibidas: int = 0
    lecturas_validas: int = 0
    lecturas_anomalas: int = 0
    errores_validacion: int = 0
    errores_adquisicion: int = 0
    errores_persistencia: int = 0
    desconexiones: int = 0
    tiempos_recuperacion_s: list = field(default_factory=list)
    tiempo_inicio_s: float = field(default_factory=time.time)
    tiempo_fin_s: float = field(default_factory=time.time)

    def resumen(self) -> dict:
        total_eventos = self.lecturas_recibidas + self.errores_adquisicion
        datos_validos_pct = (
            round(100 * self.lecturas_validas / self.lecturas_recibidas, 2)
            if self.lecturas_recibidas
            else 0.0
        )
        errores_totales = self.errores_validacion + self.errores_adquisicion + self.errores_persistencia
        tasa_errores_pct = (
            round(100 * errores_totales / total_eventos, 2) if total_eventos else 0.0
        )
        tiempo_recuperacion_promedio_s = (
            round(sum(self.tiempos_recuperacion_s) / len(self.tiempos_recuperacion_s), 2)
            if self.tiempos_recuperacion_s
            else 0.0
        )
        return {
            "lecturas_recibidas": self.lecturas_recibidas,
            "lecturas_validas": self.lecturas_validas,
            "lecturas_anomalas": self.lecturas_anomalas,
            "errores_validacion": self.errores_validacion,
            "errores_adquisicion": self.errores_adquisicion,
            "errores_persistencia": self.errores_persistencia,
            "desconexiones": self.desconexiones,
            "datos_validos_pct": datos_validos_pct,
            "tasa_errores_pct": tasa_errores_pct,
            "tiempo_recuperacion_promedio_s": tiempo_recuperacion_promedio_s,
            "duracion_total_s": round(self.tiempo_fin_s - self.tiempo_inicio_s, 2),
        }
