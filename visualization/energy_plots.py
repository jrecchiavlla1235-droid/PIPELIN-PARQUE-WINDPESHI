"""
Módulo de Visualización Gráfica para el Balance Energético.

Responsabilidad Única:
Generar gráficos comparativos profesionales de la curva de generación eólica (24h)
frente a la demanda industrial de la empresa.

Buenas Prácticas:
- Visualización con paleta de colores limpia y moderna.
- Doble área de sombreado:
  * Verde suave: Excedentes (energía almacenable en baterías BESS o inyectable).
  * Salmón/Rojo suave: Déficit (requiere respaldo de red o descarga de baterías).
- Guardado en formatos de alta resolución (PNG a 300 DPI) para reportes técnicos.
"""

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from config.settings import REPORTS_DIR


def plot_energy_balance_curve(
    df_balance: pd.DataFrame,
    summary_metrics: dict,
    output_filename: Optional[str] = None
) -> Path:
    """
    Construye y guarda la gráfica de la curva de potencia 24h: Generación vs. Demanda.

    Args:
        df_balance: DataFrame con columnas 'hour', 'wind_power_generated_kw', 'industrial_demand_kw'.
        summary_metrics: Diccionario con KPIs calculados (cobertura, excedente, etc.).
        output_filename: Nombre del archivo de salida. Si es None, usa la fecha.

    Returns:
        Path del archivo de imagen generado.
    """
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=150)

    hours = df_balance["hour"].values
    gen_kw = df_balance["wind_power_generated_kw"].values
    dem_kw = df_balance["industrial_demand_kw"].values

    # 1. Curva de Demanda Industrial
    ax.plot(
        hours, dem_kw,
        label="Demanda Industrial de la Planta (kW)",
        color="#D9534F",
        linewidth=2.5,
        linestyle="--",
        marker="o",
        markersize=4,
    )

    # 2. Curva de Generación Eólica
    ax.plot(
        hours, gen_kw,
        label="Generación Eólica Estimada (kW)",
        color="#0275D8",
        linewidth=2.8,
        marker="s",
        markersize=4,
    )

    # 3. Áreas de Excedente y Déficit
    # Excedente: Generación > Demanda
    ax.fill_between(
        hours, gen_kw, dem_kw,
        where=(gen_kw >= dem_kw),
        interpolate=True,
        color="#5CB85C",
        alpha=0.35,
        label="Excedente de Generación (Carga BESS / Inyección)",
    )

    # Déficit: Generación < Demanda
    ax.fill_between(
        hours, gen_kw, dem_kw,
        where=(gen_kw < dem_kw),
        interpolate=True,
        color="#F0AD4E",
        alpha=0.35,
        label="Déficit Energético (Respaldo Red / Descarga BESS)",
    )

    # Configuración de Ejes y Títulos
    target_date = summary_metrics.get("target_date", "Fecha de Evaluación")
    cobertura = summary_metrics.get("cobertura_diaria_pct", 0.0)
    e_gen = summary_metrics.get("energia_producida_total_kwh", 0.0)
    e_dem = summary_metrics.get("energia_demanda_total_kwh", 0.0)
    autonomia = summary_metrics.get("autonomia_nominal_horas", 0.0)

    ax.set_title(
        f"Evaluación de Factibilidad y Balance Energético - Uribia (La Guajira)\n"
        f"Fecha: {target_date} | Cobertura Diaria: {cobertura:.1f}% | Autonomía: {autonomia:.1f} horas",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Hora del Día (Local UTC-5)", fontsize=11, fontweight="semibold")
    ax.set_ylabel("Potencia (kW / kWh por hora)", fontsize=11, fontweight="semibold")
    ax.set_xticks(range(0, 24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=9)
    ax.set_xlim(-0.3, 23.3)

    # Cuadro de Resumen Ejecutivo en el gráfico
    text_kpi = (
        f"Generación Total: {e_gen:,.0f} kWh/día\n"
        f"Demanda Total: {e_dem:,.0f} kWh/día\n"
        f"Excedentes: {summary_metrics.get('excedente_total_kwh', 0):,.0f} kWh\n"
        f"Déficit: {summary_metrics.get('deficit_total_kwh', 0):,.0f} kWh"
    )
    ax.text(
        0.02, 0.95, text_kpi,
        transform=ax.transAxes,
        fontsize=9.5,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#CCC", alpha=0.9),
    )

    ax.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.9, fontsize=9.5)
    plt.tight_layout()

    if output_filename is None:
        output_filename = f"balance_energetico_uribia_{target_date}.png"

    save_path = REPORTS_DIR / output_filename
    fig.savefig(save_path, dpi=300)
    plt.close(fig)

    return save_path
