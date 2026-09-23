"""
Servidor Web Local para el Dashboard Interactivo de Windpeshi.

Responsabilidad Única:
Servir los archivos estáticos de la interfaz web (HTML, CSS, JS) y exponer
el endpoint /api/evaluate que ejecuta el pipeline de datos para la fecha seleccionada.
"""

import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import webbrowser
import sys

# Asegurar que el servidor encuentre los módulos del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from src.pipeline import WindpeshiPipeline

WEB_DIR = PROJECT_ROOT / "web"
PORT = 8050


class WindpeshiWebHandler(BaseHTTPRequestHandler):
    """Manejador de peticiones HTTP para el Dashboard Web."""

    pipeline = WindpeshiPipeline()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # ----------------------------------------------------------------------
        # ENDPOINT API: /api/evaluate?date=YYYY-MM-DD
        # ----------------------------------------------------------------------
        if path == "/api/evaluate":
            query_params = parse_qs(parsed_url.query)
            date_param = query_params.get("date", [None])[0]

            if not date_param:
                self.send_error_response(400, "Debe proporcionar el parámetro 'date' (YYYY-MM-DD).")
                return

            try:
                # Ejecutar el pipeline para la fecha seleccionada
                result, df_integrated, quality_report = self.pipeline.run(target_date=date_param)

                # Convertir DataFrame a lista de diccionarios para JSON
                hourly_records = df_integrated.to_dict(orient="records")

                # Reemplazar valores NaN por None para JSON válido
                for row in hourly_records:
                    for k, v in row.items():
                        if isinstance(v, float) and (v != v):  # Chequeo de NaN
                            row[k] = None

                payload = {
                    "success": True,
                    "target_date": result.target_date,
                    "verdict": result.verdict,
                    "operating_hours": result.operating_hours,
                    "hours_sub_cut_in": result.hours_sub_cut_in,
                    "hours_super_cut_out": result.hours_super_cut_out,
                    "avg_integrated_speed_ms": round(result.avg_integrated_speed_ms, 2),
                    "historical_p50_benchmark_ms": round(result.historical_p50_benchmark_ms, 2),
                    "estimated_daily_energy_mwh": round(result.estimated_daily_energy_mwh, 2),
                    "reasons": result.reasons,
                    "quality": {
                        "total_records": quality_report.total_records,
                        "valid_records": quality_report.valid_records,
                        "rejected_records": quality_report.rejected_records,
                        "valid_percentage": round(quality_report.valid_percentage, 1),
                        "anomalies": quality_report.anomalies_detected,
                    },
                    "hourly_data": hourly_records,
                }

                self.send_json_response(200, payload)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_error_response(500, f"Error interno al procesar el pipeline: {str(e)}")
            return

        # ----------------------------------------------------------------------
        # ENDPOINT DE DESCARGA: /api/download?type=csv|excel&date=YYYY-MM-DD
        # ----------------------------------------------------------------------
        if path == "/api/download":
            query_params = parse_qs(parsed_url.query)
            file_type = query_params.get("type", ["csv"])[0]
            date_param = query_params.get("date", [None])[0]

            if not date_param:
                self.send_error_response(400, "Parámetro 'date' requerido.")
                return

            from config.settings import PROCESSED_DATA_DIR
            if file_type == "excel":
                target_file = PROCESSED_DATA_DIR / f"integrated_{date_param}.xlsx"
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                target_file = PROCESSED_DATA_DIR / f"integrated_{date_param}.csv"
                content_type = "text/csv; charset=utf-8"

            # Si el archivo aún no existe, ejecutamos el pipeline para crearlo
            if not target_file.exists():
                try:
                    self.pipeline.run(target_date=date_param)
                except Exception as e:
                    self.send_error_response(500, f"Error al generar archivo para descarga: {e}")
                    return

            if target_file.exists():
                with open(target_file, "rb") as f:
                    file_bytes = f.read()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Disposition", f'attachment; filename="{target_file.name}"')
                self.send_header("Content-Length", str(len(file_bytes)))
                self.end_headers()
                self.wfile.write(file_bytes)
                return
            else:
                self.send_error_response(404, f"No se pudo generar el archivo {target_file.name}")
                return

        # ----------------------------------------------------------------------
        # SERVIR ARCHIVOS ESTÁTICOS (HTML, CSS, JS)
        # ----------------------------------------------------------------------
        if path == "/" or path == "":
            file_path = WEB_DIR / "index.html"
        else:
            # Eliminar la barra inicial
            rel_path = path.lstrip("/")
            file_path = WEB_DIR / rel_path

        if file_path.exists() and file_path.is_file():
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error_response(404, f"Archivo no encontrado: {path}")

    def send_json_response(self, status_code: int, data: dict):
        # default=str garantiza serialización segura de Timestamps de pandas y tipos de numpy
        response_bytes = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_response(self, status_code: int, message: str):
        self.send_json_response(status_code, {"success": False, "error": message})

    def log_message(self, format, *args):
        # Silenciar logs verbosos de cada petición estática para mantener limpia la consola
        pass


def run_server(port: int = PORT):
    # Asegurar compatibilidad de consola en Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    server_address = ("", port)
    httpd = HTTPServer(server_address, WindpeshiWebHandler)
    url = f"http://localhost:{port}"

    print("=" * 70)
    print(f"[+] DASHBOARD WEB WINDPESHI ACTIVO EN: {url}")
    print("   Presiona Ctrl+C en esta consola para detener el servidor.")
    print("=" * 70)

    # Abrir navegador automáticamente
    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Servidor detenido por el usuario.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
