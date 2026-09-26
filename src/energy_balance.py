"""
Módulo de Orquestación del Balance Energético Diario y Factibilidad.
Ubicación: Uribia (La Guajira, Colombia).

Responsabilidades Principales:
1. Coordinar la extracción climática (con caché) para Uribia.
2. Calcular densidades horarias del aire y extrapolar el viento al buje (100m).
3. Evaluar la curva de potencia real del aerogenerador para generar la serie de 24h.
4. Modelar la demanda horaria de la empresa/planta industrial.
5. Calcular el balance energético neto (excedentes, déficit, autonomía y cobertura).
6. Exportar resultados tabulares y generar la gráfica comparativa.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import pytz

from config.settings import WINDPESHI_LOCATION, TURBINE_SPECS, INDUSTRIAL_DEMAND, PROCESSED_DATA_DIR
from src.daq.climate_api import ClimateDataClient
from src.domain.wind_physics import WindPhysicsEngine
from src.domain.demand_model import IndustrialDemandModel
from visualization.energy_plots import plot_energy_balance_curve


@dataclass
class EnergyBalanceResult:
    """Contenedor de métricas y veredicto del balance energético diario."""
    target_date: str
    energia_producida_total_kwh: float
    energia_demanda_total_kwh: float
    cobertura_diaria_pct: float
    autonomia_nominal_horas: float
    autonomia_nominal_dias: float
    excedente_total_kwh: float
    deficit_total_kwh: float
    horas_con_excedente: int
    horas_con_deficit: int
    densidad_aire_promedio_kg_m3: float
    velocidad_viento_buje_promedio_ms: float
    ghi_total_kwh_m2_dia: float
    plot_path: Optional[str] = None

    def formatted_summary(self) -> str:
        """Presentación profesional para consola o informe de ingeniería."""
        sep = "=" * 80
        sub_sep = "-" * 80
        return f"""
{sep}
   INFORME DE BALANCE ENERGÉTICO Y FACTIBILIDAD DIARIA - URIBIA (LA GUAJIRA)
{sep}
Fecha Evaluada:             {self.target_date}
Ubicación:                  {WINDPESHI_LOCATION['name']} (Lat: {WINDPESHI_LOCATION['latitude']}, Lon: {WINDPESHI_LOCATION['longitude']})
Tecnología de Generación:   {TURBINE_SPECS['model_name']} ({TURBINE_SPECS['rated_power_kw'] / 1000:.1f} MW, Buje a {TURBINE_SPECS['hub_height_m']}m)

--- 1. VARIABLES CLIMÁTICAS PROMEDIO ---
* Velocidad media del viento a buje: {self.velocidad_viento_buje_promedio_ms:.2f} m/s
* Densidad media del aire (ρ):       {self.densidad_aire_promedio_kg_m3:.3f} kg/m³
* Radiación Solar Global (GHI):      {self.ghi_total_kwh_m2_dia:.2f} kWh/m²/día

--- 2. BALANCE DIARIO DE ENERGÍA ---
* Generación Eólica Total (E_prod):  {self.energia_producida_total_kwh:,.1f} kWh/día ({self.energia_producida_total_kwh / 1000:.2f} MWh/día)
* Demanda Industrial Total (E_dem):  {self.energia_demanda_total_kwh:,.1f} kWh/día ({self.energia_demanda_total_kwh / 1000:.2f} MWh/día)
* Balance Neto Global:               {self.energia_producida_total_kwh - self.energia_demanda_total_kwh:+,.1f} kWh/día

--- 3. MÉTRICAS DE SUSTENTABILIDAD Y AUTONOMÍA ---
* Cobertura Diaria:                  {self.cobertura_diaria_pct:.1f}%
* Autonomía Nominal Continua:        {self.autonomia_nominal_horas:.1f} Horas ({self.autonomia_nominal_dias:.2f} Días de operación)
* Horas con Excedente Energético:    {self.horas_con_excedente} de 24 horas (Total Excedentes: {self.excedente_total_kwh:,.1f} kWh)
* Horas con Déficit (Red / Batería): {self.horas_con_deficit} de 24 horas (Total Déficit: {self.deficit_total_kwh:,.1f} kWh)

--- 4. DIAGNÓSTICO PARA ALMACENAMIENTO (BESS / RESPALDO) ---
{self._generate_bess_recommendation()}
{sub_sep}
Gráfico Generado en: {self.plot_path or 'No generado'}
{sep}
"""

    def _generate_bess_recommendation(self) -> str:
        if self.deficit_total_kwh == 0:
            return "-> Sistema 100% autosuficiente en esta jornada: No requiere energía de la red eléctrica."
        elif self.cobertura_diaria_pct >= 100.0:
            return (
                f"-> Generación diaria global superior a la demanda ({self.cobertura_diaria_pct:.1f}%).\n"
                f"   Con un sistema de almacenamiento en baterías (BESS) de al menos {self.deficit_total_kwh:,.0f} kWh,\n"
                f"   la empresa alcanzaría un 100% de autonomía aislada sin respaldo de la red eléctrica."
            )
        else:
            return (
                f"-> Se requiere respaldo de la red o generador de apoyo ({self.deficit_total_kwh:,.0f} kWh necesarios).\n"
                f"   La energía eólica cubrió el {self.cobertura_diaria_pct:.1f}% del proceso industrial."
            )


class EnergyBalancePipeline:
    """Orquestador del flujo integral de balance energético."""

    def __init__(
        self,
        climate_client: Optional[ClimateDataClient] = None,
        physics_engine: Optional[WindPhysicsEngine] = None,
        demand_model: Optional[IndustrialDemandModel] = None,
    ):
        self.climate_client = climate_client or ClimateDataClient()
        self.physics_engine = physics_engine or WindPhysicsEngine()
        self.demand_model = demand_model or IndustrialDemandModel()

    def run(
        self,
        target_date: Optional[str] = None,
        nominal_power_kw: Optional[float] = None,
        operating_hours: Optional[int] = None,
        generate_plot: bool = True,
    ) -> Tuple[EnergyBalanceResult, pd.DataFrame]:
        """
        Ejecuta el pipeline completo para la fecha y parámetros indicados.

        Args:
            target_date: Fecha 'YYYY-MM-DD'. Si es None, toma la fecha actual en La Guajira.
            nominal_power_kw: Potencia de la maquinaria activa en kW.
            operating_hours: Horas diarias de operación.
            generate_plot: Si es True, guarda el gráfico comparativo PNG.

        Returns:
            (EnergyBalanceResult, pd.DataFrame detallado de 24 horas)
        """
        if not target_date:
            tz = pytz.timezone(WINDPESHI_LOCATION["timezone"])
            target_date = datetime.now(tz).strftime("%Y-%m-%d")

        # 1. Extracción de datos climáticos (con caché)
        df_weather = self.climate_client.fetch_daily_weather(target_date)

        # 2. Vector de demanda industrial
        hourly_demand = self.demand_model.generate_hourly_demand(
            nominal_power_kw=nominal_power_kw,
            operating_hours=operating_hours
        )

        # 3. Procesamiento físico hora a hora
        records = []
        for i, row in df_weather.iterrows():
            hour = int(row["hour"])
            v10 = row["wind_speed_10m_ms"]
            temp_c = row["temperature_c"]
            pres_hpa = row["surface_pressure_hpa"]
            ghi = row.get("solar_irradiance_ghi_wm2", 0.0)

            # A. Densidad real del aire ρ
            rho = self.physics_engine.calculate_air_density(temp_c, pres_hpa)

            # B. Extrapolación de viento a la altura del buje (100m)
            # Si la API ya proveyó wind_speed_100m, lo usamos de referencia o extrapolamos vía ley logarítmica
            if row.get("wind_speed_100m_api_ms") is not None:
                v_hub = row["wind_speed_100m_api_ms"]
            else:
                v_hub = self.physics_engine.extrapolate_wind_speed_log(v10)

            # C. Potencia generada por el aerogenerador (kW)
            p_gen_kw, op_zone = self.physics_engine.calculate_turbine_power(v_hub, rho)

            # D. Demanda industrial en esta hora
            p_dem_kw = hourly_demand[hour]

            # E. Balance neto horario
            net_balance_kw = round(p_gen_kw - p_dem_kw, 2)
            excedente = max(0.0, net_balance_kw)
            deficit = max(0.0, -net_balance_kw)

            records.append({
                "timestamp": row["timestamp"],
                "hour": hour,
                "wind_speed_10m_ms": v10,
                "wind_speed_hub_ms": v_hub,
                "temperature_c": temp_c,
                "surface_pressure_hpa": pres_hpa,
                "air_density_kg_m3": rho,
                "solar_irradiance_ghi_wm2": ghi,
                "wind_power_generated_kw": p_gen_kw,
                "industrial_demand_kw": p_dem_kw,
                "net_balance_kw": net_balance_kw,
                "excedente_kw": excedente,
                "deficit_kw": deficit,
                "operating_zone": op_zone,
            })

        df_integrated = pd.DataFrame(records)

        # 4. Cálculo de Totales y Métricas de Factibilidad
        e_producida = round(float(df_integrated["wind_power_generated_kw"].sum()), 2)
        e_demanda = round(float(df_integrated["industrial_demand_kw"].sum()), 2)
        excedente_total = round(float(df_integrated["excedente_kw"].sum()), 2)
        deficit_total = round(float(df_integrated["deficit_kw"].sum()), 2)

        # Radiación solar acumulada diaria (GHI): sum(W/m² * 1h) / 1000 = kWh/m²/día
        ghi_total = round(float(df_integrated["solar_irradiance_ghi_wm2"].sum()) / 1000.0, 2)

        cobertura_pct = round((e_producida / e_demanda) * 100.0, 2) if e_demanda > 0 else 0.0

        # Autonomía Nominal: Horas completas que la energía generada sostiene el ritmo promedio de consumo
        promedio_demanda_hora = e_demanda / 24.0 if e_demanda > 0 else 1.0
        autonomia_horas = round(e_producida / promedio_demanda_hora, 2)
        autonomia_dias = round(autonomia_horas / 24.0, 2)

        horas_excedente = int((df_integrated["net_balance_kw"] >= 0).sum())
        horas_deficit = 24 - horas_excedente

        rho_media = round(float(df_integrated["air_density_kg_m3"].mean()), 3)
        v_media = round(float(df_integrated["wind_speed_hub_ms"].mean()), 2)

        summary_dict = {
            "target_date": target_date,
            "energia_producida_total_kwh": e_producida,
            "energia_demanda_total_kwh": e_demanda,
            "cobertura_diaria_pct": cobertura_pct,
            "autonomia_nominal_horas": autonomia_horas,
            "autonomia_nominal_dias": autonomia_dias,
            "excedente_total_kwh": excedente_total,
            "deficit_total_kwh": deficit_total,
            "horas_con_excedente": horas_excedente,
            "horas_con_deficit": horas_deficit,
            "densidad_aire_promedio_kg_m3": rho_media,
            "velocidad_viento_buje_promedio_ms": v_media,
            "ghi_total_kwh_m2_dia": ghi_total,
        }

        # 5. Generar visualización gráfica si se solicita
        plot_path_str = None
        if generate_plot:
            try:
                plot_file = plot_energy_balance_curve(df_integrated, summary_dict)
                plot_path_str = str(plot_file)
            except Exception as e:
                print(f"[!] No se pudo generar la gráfica: {e}")

        # 6. Guardar archivo CSV procesado en data/processed/
        processed_csv_path = PROCESSED_DATA_DIR / f"energy_balance_{target_date}.csv"
        df_integrated.to_csv(processed_csv_path, index=False, encoding="utf-8")

        result = EnergyBalanceResult(
            target_date=target_date,
            energia_producida_total_kwh=e_producida,
            energia_demanda_total_kwh=e_demanda,
            cobertura_diaria_pct=cobertura_pct,
            autonomia_nominal_horas=autonomia_horas,
            autonomia_nominal_dias=autonomia_dias,
            excedente_total_kwh=excedente_total,
            deficit_total_kwh=deficit_total,
            horas_con_excedente=horas_excedente,
            horas_con_deficit=horas_deficit,
            densidad_aire_promedio_kg_m3=rho_media,
            velocidad_viento_buje_promedio_ms=v_media,
            ghi_total_kwh_m2_dia=ghi_total,
            plot_path=plot_path_str,
        )

        return result, df_integrated
