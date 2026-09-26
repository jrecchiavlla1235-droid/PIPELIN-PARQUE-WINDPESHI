"""
Dominio de Física Eólica y Aerodinámica.

Responsabilidad Única:
Implementar los modelos termodinámicos y aerodinámicos de conversión de energía:
1. Cálculo de densidad del aire real ρ(T, P) mediante la ley de gas ideal.
2. Extrapolación del perfil de viento por ley logarítmica de Prandtl.
3. Modelo físico y curva de potencia del aerogenerador considerando las 4 zonas operativas.
"""

import math
from typing import Tuple, Dict, Any
from config.settings import PHYSICS, TURBINE_SPECS, WINDPESHI_LOCATION


class WindPhysicsEngine:
    """Motor de cálculo físico para recursos eólicos y generación de potencia."""

    def __init__(self, turbine_specs: Dict[str, Any] = TURBINE_SPECS):
        self.specs = turbine_specs
        self.z0 = WINDPESHI_LOCATION["surface_roughness_z0"]
        self.hub_height = self.specs["hub_height_m"]
        self.swept_area = self.specs["swept_area_m2"]
        self.cp = self.specs["power_coefficient_cp"]
        self.rated_power_kw = self.specs["rated_power_kw"]
        self.cut_in = self.specs["cut_in_speed_ms"]
        self.rated_speed = self.specs["rated_speed_ms"]
        self.cut_out = self.specs["cut_out_speed_ms"]

    @staticmethod
    def calculate_air_density(temp_c: float, pressure_hpa: float) -> float:
        """
        Calcula la densidad real del aire (ρ) en kg/m³.

        Fórmula termodinámica:
            ρ = P / (R_aire * T)
        Donde:
            P: Presión en Pascales (1 hPa = 100 Pa)
            R_aire = 287.058 J/(kg*K)
            T: Temperatura en Kelvin (T_c + 273.15)

        En Uribia (cálido y costero), ρ suele rondar entre 1.15 y 1.18 kg/m³.
        """
        if temp_c is None or pressure_hpa is None:
            return PHYSICS["STANDARD_AIR_DENSITY"]

        temp_k = temp_c + 273.15
        pressure_pa = pressure_hpa * 100.0
        rho = pressure_pa / (PHYSICS["R_SPECIFIC_AIR"] * temp_k)
        return round(rho, 4)

    def extrapolate_wind_speed_log(
        self,
        v_ref: float,
        z_ref: float = PHYSICS["REF_HEIGHT_ANEMOMETER"],
        z_target: float = None,
    ) -> float:
        """
        Extrapola la velocidad del viento desde una altura de referencia (ej. 10m)
        hasta la altura del buje de la turbina (ej. 100m) usando la ley logarítmica de Prandtl:

            v(z) = v(z_ref) * [ ln(z / z0) / ln(z_ref / z0) ]

        Args:
            v_ref: Velocidad en m/s a la altura de referencia.
            z_ref: Altura de medición (por defecto 10m).
            z_target: Altura objetivo (por defecto altura del buje de la turbina).

        Returns:
            Velocidad extrapolada en m/s a la altura del buje.
        """
        if v_ref is None or v_ref < 0:
            return 0.0

        target_h = z_target if z_target is not None else self.hub_height

        # Si la altura ya es la del buje, no extrapolamos
        if abs(target_h - z_ref) < 1e-3:
            return round(v_ref, 2)

        numerator = math.log(target_h / self.z0)
        denominator = math.log(z_ref / self.z0)

        extrapolated_v = v_ref * (numerator / denominator)
        return round(extrapolated_v, 2)

    def calculate_turbine_power(self, wind_speed_ms: float, air_density: float) -> Tuple[float, str]:
        """
        Calcula la potencia eléctrica instantánea (kW) producida por el aerogenerador
        incorporando la densidad real del aire y la curva de potencia con control de paso (pitch).

        Fórmula aerodinámica base:
            P_aero = 0.5 * ρ * A * v³ * Cp  (en Watts)
            P_kw = P_aero / 1000

        Zonas operativas:
        - Zona I (v < v_cut_in): Potencia = 0 kW (fuerza insuficiente para iniciar rotación).
        - Zona II (v_cut_in <= v < v_rated): Régimen cúbico proporcional a ρ * v³ * Cp.
        - Zona III (v_rated <= v <= v_cut_out): Potencia nominal constante regulada por pitch.
        - Zona IV (v > v_cut_out): Potencia = 0 kW (frenado por seguridad ante ráfagas extremas).

        Returns:
            (potencia_kw, zona_operativa)
        """
        if wind_speed_ms is None or wind_speed_ms < self.cut_in:
            return 0.0, "Sub-Cut-In (Parado)"

        if wind_speed_ms > self.cut_out:
            return 0.0, "Super-Cut-Out (Freno Emergencia)"

        # Factor de corrección de densidad respecto a la estándar
        density_ratio = air_density / PHYSICS["STANDARD_AIR_DENSITY"]

        # Zona III: Si supera o iguala la velocidad nominal corregida por densidad
        effective_rated_speed = self.rated_speed * (1.0 / (density_ratio ** (1.0 / 3.0)))

        if wind_speed_ms >= effective_rated_speed:
            return self.rated_power_kw, "Potencia Nominal (Pitch Control)"

        # Zona II: Generación aerodinámica óptima
        # P = 0.5 * rho * A * v^3 * Cp (en Watts) -> convertir a kW (/ 1000)
        power_watts = 0.5 * air_density * self.swept_area * (wind_speed_ms ** 3) * self.cp
        power_kw = power_watts / 1000.0

        # No superar nunca la potencia nominal del generador eléctrico
        power_kw = min(power_kw, self.rated_power_kw)

        return round(power_kw, 2), "Operación Óptima (Régimen Cúbico)"
