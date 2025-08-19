import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

class ClonadorExcel:
    def __init__(self, carpeta_json: str, carpeta_salida: str):
        self.carpeta_json = Path(carpeta_json)
        self.carpeta_salida = Path(carpeta_salida)
        self.logger = logging.getLogger("ClonadorExcel")

    def _cargar_json(self, ruta_archivo_json: Path):
        """Carga el JSON y devuelve (lista_documentos, fecha_procesado|None). Soporta ambos formatos."""
        try:
            with open(ruta_archivo_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(f"No se pudo leer '{ruta_archivo_json}'. Error: {e}")
            return None, None

        # Formato nuevo: dict con 'documentos'
        if isinstance(data, dict) and "documentos" in data and isinstance(data["documentos"], list):
            lista = data["documentos"]
            fecha_proc = data.get("fecha_procesado")
            return lista, fecha_proc

        # Formato anterior: lista en la raíz
        if isinstance(data, list):
            return data, None

        self.logger.warning(f"Formato JSON no reconocido en '{ruta_archivo_json}'. Se omite.")
        return None, None

    def _procesar_json_anidado(self, ruta_archivo_json: Path):
        """
        De un archivo JSON (en cualquiera de los 2 formatos), extrae una sola fila consolidada:
        - id_cargue_origen (primer documento)
        - nombre_archivo_origen (nombre del .json)
        - fecha_procesado_origen (si viene en formato nuevo)
        - todas las claves de data_extraida prefijadas por tipo_documento_
        """
        lista_de_documentos, fecha_procesado = self._cargar_json(ruta_archivo_json)
        if not lista_de_documentos:
            return None

        fila_consolidada = {
            "nombre_archivo_origen": ruta_archivo_json.name
        }

        # Si hay fecha_procesado (formato nuevo), guardarla
        if fecha_procesado:
            fila_consolidada["fecha_procesado_origen"] = fecha_procesado

        # Tomar id_cargue del primer documento válido que lo tenga
        id_cargue = None
        for doc in lista_de_documentos:
            if isinstance(doc, dict):
                id_cargue = doc.get("id_cargue")
                if id_cargue:
                    break
        fila_consolidada["id_cargue_origen"] = id_cargue if id_cargue else "No encontrado"

        # Volcar data_extraida de cada documento con prefijo del tipo_documento
        for documento in lista_de_documentos:
            if not isinstance(documento, dict):
                continue
            tipo_doc = documento.get('tipo_documento', 'sin_tipo')
            datos_anidados = documento.get('data_extraida', {}) or {}
            if isinstance(datos_anidados, dict):
                for clave, valor in datos_anidados.items():
                    nueva_clave = f"{tipo_doc}_{clave}"
                    fila_consolidada[nueva_clave] = valor

        return fila_consolidada

    def generar_excel(self):
        if not self.carpeta_json.exists():
            self.logger.error(f"La carpeta '{self.carpeta_json}' no existe.")
            return False

        archivos_json = [f for f in self.carpeta_json.glob("*.json")]
        if not archivos_json:
            self.logger.warning(f"No se encontraron JSON en '{self.carpeta_json}'.")
            return False

        filas = []
        for archivo in archivos_json:
            self.logger.info(f"Procesando {archivo.name}...")
            fila = self._procesar_json_anidado(archivo)
            if fila:
                filas.append(fila)

        if not filas:
            self.logger.error("No se pudo extraer información de los JSON.")
            return False

        df = pd.DataFrame(filas)

        # Orden: columnas de referencia primero
        columnas_ref = ['id_cargue_origen', 'nombre_archivo_origen']
        if 'fecha_procesado_origen' in df.columns:
            columnas_ref.insert(1, 'fecha_procesado_origen')  # si existe, va después de id_cargue

        otras = [c for c in df.columns if c not in columnas_ref]
        df = df[columnas_ref + sorted(otras)]

        # Nombre dinámico con fecha y hora
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_archivo = f"clon_json_{timestamp}.xlsx"
        ruta_salida = self.carpeta_salida / nombre_archivo

        self.carpeta_salida.mkdir(parents=True, exist_ok=True)
        df.to_excel(ruta_salida, index=False, engine='openpyxl')

        self.logger.info(f"Excel generado: {ruta_salida} ({len(df)} filas, {len(df.columns)} columnas)")
        return True
