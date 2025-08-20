import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import config

# si vas a usar SFTP:
try:
    from utils.sftp_client import SFTPReader
except Exception:
    SFTPReader = None

class ClonadorExcel:
    def __init__(self, carpeta_json_local: str, carpeta_salida: str, modo_ingesta: int = None):
        self.carpeta_json = Path(carpeta_json_local)
        self.carpeta_salida = Path(carpeta_salida)
        self.modo_ingesta = modo_ingesta or config.MODO_INGESTA_DEFAULT
        self.logger = logging.getLogger("ClonadorExcel")

    # ---- Entrada LOCAL ----
    def _iter_local(self):
        for p in self.carpeta_json.glob("*.json"):
            yield p.name, p.read_bytes()

    # ---- Entrada SFTP (streaming) ----
    def _iter_sftp(self):
        if SFTPReader is None:
            raise RuntimeError("Paramiko/SFTP no disponible. Instala 'paramiko'.")
        with SFTPReader(config.SFTP_HOST, config.SFTP_PORT, config.SFTP_USER, config.SFTP_PASS) as s:
            for fname, data in s.iter_json_files(config.SFTP_DIR_JSONS):
                yield fname, data

    def _procesar_json_anidado(self, nombre_archivo: str, raw_bytes: bytes):
        try:
            text = raw_bytes.decode("utf-8")
            obj = json.loads(text)
        except Exception as e:
            self.logger.warning(f"No se pudo leer '{nombre_archivo}'. Error: {e}")
            return None

        # Soporta ambos formatos:
        # 1) lista de documentos
        # 2) {"fecha_procesado": "...", "documentos":[...]}
        documentos = None
        if isinstance(obj, list):
            documentos = obj
        elif isinstance(obj, dict) and isinstance(obj.get("documentos"), list):
            documentos = obj["documentos"]

        if not documentos:
            self.logger.warning(f"'{nombre_archivo}' no contiene datos válidos.")
            return None

        fila = {}
        primero = documentos[0]
        fila['id_cargue_origen'] = primero.get('id_cargue', 'No encontrado')
        fila['nombre_archivo_origen'] = nombre_archivo

        for documento in documentos:
            if not isinstance(documento, dict):
                continue
            tipo = documento.get('tipo_documento', 'sin_tipo')
            datos = documento.get('data_extraida', {}) or {}
            if isinstance(datos, dict):
                for k, v in datos.items():
                    fila[f"{tipo}_{k}"] = v
        return fila

    def generar_excel(self):
        # Selección de fuente
        if self.modo_ingesta == 2:
            iterador = self._iter_sftp()
            self.logger.info("Leyendo JSON desde SFTP (streaming)...")
        else:
            iterador = self._iter_local()
            self.logger.info("Leyendo JSON desde carpeta local...")

        filas = []
        for nombre, raw in iterador:
            self.logger.info(f"Procesando {nombre}...")
            fila = self._procesar_json_anidado(nombre, raw)
            if fila:
                filas.append(fila)

        if not filas:
            self.logger.error("No se pudo extraer información de los JSON.")
            return False

        df = pd.DataFrame(filas)
        cols_ref = ['id_cargue_origen', 'nombre_archivo_origen']
        otras = [c for c in df.columns if c not in cols_ref]
        df = df[cols_ref + sorted(otras)]

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_archivo = f"clon_json_{timestamp}.xlsx"
        ruta_salida = Path(config.CARPETA_EXCEL_CLON) / nombre_archivo

        Path(config.CARPETA_EXCEL_CLON).mkdir(parents=True, exist_ok=True)
        df.to_excel(ruta_salida, index=False, engine='openpyxl')

        self.logger.info(f"Excel generado: {ruta_salida} ({len(df)} filas, {len(df.columns)} columnas)")
        return True
