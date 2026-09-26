"""
Modelado de Demanda Eléctrica Industrial.

Responsabilidad Única:
Construir el perfil de carga horario (kWh por hora) de la empresa consumidora
a partir de parámetros de maquinaria activa, turnos y factor de carga.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from config.settings import INDUSTRIAL_DEMAND


class IndustrialDemandModel:
    """Modelo de simulación y parametrización de demanda eléctrica industrial."""

    def __init__(self, demand_config: Optional[Dict[str, Any]] = None):
        self.config = demand_config or INDUSTRIAL_DEMAND
        self.nominal_kw = self.config.get("nominal_power_kw", 1200.0)
        self.operating_hours = self.config.get("operating_hours", 24)
        self.base_load_factor = self.config.get("base_load_factor", 0.85)
        self.profile_type = self.config.get("profile_type", "continuous")

    def generate_hourly_demand(
        self,
        nominal_power_kw: Optional[float] = None,
        operating_hours: Optional[int] = None,
        profile_type: Optional[str] = None
    ) -> List[float]:
        """
        Genera el vector de 24 valores horarios de demanda (kW / kWh por hora).

        Args:
            nominal_power_kw: Potencia nominal de maquinaria activa en kW.
            operating_hours: Número de horas al día que opera la maquinaria principal.
            profile_type: 'continuous' (planta continua 24h) o 'day_shift' (turnos diurnos).

        Returns:
            Lista de 24 valores de consumo en kW (al ser intervalos de 1 hora, kW == kWh).
        """
        p_nom = nominal_power_kw if nominal_power_kw is not None else self.nominal_kw
        hours_active = operating_hours if operating_hours is not None else self.operating_hours
        p_type = profile_type if profile_type is not None else self.profile_type

        hourly_kw = []

        for h in range(24):
            if p_type == "continuous" or hours_active >= 24:
                # Proceso continuo (desalinizadora, planta minera o bombeo constante)
                # Pequeña oscilación estocástica realista (+/- 5%) debida al arranque/parada de motores secundarios
                variation = 1.0 + 0.05 * math_sin_wave(h)
                kw = p_nom * self.base_load_factor * variation
            else:
                # Planta con turno específico (ej. activa entre las 6:00 y las 6:00 + hours_active)
                start_h = 6
                end_h = min(24, start_h + hours_active)
                if start_h <= h < end_h:
                    # En operación activa
                    variation = 1.0 + 0.06 * math_sin_wave(h)
                    kw = p_nom * self.base_load_factor * variation
                else:
                    # En espera (cargas pasivas, iluminación, sistemas auxiliares ~ 10%)
                    kw = p_nom * 0.10

            hourly_kw.append(round(kw, 2))

        return hourly_kw

    def calculate_total_daily_demand(self, hourly_demand: List[float]) -> float:
        """Suma la energía total demandada en las 24 horas (kWh/día)."""
        return round(float(sum(hourly_demand)), 2)


def math_sin_wave(hour: int) -> float:
    """Onda armónica suave para emular fluctuaciones diarias sin aleatoriedad no reproducible."""
    import math
    return math.sin(2 * math.pi * hour / 24)
