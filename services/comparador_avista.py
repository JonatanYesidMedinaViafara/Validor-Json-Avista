import pandas as pd
from pathlib import Path
import logging
import re
from difflib import SequenceMatcher
from openpyxl import load_workbook
import config

# --------------------
# Normalizadores (solo para comparar)
# --------------------
def _norm_num_like(v):
    if pd.isna(v):
        return ""
    s = str(v).strip()
    try:
        if "e" in s.lower():
            return str(int(float(s)))
    except Exception:
        pass
    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return s.replace(".", "").replace(",", "").replace(" ", "")

def _norm_text(v):
    if pd.isna(v):
        return ""
    return str(v).strip().upper()

_MESES = {"ENE":"01","FEB":"02","MAR":"03","ABR":"04","MAY":"05","JUN":"06",
          "JUL":"07","AGO":"08","SEP":"09","OCT":"10","NOV":"11","DIC":"12"}

def _norm_fecha(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().upper().replace("-", "/")
    m = re.match(r"^(\d{1,2})/([A-Z]{3})/(\d{4})$", s)
    if m and m.group(2) in _MESES:
        return f"{m.group(1).zfill(2)}/{_MESES[m.group(2)]}/{m.group(3)}"
    m2 = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m2:
        return f"{m2.group(1).zfill(2)}/{m2.group(2).zfill(2)}/{m2.group(3)}"
    return s

# Fecha -> Timestamp (para reglas especiales)
def _parse_date(x):
    if pd.isna(x) or str(x).strip() == "":
        return None
    s = str(x).strip()
    up = s.upper().replace("-", "/")
    m = re.match(r"^(\d{1,2})/([A-Z]{3})/(\d{4})$", up)
    if m and m.group(2) in _MESES:
        up = f"{m.group(1).zfill(2)}/{_MESES[m.group(2)]}/{m.group(3)}"
    try:
        dt = pd.to_datetime(up, dayfirst=True, errors="coerce")
        return None if pd.isna(dt) else dt
    except:
        return None

def _cmp(avista_val, re_val, tipo):
    if tipo == "numero":
        return _norm_num_like(avista_val) == _norm_num_like(re_val)
    if tipo == "fecha":
        return _norm_fecha(avista_val) == _norm_fecha(re_val)
    # texto con tolerancia del 70%
    a = _norm_text(avista_val); b = _norm_text(re_val)
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= float(config.TOLERANCIA_TEXTO)

def _parse_percent_to_float(s):
    """'1,86%' -> 0.0186 ; '1.86 %' -> 0.0186 ; '1.86' -> 0.0186 si trae %; si no trae %, asume ya en fracción."""
    if s is None or str(s).strip() == "":
        return None
    t = str(s).strip().replace(" ", "")
    has_pct = "%" in t
    t = t.replace("%", "").replace(".", "").replace(",", ".")  # 1,86 -> 1.86 ; 1.234,56 -> 1234.56 (no debería aplicar)
    try:
        val = float(t)
        if has_pct:
            return val / 100.0
        return val  # ya en fracción
    except:
        return None

def _validacion_tasa_mensual_redondeada_4(avista_tasa_nominal, re_tasa_interes):
    """
    re_tasa_interes: anual en % (texto/numero). Se transforma a mensual: round((1 + J/100)**(1/12) - 1, 4)
    avista_tasa_nominal: porcentaje mensual (ej. '1,86%'). Se compara contra el valor mensual calculado (redondeado a 4).
    """
    # 1) mensual desde amortizacion_tasa_interes (anual en %)
    if re_tasa_interes is None or str(re_tasa_interes).strip() == "":
        return None
    try:
        anual_pct = float(str(re_tasa_interes).replace(",", "."))
    except:
        return None
    mensual = round((1 + (anual_pct / 100.0)) ** (1/12) - 1, 4)

    # 2) tasa nominal de Avista (en %). La convertimos a fracción mensual
    m_av = _parse_percent_to_float(avista_tasa_nominal)
    if m_av is None:
        return None
    m_av = round(m_av, 4)

    # 3) Comparamos con 4 decimales
    return abs(mensual - m_av) < 0.00005

# Evitar conflicto con columna original "CEDULA"
def _doc_out_col(doc: str) -> str:
    return "CEDULA COMPARADA" if doc.strip().upper() == "CEDULA" else doc

# --------------------
# Formateo al exportar (number_format en Excel)
# --------------------
FECHA_COLS      = ["FECHA VENCIMIENTO", "FECHA DESEMBOLSO", "FECHA NACIMIENTO"]
PERCENT_COLS    = ["TASA NOMINAL"]
NUM_DEC_COLS    = ["SALARIO", "VALOR CUOTA", "SALDO CAPITAL", "MONTO INCIAL", "CUOTA CORRIENTE"]
NUM_INT_COLS    = ["CUOTAS FALTANTES", "PLAZO INICIAL"]

def _tipar_y_formatear_excel(ruta_xlsx: Path, header_row: int = 1):
    wb = load_workbook(ruta_xlsx)
    ws = wb.active
    header = {cell.value: idx+1 for idx, cell in enumerate(ws[header_row])}
    fmt_date = "DD/MM/YYYY"; fmt_pct  = "0.00%"; fmt_int = "#,##0"; fmt_dec = "#,##0.00"
    for col_name in FECHA_COLS:
        idx = header.get(col_name)
        if idx:
            for row in ws.iter_rows(min_row=header_row+1, min_col=idx, max_col=idx):
                for cell in row: cell.number_format = fmt_date
    for col_name in PERCENT_COLS:
        idx = header.get(col_name)
        if idx:
            for row in ws.iter_rows(min_row=header_row+1, min_col=idx, max_col=idx):
                for cell in row: cell.number_format = fmt_pct
    for col_name in NUM_INT_COLS:
        idx = header.get(col_name)
        if idx:
            for row in ws.iter_rows(min_row=header_row+1, min_col=idx, max_col=idx):
                for cell in row: cell.number_format = fmt_int
    for col_name in NUM_DEC_COLS:
        idx = header.get(col_name)
        if idx:
            for row in ws.iter_rows(min_row=header_row+1, min_col=idx, max_col=idx):
                for cell in row: cell.number_format = fmt_dec
    wb.save(ruta_xlsx)

# --------------------
# Validaciones especiales
# --------------------
def _validacion_max_3_meses_antes(fecha_desembolso_avista, fecha_vigencia_re):
    """OK si vigencia está entre (desembolso - 3 meses) y desembolso (inclusive)."""
    dt_des = _parse_date(fecha_desembolso_avista)
    dt_vig = _parse_date(fecha_vigencia_re)
    if dt_des is None or dt_vig is None:
        return None  # no evaluable
    limite_inferior = dt_des - pd.DateOffset(months=3)
    return (dt_vig >= limite_inferior) and (dt_vig <= dt_des)

# --------------------
# Comparador
# --------------------
class ComparadorAvista:
    """
    Evidencia en UNA sola hoja:
    - Copia Avista y agrega 9 columnas (una por documento en config.DOCUMENTOS).
      Para 'CEDULA' se usa 'CEDULA COMPARADA'.
    - Cada celda: 'OK' / 'FALLO <Campo>' / 'SIN DATO <Campo>'.
    - Reglas especiales soportadas:
        * validacion_especial = 'max_3_meses_antes'
        * validacion_especial = 'tasa_mensual_redondeada_4'
        * comparar_recontra_re = True
    """
    def __init__(self, carpeta_excel_reestructurado: str, ruta_avista_excel: str, carpeta_salida: str):
        self.carpeta_excel_reestructurado = Path(carpeta_excel_reestructurado)
        self.ruta_avista_excel = Path(ruta_avista_excel)
        self.carpeta_salida = Path(carpeta_salida)
        self.logger = logging.getLogger("ComparadorAvista")

    def _obtener_ultimo_reestructurado(self) -> Path | None:
        archivos = list(self.carpeta_excel_reestructurado.glob("clon_json_*_reestructurado.xlsx"))
        if not archivos:
            self.logger.error("No se encontraron excels reestructurados.")
            return None
        return max(archivos, key=lambda f: f.stat().st_mtime)

    def _leer_avista(self, ruta: Path) -> pd.DataFrame | None:
        try:
            return pd.read_excel(ruta)  # preserva tipos
        except Exception as e:
            self.logger.exception(f"Error leyendo Avista {ruta}: {e}")
            return None

    def _leer_reestructurado(self, ruta: Path) -> pd.DataFrame | None:
        try:
            return pd.read_excel(ruta, dtype=str)  # comparamos como texto normalizado
        except Exception as e:
            self.logger.exception(f"Error leyendo reestructurado {ruta}: {e}")
            return None

    def comparar(self) -> bool:
        ruta_reestr = self._obtener_ultimo_reestructurado()
        if not ruta_reestr:
            return False

        df_avista = self._leer_avista(self.ruta_avista_excel)
        if df_avista is None:
            return False
        if "OPERACIÓN" not in df_avista.columns:
            self.logger.error("Avista no contiene la columna 'OPERACIÓN'.")
            return False

        df_res = self._leer_reestructurado(ruta_reestr)
        if df_res is None:
            return False
        if "Numero credito" not in df_res.columns:
            self.logger.error("Reestructurado no contiene 'Numero credito'.")
            return False

        df_res["_NUM_CRED_NORM_"] = df_res["Numero credito"].apply(_norm_num_like)

        # Hoja única: copia de Avista + columnas de evidencia
        hoja = df_avista.copy(deep=True)
        out_cols = {doc: _doc_out_col(doc) for doc in config.DOCUMENTOS}
        for _, out_name in out_cols.items():
            if out_name not in hoja.columns:
                hoja[out_name] = ""

        ok_global, fallos_global = [], []

        for idx, fav in df_avista.iterrows():
            op_raw = fav.get("OPERACIÓN", "")
            op_norm = _norm_num_like(op_raw)
            candidatos = df_res[df_res["_NUM_CRED_NORM_"] == op_norm]

            if candidatos.empty:
                for out_name in out_cols.values():
                    hoja.at[idx, out_name] = "NO ENCONTRADO EN REESTRUCTURADO"
                fallos_global.append({"OPERACIÓN": op_raw, "Motivo": "No match en reestructurado"})
                continue

            fila_res = candidatos.iloc[0]
            fila_tuvo_hallazgo = False

            for doc in config.DOCUMENTOS:
                out_name = out_cols[doc]
                campos = config.DOCUMENTOS_MAPEO.get(doc, {})
                if not campos:
                    hoja.at[idx, out_name] = ""
                    continue

                evidencias = []
                for campo_avista, spec in campos.items():

                    # --- RE vs RE (comparación entre dos columnas del reestructurado) ---
                    if spec.get("comparar_recontra_re"):
                        re1 = spec.get("re")
                        re2 = spec.get("re2")
                        tipo = spec.get("tipo", "texto")

                        if re1 not in fila_res.index:
                            evidencias.append(f"SIN DATO {re1}")
                            fila_tuvo_hallazgo = True
                            continue
                        if re2 not in fila_res.index:
                            evidencias.append(f"SIN DATO {re2}")
                            fila_tuvo_hallazgo = True
                            continue

                        v1 = fila_res.get(re1, "")
                        v2 = fila_res.get(re2, "")
                        if (v1 is None or str(v1).strip() == ""):
                            evidencias.append(f"SIN DATO {re1}")
                            fila_tuvo_hallazgo = True
                            continue
                        if (v2 is None or str(v2).strip() == ""):
                            evidencias.append(f"SIN DATO {re2}")
                            fila_tuvo_hallazgo = True
                            continue

                        if _cmp(v1, v2, tipo):
                            evidencias.append("OK")
                        else:
                            evidencias.append("Son Diferentes entre Solicitud Credito Solicitud y Amortizacion Numero Solicitud")
                            fila_tuvo_hallazgo = True
                        continue  # siguiente campo

                    # --- Avista vs Reestructurado ---
                    re_col = spec.get("re")
                    tipo = spec.get("tipo", "texto")
                    special = spec.get("validacion_especial")
                    av_val = fav.get(campo_avista, "")

                    if not re_col:
                        continue

                    if re_col not in fila_res.index:
                        evidencias.append(f"SIN DATO {campo_avista}")
                        fila_tuvo_hallazgo = True
                        continue

                    re_val = fila_res.get(re_col, "")
                    if re_val is None or str(re_val).strip() == "":
                        evidencias.append(f"SIN DATO {campo_avista}")
                        fila_tuvo_hallazgo = True
                        continue

                    # --- Validaciones especiales ---
                    if special == "max_3_meses_antes":
                        ok = _validacion_max_3_meses_antes(av_val, re_val)
                        if ok is None:
                            evidencias.append(f"SIN DATO {campo_avista}")
                            fila_tuvo_hallazgo = True
                        elif ok:
                            evidencias.append("OK")
                        else:
                            evidencias.append("FECHA EXCEDE EL TIEMPO")
                            fila_tuvo_hallazgo = True
                        continue

                    if special == "tasa_mensual_redondeada_4":
                        ok = _validacion_tasa_mensual_redondeada_4(av_val, re_val)
                        if ok is None:
                            evidencias.append(f"SIN DATO {campo_avista}")
                            fila_tuvo_hallazgo = True
                        elif ok:
                            evidencias.append("OK")
                        else:
                            evidencias.append("FALLO TASA NOMINAL")
                            fila_tuvo_hallazgo = True
                        continue

                    # --- Validación estándar ---
                    if _cmp(av_val, re_val, tipo):
                        evidencias.append("OK")
                    else:
                        evidencias.append(f"FALLO {campo_avista}")
                        fila_tuvo_hallazgo = True

                hoja.at[idx, out_name] = ", ".join(evidencias) if evidencias else ""

            if fila_tuvo_hallazgo:
                fallos_global.append({"OPERACIÓN": op_raw})
            else:
                ok_global.append({"OPERACIÓN": op_raw})

        # Guardar
        self.carpeta_salida.mkdir(parents=True, exist_ok=True)
        base = Path(ruta_reestr).stem.replace("_reestructurado", "")

        ruta_evid = self.carpeta_salida / f"{base}_evidencia_avista_unica.xlsx"
        ruta_ok   = self.carpeta_salida / f"{base}_ok.xlsx"
        ruta_fail = self.carpeta_salida / f"{base}_fallos.xlsx"

        hoja.to_excel(ruta_evid, index=False, engine="openpyxl")
        _tipar_y_formatear_excel(ruta_evid)

        pd.DataFrame(ok_global).to_excel(ruta_ok, index=False, engine="openpyxl")
        pd.DataFrame(fallos_global).to_excel(ruta_fail, index=False, engine="openpyxl")

        self.logger.info(f"Evidencia (única hoja) -> {ruta_evid}")
        self.logger.info(f"OK global              -> {ruta_ok}")
        self.logger.info(f"Fallos global          -> {ruta_fail}")
        return True
