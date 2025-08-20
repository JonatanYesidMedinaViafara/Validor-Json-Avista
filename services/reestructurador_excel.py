import pandas as pd
from pathlib import Path
import logging

def _clean_spaces_up(s):
    if not isinstance(s, str):
        return ""
    return " ".join(s.strip().upper().split())

def separar_nombre_datacredito(nombre_completo: str):
    if not isinstance(nombre_completo, str) or not nombre_completo.strip():
        return ""
    partes = nombre_completo.strip().split()
    if len(partes) == 1:
        return partes[0].upper()
    if len(partes) == 2:
        return f"{partes[1].upper()} {partes[0].upper()}"
    if len(partes) == 3:
        return f"{partes[2].upper()} {partes[0].upper()} {partes[1].upper()}"
    primer_ap = partes[0].upper()
    segundo_ap = partes[1].upper()
    nombres = " ".join(p.upper() for p in partes[2:])
    return f"{nombres} {primer_ap} {segundo_ap}".strip()

def _strip_desprendible_prefijo(nombre: str):
    """
    Quita prefijos de 1-3 letras al inicio (p.ej. 'ag ', 'ij ', 'pt ') que no pertenecen al nombre.
    Solo si el primer token es 100% letras y longitud <=3.
    """
    if not isinstance(nombre, str):
        return ""
    s = nombre.strip()
    if not s:
        return ""
    # normaliza espacios y mayúsculas al final
    tokens = s.split()
    if tokens and tokens[0].isalpha() and len(tokens[0]) <= 3:
        tokens = tokens[1:]  # quita prefijo
    return _clean_spaces_up(" ".join(tokens))

def convertir_a_entero_sin_notacion(valor):
    try:
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        s = str(valor)
        if s.isdigit():
            return s
        if "e" in s.lower():
            return str(int(float(s)))
    except:
        pass
    return valor

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

    def reestructurar(self):
        archivo = self._obtener_ultimo_excel()
        if not archivo:
            return False
        self.logger.info(f"Reestructurando archivo: {archivo.name}")

        df = pd.read_excel(archivo, dtype=str)
        if 'nombre_archivo_origen' not in df.columns:
            self.logger.error("La columna 'nombre_archivo_origen' no existe en el Excel.")
            return False

        # NN / Número crédito / Cédula desde el nombre del .json
        nuevo_df = df['nombre_archivo_origen'].str.replace('.json', '', regex=False).str.split('_', expand=True)
        nuevo_df.columns = ['NN', 'Numero credito', 'Cedula']
        for i, col in enumerate(['NN', 'Numero credito', 'Cedula']):
            df.insert(i, col, nuevo_df[col])
        df.drop(columns=['nombre_archivo_origen'], inplace=True)

        # *_nombre_completo  -> "<Prefijo> Nombre Completo"
        cols_nc = [c for c in df.columns if c.endswith("_nombre_completo")]
        for col in cols_nc:
            prefijo = col.replace("_nombre_completo", "").replace("_", " ").title()
            nuevo = f"{prefijo} Nombre Completo"
            df[nuevo] = df[col].apply(_clean_spaces_up)
            df.drop(columns=[col], inplace=True)

        # Datacrédito (apellidos primero -> nombre completo estándar)
        if "datacredito_nombre_deudor" in df.columns:
            df["Datacredito Nombre Completo"] = df["datacredito_nombre_deudor"].apply(separar_nombre_datacredito).apply(_clean_spaces_up)
            df.drop(columns=["datacredito_nombre_deudor"], inplace=True)

        # *_nombre_firma_electronica -> "<Prefijo> Firma Electrónica Nombre Completo"
        cols_firma = [c for c in df.columns if c.endswith("_nombre_firma_electronica")]
        for col in cols_firma:
            prefijo = col.replace("_nombre_firma_electronica", "").replace("_", " ").title()
            nuevo = f"{prefijo} Firma Electrónica Nombre Completo"
            df[nuevo] = df[col].apply(_clean_spaces_up)
            df.drop(columns=[col], inplace=True)

        # Limpieza especial: Desprendible Nomina Nombre Completo (quitar prefijo de 1-3 letras)
        col_despr = "Desprendible Nomina Nombre Completo"
        if col_despr in df.columns:
            df[col_despr] = df[col_despr].apply(_strip_desprendible_prefijo)

        # *_numero_documento -> "<Prefijo> Cedula"
        cols_doc = [c for c in df.columns if c.endswith("_numero_documento")]
        for col in cols_doc:
            prefijo = col.replace("_numero_documento", "").replace("_", " ").title()
            df.rename(columns={col: f"{prefijo} Cedula"}, inplace=True)

        # Fechas: "-" -> "/" y meses texto -> número
        meses = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06',
                 'JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
        def normalizar_fecha(s):
            if not isinstance(s, str): return s
            s = s.strip().upper().replace("-", "/")
            for k,v in meses.items():
                s = s.replace(f"/{k}/", f"/{v}/")
            return s

        fecha_cols = ["cedula_fecha_nacimiento", "desprendible_nomina_vigencia"]
        for col in fecha_cols:
            if col in df.columns:
                df[col] = df[col].apply(normalizar_fecha)

        # Mantener NN / Numero credito / Cedula como texto legible
        for col in ["NN", "Numero credito", "Cedula"]:
            if col in df.columns:
                df[col] = df[col].apply(convertir_a_entero_sin_notacion)

        # Convertir a numérico lo demás cuando aplique
        excluir = set(fecha_cols) | {"NN","Numero credito","Cedula"}
        for col in df.columns:
            if col not in excluir:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass

        # Reordenar
        columnas = list(df.columns)
        base = ['NN', 'Numero credito', 'Cedula']
        if 'id_cargue_origen' in columnas:
            base.append('id_cargue_origen')
        otras = [c for c in columnas if c not in base]
        df = df[base + otras]

        # Guardar
        self.carpeta_excel_destino.mkdir(parents=True, exist_ok=True)
        nuevo_nombre = archivo.name.replace(".xlsx", "_reestructurado.xlsx")
        ruta_nueva = self.carpeta_excel_destino / nuevo_nombre
        df.to_excel(ruta_nueva, index=False, engine='openpyxl')
        self.logger.info(f"Archivo reestructurado guardado en: {ruta_nueva}")
        return True
