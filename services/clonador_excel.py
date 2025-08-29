# services/clonador_excel.py
import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import config

# SFTP (opcional)
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

    # ---- Entrada SFTP (streaming, sin descargar) ----
    def _iter_sftp(self):
        if SFTPReader is None:
            raise RuntimeError("Paramiko/SFTP no disponible. Instala 'paramiko'.")
        with SFTPReader(config.SFTP_HOST, config.SFTP_PORT, config.SFTP_USER, config.SFTP_PASS) as s:
            for fname, data in s.iter_json_files(config.SFTP_DIR_JSONS):
                yield fname, data

    # ---- Parser de un JSON (lista o {documentos:[...]}) ----
    def _procesar_json_anidado(self, nombre_json: str, raw_bytes: bytes):
        try:
            text = raw_bytes.decode("utf-8")
            obj = json.loads(text)
        except Exception as e:
            self.logger.warning(f"No se pudo leer '{nombre_json}'. Error: {e}")
            return None

        # 1) lista de documentos  2) dict con clave 'documentos'
        documentos = obj if isinstance(obj, list) else obj.get("documentos") if isinstance(obj, dict) else None
        if not documentos:
            self.logger.warning(f"'{nombre_json}' no contiene datos válidos.")
            return None

        fila = {}
        # Metadata origen
        fila['nombre_json_origen'] = nombre_json

        # id_cargue (del primer doc válido)
        primero = next((d for d in documentos if isinstance(d, dict)), {})
        fila['id_cargue_origen'] = primero.get('id_cargue', 'No encontrado')

        # --- Buscar un nombre_archivo válido y extraer NN / Numero credito / Cedula ---
        def _parse_tripleta(na: str):
            """
            Formato esperado (ejemplos):
              492799_1_772024254676_19143788_SOLICITUD CREDITO.pdf
              700017_11_772025329689_19301051_AMORTIZACION.pdf
            NN = partes[0], Numero credito = partes[2], Cedula = partes[3]
            """
            if not isinstance(na, str) or not na:
                return None, None, None, None
            base = na.rsplit(".", 1)[0]              # sin extensión
            partes = base.split("_")
            if len(partes) >= 4:
                nn = partes[0]
                numcred = partes[2]
                ced = partes[3]
                return nn, numcred, ced, base
            return None, None, None, base

        # Prioriza el del primer documento
        candidatos = []
        na_primero = primero.get("nombre_archivo")
        if na_primero:
            candidatos.append(na_primero)
        # Agrega el resto como fallback
        for d in documentos:
            na = (d or {}).get("nombre_archivo")
            if na:
                candidatos.append(na)

        nn_val = numcred_val = ced_val = None
        nombre_archivo_origen = None
        for na in candidatos:
            nn, numcred, ced, base = _parse_tripleta(na)
            if nn and numcred and ced:
                nn_val, numcred_val, ced_val = nn, numcred, ced
                nombre_archivo_origen = na
                break

        # Setea nombre_archivo_origen (para retrocompatibilidad con reestructurador)
        # Si no se encontró ninguno, deja el nombre del JSON para no romper, pero ya avisamos.
        fila['nombre_archivo_origen'] = nombre_archivo_origen or nombre_json

        # Guarda tripleta si se obtuvo
        if nn_val and numcred_val and ced_val:
            fila["NN"] = str(nn_val)
            fila["Numero credito"] = str(numcred_val)
            fila["Cedula"] = str(ced_val)
        else:
            self.logger.warning(
                f"No se pudo extraer NN/Numero credito/Cedula desde los nombres de archivo en '{nombre_json}'."
            )

        # --- Copiar todos los data_extraida ---
        for documento in documentos:
            if not isinstance(documento, dict):
                continue
            tipo = documento.get('tipo_documento', 'sin_tipo')
            datos = documento.get('data_extraida', {}) or {}
            if isinstance(datos, dict):
                for k, v in datos.items():
                    fila[f"{tipo}_{k}"] = v

        return fila

    # ---- Generar Excel de clonación ----
    def generar_excel(self):
        # Fuente de JSON
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

        # Ordenar dejando NN / Numero credito / Cedula primero si están presentes
        pref = ["NN", "Numero credito", "Cedula", "id_cargue_origen", "nombre_archivo_origen", "nombre_json_origen"]
        pref_presentes = [c for c in pref if c in df.columns]
        otras = [c for c in df.columns if c not in pref_presentes]
        df = df[pref_presentes + sorted(otras)]

        # Guardar
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_archivo = f"clon_json_{timestamp}.xlsx"
        ruta_salida = Path(config.CARPETA_EXCEL_CLON) / nombre_archivo

        Path(config.CARPETA_EXCEL_CLON).mkdir(parents=True, exist_ok=True)
        df.to_excel(ruta_salida, index=False, engine='openpyxl')

        self.logger.info(f"Excel generado: {ruta_salida} ({len(df)} filas, {len(df.columns)} columnas)")
        return True
