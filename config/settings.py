"""
Configuración centralizada del Sistema de Evaluación Eólica y Balance Energético.
Ubicación: Parque Eólico Windpeshi / Uribia (La Guajira, Colombia).

Buenas prácticas de arquitectura:
- Centralizar constantes físicas, parámetros geográficos y umbrales operacionales.
- Evitar 'números mágicos' dispersos en el código.
"""

from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Rutas de datos y almacenamiento
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DATA_DIR = DATA_DIR / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Crear directorios clave automáticamente si no existen
for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DATA_DIR, REPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. PARÁMETROS GEOGRÁFICOS - URIBIA / WINDPESHI (LA GUAJIRA)
# -----------------------------------------------------------------------------
WINDPESHI_LOCATION = {
    "name": "Parque Eólico Windpeshi (Uribia, La Guajira)",
    "latitude": 11.7167,       # Coordenadas representativas de Uribia
    "longitude": -72.2667,
    "elevation_m": 15.0,       # Altura aproximada sobre el nivel del mar
    "timezone": "America/Bogota",
    "surface_roughness_z0": 0.03,  # Rugosidad z0 (m): Terreno llano semidesértico con vegetación baja
}

# -----------------------------------------------------------------------------
# 2. CONSTANTES FÍSICAS Y TERMODINÁMICAS
# -----------------------------------------------------------------------------
PHYSICS = {
    "R_SPECIFIC_AIR": 287.058,     # Constante específica para aire seco [J / (kg * K)]
    "STANDARD_AIR_DENSITY": 1.225, # Densidad estándar ISA a nivel del mar (15 °C, 1013.25 hPa) [kg/m³]
    "REF_HEIGHT_ANEMOMETER": 10.0, # Altura estándar de medición meteorológica [m]
}

# -----------------------------------------------------------------------------
# 3. ESPECIFICACIONES TÉCNICAS DEL AEROGENERADOR (Turbina Industrial de 3.0 MW)
# -----------------------------------------------------------------------------
TURBINE_SPECS = {
    "model_name": "Turbina Industrial Clase IEC S (Adaptada a Vientos Alisios)",
    "rated_power_kw": 3000.0,      # Potencia Nominal Máxima: 3 MW = 3,000 kW
    "hub_height_m": 100.0,         # Altura del buje (torre) [m]
    "rotor_diameter_m": 112.0,     # Diámetro del rotor [m]
    "swept_area_m2": 9852.0,       # Área barrida A = pi * (D/2)^2 [m²]
    "power_coefficient_cp": 0.42,  # Coeficiente aerodinámico medio en régimen cúbico
    "cut_in_speed_ms": 3.5,        # Velocidad de arranque [m/s]
    "rated_speed_ms": 12.0,        # Velocidad para alcanzar potencia nominal [m/s]
    "cut_out_speed_ms": 25.0,      # Velocidad de corte por seguridad mecánica [m/s]
}

# -----------------------------------------------------------------------------
# 4. PARÁMETROS DE LA DEMANDA INDUSTRIAL (EMPRESA / PROCESO)
# -----------------------------------------------------------------------------
INDUSTRIAL_DEMAND = {
    "nominal_power_kw": 1200.0,    # Carga activa instalada (kW)
    "operating_hours": 24,         # Horas de operación al día (24h para proceso continuo)
    "base_load_factor": 0.85,      # Factor de carga promedio respecto al nominal
    "profile_type": "continuous",  # 'continuous' (planta 24/7) o 'day_shift' (turnos diurnos)
}
