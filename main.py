"""
Punto de Entrada Principal (CLI) - Sistema de Evaluación Eólica del Parque Windpeshi.

Uso:
    python main.py                  # Ejecuta con la fecha de hoy
    python main.py --date 2026-03-24 # Ejecuta para una fecha específica
"""

import argparse
import sys
from datetime import datetime
import pandas as pd
import pytz
from config.settings import WINDPESHI_LOCATION
from src.pipeline import WindpeshiPipeline

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

        # Comparar si la velocidad efectiva es óptima
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
        description="Sistema de Adquisición e Integración de Datos - Parque Eólico Windpeshi"
    )
    
    # Fecha por defecto: hoy en La Guajira
    tz = pytz.timezone(WINDPESHI_LOCATION["timezone"])
    default_date = datetime.now(tz).strftime("%Y-%m-%d")
    
    parser.add_argument(
        "--date",
        type=str,
        default=default_date,
        help=f"Fecha a evaluar en formato YYYY-MM-DD (por defecto: {default_date})"
    )

    args = parser.parse_args()

    # Instanciar y ejecutar el pipeline
    pipeline = WindpeshiPipeline()
    result, df_integrated, quality_report = pipeline.run(target_date=args.date)

    # Imprimir tabla hora a hora
    print_hourly_breakdown(df_integrated)

    # Imprimir informe final de evaluación
    print(result.formatted_summary())


if __name__ == "__main__":
    main()
