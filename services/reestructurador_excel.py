import pandas as pd
from pathlib import Path
import logging

def separar_nombre_completo(nombre_completo: str):
    """Separa nombres normales: Nombres primero, Apellidos al final."""
    if not isinstance(nombre_completo, str) or not nombre_completo.strip():
        return "", "", "", ""
    partes = nombre_completo.strip().split()
    cantidad = len(partes)

    if cantidad == 1:
        return partes[0].upper(), "", "", ""
    elif cantidad == 2:
        return partes[0].upper(), "", partes[1].upper(), ""
    elif cantidad == 3:
        return partes[0].upper(), partes[1].upper(), partes[2].upper(), ""
    elif cantidad >= 4:
        primer_nombre = partes[0].upper()
        segundo_nombre = " ".join(partes[1:-2]).upper() if cantidad > 4 else partes[1].upper()
        primer_apellido = partes[-2].upper()
        segundo_apellido = partes[-1].upper()
        return primer_nombre, segundo_nombre, primer_apellido, segundo_apellido

def separar_nombre_datacredito(nombre_completo: str):
    """Separa nombres invertidos: Apellidos primero, Nombres al final."""
    if not isinstance(nombre_completo, str) or not nombre_completo.strip():
        return "", "", "", ""
    partes = nombre_completo.strip().split()
    cantidad = len(partes)

    if cantidad == 1:
        return partes[0].upper(), "", "", ""
    elif cantidad == 2:
        return partes[1].upper(), "", partes[0].upper(), ""
    elif cantidad == 3:
        return partes[1].upper(), partes[2].upper(), partes[0].upper(), ""
    elif cantidad >= 4:
        primer_nombre = partes[-2].upper()
        segundo_nombre = partes[-1].upper()
        primer_apellido = partes[0].upper()
        segundo_apellido = " ".join(partes[1:-2]).upper() if cantidad > 4 else partes[1].upper()
        return primer_nombre, segundo_nombre, primer_apellido, segundo_apellido

def convertir_a_entero_sin_notacion(valor):
    """Evita la notación científica en campos numéricos grandes, retornando texto legible."""
    try:
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        elif isinstance(valor, (int, str)) and str(valor).isdigit():
            return str(valor)
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
        ultimo = max(archivos, key=lambda f: f.stat().st_mtime)
        return ultimo

    def reestructurar(self):
        archivo = self._obtener_ultimo_excel()
        if not archivo:
            return False
        self.logger.info(f"Reestructurando archivo: {archivo.name}")

        df = pd.read_excel(archivo, dtype=str)
        if 'nombre_archivo_origen' not in df.columns:
            self.logger.error("La columna 'nombre_archivo_origen' no existe en el Excel.")
            return False

        # 1) Generar NN, Numero credito, Cedula
        nuevo_df = df['nombre_archivo_origen'].str.replace('.json', '', regex=False).str.split('_', expand=True)
        nuevo_df.columns = ['NN', 'Numero credito', 'Cedula']
        for i, col in enumerate(['NN', 'Numero credito', 'Cedula']):
            df.insert(i, col, nuevo_df[col])
        df = df.drop(columns=['nombre_archivo_origen'])

        # 2) Procesar columnas que terminen en "_nombre_completo" o especiales
        cols_split = [col for col in df.columns if col.endswith("_nombre_completo")]
        especiales = ["datacredito_nombre_deudor"]
        cols_split.extend([c for c in especiales if c in df.columns])

        eliminadas = []

        for col in cols_split:
            prefijo = col.replace("_nombre_completo", "").replace("_nombre_deudor", "").replace("_", " ").title()
            # elegir separador correcto
            if "datacredito" in col:
                nombres = df[col].apply(separar_nombre_datacredito)
            else:
                nombres = df[col].apply(separar_nombre_completo)

            df[f'{prefijo} Primer Nombre'] = nombres.apply(lambda x: x[0])
            df[f'{prefijo} Segundo Nombre'] = nombres.apply(lambda x: x[1])
            df[f'{prefijo} Primer Apellido'] = nombres.apply(lambda x: x[2])
            df[f'{prefijo} Segundo Apellido'] = nombres.apply(lambda x: x[3])

            # eliminar la columna fuente
            if col in df.columns:
                df.drop(columns=[col], inplace=True)
                eliminadas.append(col)

        # 3) Procesar columnas que terminen en "_nombre_firma_electronica"
        cols_firma = [col for col in df.columns if col.endswith("_nombre_firma_electronica")]
        for col in cols_firma:
            base = col.replace("_nombre_firma_electronica", "").replace("_", " ").title()
            prefijo = f"{base} Firma Electrónica"
            nombres = df[col].apply(separar_nombre_completo)

            df[f'{prefijo} Primer Nombre'] = nombres.apply(lambda x: x[0])
            df[f'{prefijo} Segundo Nombre'] = nombres.apply(lambda x: x[1])
            df[f'{prefijo} Primer Apellido'] = nombres.apply(lambda x: x[2])
            df[f'{prefijo} Segundo Apellido'] = nombres.apply(lambda x: x[3])

            if col in df.columns:
                df.drop(columns=[col], inplace=True)
                eliminadas.append(col)

        if eliminadas:
            self.logger.info(f"Columnas de nombres divididas y eliminadas: {eliminadas}")

        # 4) Procesar columnas que terminen en "_numero_documento"
        columnas_doc = [col for col in df.columns if col.endswith("_numero_documento")]
        for col in columnas_doc:
            prefijo = col.replace("_numero_documento", "").replace("_", " ").title()
            nuevo_nombre = f"{prefijo} Cedula"
            df = df.rename(columns={col: nuevo_nombre})

        # 5) Arreglar fechas con texto tipo "18/ENE/1941" -> "18/01/1941"
        meses = {
            'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
        }
        def normalizar_fecha(fecha: str):
            if isinstance(fecha, str):
                up = fecha.upper().replace("-", "/")
                for mes_texto, mes_num in meses.items():
                    if f'/{mes_texto}/' in up:
                        return up.replace(f'/{mes_texto}/', f'/{mes_num}/')
                return up
            return fecha

        columnas_fecha = ["cedula_fecha_nacimiento", "desprendible_nomina_vigencia"]
        for col in columnas_fecha:
            if col in df.columns:
                df[col] = df[col].apply(normalizar_fecha)

        # 6) Evitar notación científica en NN / Numero credito / Cedula (mantenerlos como texto legible)
        columnas_preservar_texto = ["NN", "Numero credito", "Cedula"]
        for col in columnas_preservar_texto:
            if col in df.columns:
                df[col] = df[col].apply(convertir_a_entero_sin_notacion)

        # 7) Convertir otras columnas numéricas cuando aplique (excepto fechas y preservadas)
        columnas_excluir = columnas_fecha + columnas_preservar_texto
        for col in df.columns:
            if col not in columnas_excluir:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass

        # 8) Reordenar columnas
        columnas = list(df.columns)
        nuevas_columnas = ['NN', 'Numero credito', 'Cedula']
        if 'id_cargue_origen' in columnas:
            nuevas_columnas.append('id_cargue_origen')
        generadas = [c for c in df.columns if any(suf in c for suf in ['Primer Nombre', 'Segundo Nombre', 'Primer Apellido', 'Segundo Apellido', 'Cedula'])]
        for c in generadas:
            if c not in nuevas_columnas:
                nuevas_columnas.append(c)
        for col in columnas:
            if col not in nuevas_columnas:
                nuevas_columnas.append(col)
        df = df[nuevas_columnas]

        # 9) Guardar Excel
        self.carpeta_excel_destino.mkdir(parents=True, exist_ok=True)
        nuevo_nombre = archivo.name.replace(".xlsx", "_reestructurado.xlsx")
        ruta_nueva = self.carpeta_excel_destino / nuevo_nombre
        df.to_excel(ruta_nueva, index=False, engine='openpyxl')
        self.logger.info(f"Archivo reestructurado guardado en: {ruta_nueva}")
        return True
