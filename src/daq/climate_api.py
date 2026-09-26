"""
Capa de Adquisición de Datos Climáticos (DAQ) con Mecanismo de Caché Local.

Responsabilidad Única:
Consultar la API pública de Open-Meteo para obtener las variables meteorológicas horarias
de Uribia (La Guajira, Colombia).

Buenas Prácticas Implementadas:
- Principio de Resiliencia: Si la red falla o está saturada, intenta leer del caché local.
- Caché Determinista: Evita realizar llamadas duplicadas a la API para la misma fecha.
- Conversión explícita a UTC-5 (hora local de Colombia).
- Manejo estricto de excepciones de red y HTTP.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import requests

from config.settings import WINDPESHI_LOCATION, CACHE_DATA_DIR


class ClimateDataClient:
    """Cliente para la extracción de datos meteorológicos horarios con caché."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, target_date: str) -> Path:
        """Genera la ruta determinista del archivo de caché según la fecha."""
        return self.cache_dir / f"climate_uribia_{target_date}.json"

    def fetch_daily_weather(self, target_date: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Obtiene los datos meteorológicos horarios para Uribia en la fecha dada.

        Args:
            target_date: Fecha en formato 'YYYY-MM-DD'.
            force_refresh: Si es True, ignora el caché y consulta la API directamente.

        Returns:
            pd.DataFrame con 24 filas (una por cada hora) con las variables meteorológicas.
        """
        cache_path = self._get_cache_path(target_date)

        # 1. Revisar si tenemos los datos en caché
        if not force_refresh and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._parse_json_to_dataframe(data, target_date)
            except Exception as e:
                print(f"[!] Advertencia: No se pudo leer el caché local ({e}). Consultando API externa...")

        # 2. Si no hay caché o se forzó refresco, consultar la API externa
        data = self._request_from_api(target_date)

        # Guardar en caché para futuras ejecuciones
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[!] Advertencia: No se pudo guardar la respuesta en caché: {e}")

        return self._parse_json_to_dataframe(data, target_date)

    def _request_from_api(self, target_date: str) -> Dict[str, Any]:
        """Realiza la petición HTTP GET a Open-Meteo con los parámetros específicos de Uribia."""
        params = {
            "latitude": WINDPESHI_LOCATION["latitude"],
            "longitude": WINDPESHI_LOCATION["longitude"],
            "start_date": target_date,
            "end_date": target_date,
            "hourly": [
                "wind_speed_10m",
                "wind_speed_100m",
                "wind_direction_10m",
                "temperature_2m",
                "surface_pressure",
                "direct_normal_irradiance",
                "global_tilted_irradiance",
                "shortwave_radiation",
            ],
            "timezone": WINDPESHI_LOCATION["timezone"],  # America/Bogota
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=12)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Error al consultar la API meteorológica para Uribia ({target_date}): {e}"
            ) from e

    def _parse_json_to_dataframe(self, json_data: Dict[str, Any], target_date: str) -> pd.DataFrame:
        """
        Normaliza el JSON de Open-Meteo en un DataFrame canónico de 24 horas.
        Garantiza nombres estandarizados y tipos numéricos adecuados.
        """
        if "hourly" not in json_data:
            raise ValueError(f"Respuesta inválida de la API meteorológica: falta clave 'hourly'.")

        hourly = json_data["hourly"]
        timestamps = hourly.get("time", [])

        # Open-Meteo retorna la velocidad en km/h por defecto si no se especifica wind_speed_unit.
        # Convertimos km/h a m/s dividiendo por 3.6
        speed_10m_raw = hourly.get("wind_speed_10m", [])
        speed_100m_raw = hourly.get("wind_speed_100m", [])
        units = json_data.get("hourly_units", {})

        is_kmh_10 = units.get("wind_speed_10m") == "km/h"
        is_kmh_100 = units.get("wind_speed_100m") == "km/h"

        def to_ms(values, is_kmh):
            if is_kmh:
                return [round(v / 3.6, 2) if v is not None else None for v in values]
            return [round(v, 2) if v is not None else None for v in values]

        speed_10m_ms = to_ms(speed_10m_raw, is_kmh_10)
        speed_100m_ms = to_ms(speed_100m_raw, is_kmh_100) if speed_100m_raw else [None] * len(timestamps)

        # Radiación solar GHI (Global Horizontal Irradiance) en W/m²
        # Para pasar W/m² horario a kWh/m² en esa hora: (W/m² * 1h) / 1000
        ghi_wm2 = hourly.get("shortwave_radiation", [0.0] * len(timestamps))

        records = []
        for i, t_str in enumerate(timestamps):
            dt = datetime.fromisoformat(t_str)
            records.append({
                "timestamp": t_str,
                "hour": dt.hour,
                "wind_speed_10m_ms": speed_10m_ms[i],
                "wind_speed_100m_api_ms": speed_100m_ms[i],
                "wind_direction_deg": hourly.get("wind_direction_10m", [None] * len(timestamps))[i],
                "temperature_c": hourly.get("temperature_2m", [None] * len(timestamps))[i],
                "surface_pressure_hpa": hourly.get("surface_pressure", [None] * len(timestamps))[i],
                "solar_irradiance_ghi_wm2": ghi_wm2[i] if i < len(ghi_wm2) else 0.0,
            })

        df = pd.DataFrame(records)
        return df
