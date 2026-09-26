"""
Punto de Entrada Principal (CLI) - Sistema de Evaluación Eólica y Balance Energético.
Parque Windpeshi / Uribia (La Guajira, Colombia).

Uso:
    python main.py                                  # Ejecuta el flujo con fecha actual
    python main.py --mode balance                   # Ejecuta el balance de factibilidad energética
    python main.py --mode balance --power 1500      # Con 1500 kW de maquinaria industrial
    python main.py --date 2026-03-24                # Fecha específica
"""

import argparse
import sys
from datetime import datetime
import pandas as pd
import pytz

from config.settings import WINDPESHI_LOCATION, INDUSTRIAL_DEMAND
from src.pipeline import WindpeshiPipeline
from src.energy_balance import EnergyBalancePipeline

# Forzar codificación UTF-8 en la salida estándar de Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def print_hourly_breakdown(df_integrated: pd.DataFrame):
    """Muestra una tabla legible en consola con el desglose hora a hora."""
    print("\n" + "-" * 78)
    print(f"{'HORA':^6} | {'SENSOR (m/s)':^14} | {'PRONÓSTICO (m/s)':^16} | {'P50 HIST. (m/s)':^15} | {'ESTADO':^15}")
    print("-" * 78)

    for _, row in df_integrated.iterrows():
        hour_str = f"{int(row['hour']):02d}:00"
        sensor_v = f"{row['sensor_speed_mean_ms']:.2f}" if pd.notna(row.get('sensor_speed_mean_ms')) else "N/A"
        fc_v = f"{row['forecast_wind_speed_ms']:.2f}" if pd.notna(row.get('forecast_wind_speed_ms')) else "N/A"
        p50_v = f"{row['hist_wind_p50']:.2f}" if pd.notna(row.get('hist_wind_p50')) else "N/A"

        val = row.get('sensor_speed_mean_ms') or row.get('forecast_wind_speed_ms') or 0.0
        if val < 3.5:
            status = "Sub-Arranque"
        elif val >= 12.0:
            status = "Generación Máx"
        else:
            status = "Operación Óptima"

        print(f"{hour_str:^6} | {sensor_v:^14} | {fc_v:^16} | {p50_v:^15} | {status:^15}")
    print("-" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Evaluación Eólica y Factibilidad Energética - Windpeshi / Uribia"
    )

    tz = pytz.timezone(WINDPESHI_LOCATION["timezone"])
    default_date = datetime.now(tz).strftime("%Y-%m-%d")

    parser.add_argument(
        "--mode",
        type=str,
        choices=["evaluation", "balance"],
        default="balance",
        help="Modo de ejecución: 'evaluation' (evaluación básica de viento) o 'balance' (balance energético industrial)"
    )

    parser.add_argument(
        "--date",
        type=str,
        default=default_date,
        help=f"Fecha a evaluar en formato YYYY-MM-DD (por defecto: {default_date})"
    )

    parser.add_argument(
        "--power",
        type=float,
        default=INDUSTRIAL_DEMAND["nominal_power_kw"],
        help=f"Potencia activa de maquinaria industrial en kW (por defecto: {INDUSTRIAL_DEMAND['nominal_power_kw']} kW)"
    )

    parser.add_argument(
        "--hours",
        type=int,
        default=INDUSTRIAL_DEMAND["operating_hours"],
        help=f"Horas de operación diaria de la planta (por defecto: {INDUSTRIAL_DEMAND['operating_hours']} h)"
    )

    args = parser.parse_args()

    if args.mode == "balance":
        print(f"\n[*] Ejecutando Pipeline de Balance Energético Diario para Uribia ({args.date})...")
        pipeline = EnergyBalancePipeline()
        result, df_hourly = pipeline.run(
            target_date=args.date,
            nominal_power_kw=args.power,
            operating_hours=args.hours,
            generate_plot=True
        )
        print(result.formatted_summary())
    else:
        pipeline = WindpeshiPipeline()
        result, df_integrated, quality_report = pipeline.run(target_date=args.date)
        print_hourly_breakdown(df_integrated)
        print(result.formatted_summary())


if __name__ == "__main__":
    main()
