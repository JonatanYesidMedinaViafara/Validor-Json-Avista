# services/reestructurador_excel.py
import pandas as pd
from pathlib import Path
import logging

def convertir_a_entero_sin_notacion(valor):
    try:
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        if isinstance(valor, (int, str)) and str(valor).isdigit():
            return str(valor)
    except:
        pass
    return str(valor) if valor is not None else ""

class ReestructuradorExcel:
    def __init__(self, carpeta_excel_origen: str, carpeta_excel_destino: str):
        self.carpeta_excel_origen = Path(carpeta_excel_origen)
        self.carpeta_excel_destino = Path(carpeta_excel_destino)
        self.logger = logging.getLogger("ReestructuradorExcel")

    def _obtener_ultimo_excel(self):
        archivos = list(self.carpeta_excel_origen.glob("clon_json_*.xlsx"))
        if not archivos:
            self.logger.error("No se encontraron archivos clonados.")
            return None
        return max(archivos, key=lambda f: f.stat().st_mtime)

    def _upper_text_columns(self, df: pd.DataFrame, exclude=None) -> pd.DataFrame:
        exclude = set(exclude or [])
        out = df.copy()
        for col in out.columns:
            if col in exclude:
                continue
            if out[col].dtype == "object":
                out[col] = out[col].fillna("").apply(lambda x: x.upper() if isinstance(x, str) else x)
        return out

    def _normalizar_fechas_texto(self, df: pd.DataFrame) -> pd.DataFrame:
        meses = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06',
                 'JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
        def _norm(x):
            if not isinstance(x, str): return x
            up = x.upper().replace("-", "/")
            for k,v in meses.items():
                up = up.replace(f"/{k}/", f"/{v}/")
            return up
        for col in ["cedula_fecha_nacimiento","desprendible_nomina_vigencia"]:
            if col in df.columns:
                df[col] = df[col].apply(_norm)
        return df

    def _crear_nombres_completos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crea columnas 'X Nombre Completo' y 'X Firma Electrónica Nombre Completo' a partir
        de *_nombre_completo y *_nombre_firma_electronica. Elimina las columnas fuente.
        """
        df = df.copy()
        mapeo = {
            "Cedula Nombre Completo": ["cedula_nombre_completo"],
            "Libranza Nombre Completo": ["libranza_nombre_completo"],
            "Amortizacion Nombre Completo": ["amortizacion_nombre_completo"],
            "Solicitud Credito Nombre Completo": ["solicitud_credito_nombre_completo"],
            "Solicitud Fianza Nombre Completo": ["solicitud_fianza_nombre_completo"],
            "Seguro De Vida Nombre Completo": ["seguro_de_vida_nombre_completo"],
            "Datacredito Nombre Completo": ["datacredito_nombre_deudor"],
            "Formato Conocimiento Nombre Completo": ["formato_conocimiento_nombre_completo"],
            "Desprendible Nomina Nombre Completo": ["desprendible_nomina_nombre_completo"],

            "Libranza Firma Electrónica Nombre Completo": ["libranza_nombre_firma_electronica"],
            "Amortizacion Firma Electrónica Nombre Completo": ["amortizacion_nombre_firma_electronica"],
            "Solicitud Credito Firma Electrónica Nombre Completo": ["solicitud_credito_nombre_firma_electronica"],
            "Solicitud Fianza Firma Electrónica Nombre Completo": ["solicitud_fianza_nombre_firma_electronica"],
            "Formato Conocimiento Firma Electrónica Nombre Completo": ["formato_conocimiento_nombre_firma_electronica"],
            "Seguro De Vida Firma Electrónica Nombre Completo": ["seguro_de_vida_nombre_firma_electronica"],
        }

        # crear destino y recordar columnas fuente para borrarlas
        a_borrar = []
        for destino, fuentes in mapeo.items():
            for f in fuentes:
                if f in df.columns:
                    df[destino] = df[f]
                    a_borrar.append(f)

        # Limpieza prefijos de 2 letras + espacio en Desprendible
        col_dn = "Desprendible Nomina Nombre Completo"
        if col_dn in df.columns:
            df[col_dn] = df[col_dn].astype(str).str.replace(r'^[A-Z]{2}\s+', '', regex=True)

        # borrar fuentes
        if a_borrar:
            df.drop(columns=[c for c in a_borrar if c in df.columns], inplace=True, errors="ignore")

        return df

    def reestructurar(self):
        archivo = self._obtener_ultimo_excel()
        if not archivo:
            return False

        self.logger.info(f"Reestructurando archivo: {archivo.name}")
        df = pd.read_excel(archivo, dtype=str)

        if 'nombre_archivo_origen' not in df.columns:
            self.logger.error("La columna 'nombre_archivo_origen' no existe en el Excel.")
            return False
        # 1) Asegurar NN / Numero credito / Cedula
        necesarias = {"NN", "Numero credito", "Cedula"}
        if not necesarias.issubset(df.columns):
            # Solo si faltan, intentamos derivarlas de algún nombre_archivo de los documentos (si existiera)
            # En la clonación nueva ya no será necesario, pero dejamos este fallback.
            posibles_cols = [c for c in df.columns if c.endswith("_nombre_archivo")]
            nom = df[posibles_cols[0]].astype(str) if posibles_cols else None
            if nom is not None:
                base = nom.str.replace(r"\.pdf$", "", regex=True).str.split("_", expand=True)
                if base.shape[1] >= 4:
                    df.insert(0, "NN", base[0])
                    df.insert(1, "Numero credito", base[2])
                    df.insert(2, "Cedula", base[3])
        else:
            # Ya existen: garantizamos que son cadenas legibles
            for c in ["NN", "Numero credito", "Cedula"]:
                df[c] = df[c].astype(str)

        # 2) Fechas a texto normalizado (no tipar)
        df = self._normalizar_fechas_texto(df)

        # 3) Todo texto a MAYÚSCULA (excepto fechas ya normalizadas)
        df = self._upper_text_columns(df, exclude={"cedula_fecha_nacimiento","desprendible_nomina_vigencia"})

        # 4) Crear columnas 'Nombre Completo' (y firmantes) y eliminar las de origen
        df = self._crear_nombres_completos(df)

        # 5) Preservar llaves como texto legible
        for col in ["NN","Numero credito","Cedula"]:
            if col in df.columns:
                df[col] = df[col].apply(convertir_a_entero_sin_notacion)

        # 6) Tipar números donde aplique (sin tocar fechas ni llaves)
        columnas_excluir = {"cedula_fecha_nacimiento","desprendible_nomina_vigencia","NN","Numero credito","Cedula"}
        for col in df.columns:
            if col in columnas_excluir: 
                continue
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass

        # 7) Reordenar
        columnas = list(df.columns)
        nuevas = ['NN','Numero credito','Cedula']
        if 'id_cargue_origen' in columnas:
            nuevas.append('id_cargue_origen')
        for c in columnas:
            if c not in nuevas:
                nuevas.append(c)
        df = df[nuevas]

        # 8) Guardar
        self.carpeta_excel_destino.mkdir(parents=True, exist_ok=True)
        nuevo_nombre = archivo.name.replace(".xlsx", "_reestructurado.xlsx")
        ruta_nueva = self.carpeta_excel_destino / nuevo_nombre
        df.to_excel(ruta_nueva, index=False, engine='openpyxl')
        self.logger.info(f"Archivo reestructurado guardado en: {ruta_nueva}")
        return True
