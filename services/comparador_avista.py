import pandas as pd
from pathlib import Path
import logging
import re
from difflib import SequenceMatcher
import unicodedata
import config

# -------------------- Normalizadores --------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def _norm_header(h):
    return _strip_accents(str(h)).strip().upper()

def _is_blank(v) -> bool:
    try:
        if v is None: return True
        if isinstance(v, float) and pd.isna(v): return True
        s = str(v).strip()
        return s == "" or s.upper() in {"NAN", "NAT", "NONE", "NULL"}
    except Exception:
        return False

def _norm_text(v):
    if pd.isna(v): return ""
    return " ".join(_strip_accents(str(v)).strip().upper().split())

def _norm_num_like(v):
    if pd.isna(v): return ""
    s = str(v).strip()
    try:
        if "e" in s.lower():
            return str(int(float(s)))
    except Exception:
        pass
    s2 = s.replace(".", "").replace(",", "").replace(" ", "")
    try:
        f = float(s2)
        return str(int(f)) if f.is_integer() else str(int(round(f)))
    except Exception:
        return s2

_MESES = {"ENE":"01","FEB":"02","MAR":"03","ABR":"04","MAY":"05","JUN":"06",
          "JUL":"07","AGO":"08","SEP":"09","OCT":"10","NOV":"11","DIC":"12"}

def _norm_fecha(v):
    """Devuelve fecha como DD/MM/YYYY cuando es reconocible."""
    if pd.isna(v): return ""
    s = str(v).strip()
    if not s: return ""
    up = _strip_accents(s).upper().replace("-", "/")
    m = re.match(r"^(\d{1,2})/([A-Z]{3})/(\d{2,4})(?:\s+.*)?$", up)
    if m and m.group(2) in _MESES:
        up = f"{m.group(1).zfill(2)}/{_MESES[m.group(2)]}/{m.group(3)}"
    dt = pd.to_datetime(up, dayfirst=True, errors="coerce")
    if pd.isna(dt):
        m2 = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})(?:\s+.*)?$", up)
        if m2:
            dt = pd.to_datetime(f"{m2.group(3).zfill(2)}/{m2.group(2).zfill(2)}/{m2.group(1)}",
                                dayfirst=True, errors="coerce")
    if pd.isna(dt): return up
    return dt.strftime("%d/%m/%Y")

def _parse_date(x):
    s = _norm_fecha(x)
    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return None if pd.isna(dt) else dt

def _dates_equal(a, b) -> bool | None:
    da = pd.to_datetime(str(a), dayfirst=True, errors="coerce")
    db = pd.to_datetime(str(b), dayfirst=True, errors="coerce")
    if pd.isna(da):
        da = pd.to_datetime(str(a), yearfirst=True, errors="coerce")
    if pd.isna(db):
        db = pd.to_datetime(str(b), yearfirst=True, errors="coerce")
    if pd.isna(da) or pd.isna(db): return None
    try:
        return da.date() == db.date()
    except Exception:
        return None

def _cmp(avista_val, re_val, tipo):
    if tipo == "numero":
        return _norm_num_like(avista_val) == _norm_num_like(re_val)
    if tipo == "fecha":
        eq = _dates_equal(avista_val, re_val)
        if eq is not None:
            return eq
        return _norm_fecha(avista_val) == _norm_fecha(re_val)
    a = _norm_text(avista_val); b = _norm_text(re_val)
    return SequenceMatcher(None, a, b).ratio() >= float(config.TOLERANCIA_TEXTO)

# -------------------- Reglas especiales --------------------
def _max_3_meses_antes_mes_anio(fecha_desembolso_avista, fecha_vigencia_re):
    dt_des = _parse_date(fecha_desembolso_avista)
    dt_vig = _parse_date(fecha_vigencia_re)
    if dt_des is None or dt_vig is None: return None
    des_m = pd.Timestamp(year=dt_des.year, month=dt_des.month, day=1)
    vig_m = pd.Timestamp(year=dt_vig.year, month=dt_vig.month, day=1)
    limite_inf = des_m - pd.DateOffset(months=3)
    return (vig_m >= limite_inf) and (vig_m <= des_m)

# -------------------- Helpers AVISTA --------------------
def _avista_nombre_completo(row: pd.Series) -> str:
    p1 = str(row.get("PRIMER NOMBRE", "") or "").strip()
    p2 = str(row.get("SEGUNDO NOMBRE", "") or "").strip()
    a1 = str(row.get("PRIMER APELLIDO", "") or "").strip()
    a2 = str(row.get("SEGUNDO APELLIDO", "") or "").strip()
    partes = [p for p in [p1, p2, a1, a2] if p]
    return " ".join(partes)

# Alias de columnas AVISTA para tolerar typos/variantes
_AVISTA_ALIASES = {
    "MONTO INICIAL": "MONTO INCIAL",  # si la base trae el typo 'INCIAL'
}

def _avista_val(row: pd.Series, campo_avista: str) -> str:
    ca = _norm_header(campo_avista)
    if ca == "NOMBRE COMPLETO":
        return _avista_nombre_completo(row)
    if ca.startswith("CEDULA"):
        return str(row.get("CEDULA", "") or "")
    if ca == "FECHA NACIMIENTO":
        return str(row.get("FECHA NACIMIENTO", "") or "")
    # Lookup directo y con alias (por si viene con typo en AVISTA)
    val = row.get(ca, "")
    if (val is None or str(val).strip() == "") and ca in _AVISTA_ALIASES:
        val = row.get(_AVISTA_ALIASES[ca], "")
    return str(val or "")

# --- Nombre por componentes → un solo OK (Datacrédito / Fianza / Formato Conocimiento) ---
def _ok_fullname_components(fav_row: pd.Series, re_fullname: str) -> list[str]:
    re_full = _norm_text(re_fullname)
    av_p1 = _norm_text(fav_row.get("PRIMER NOMBRE", ""))
    av_p2 = _norm_text(fav_row.get("SEGUNDO NOMBRE", ""))
    av_a1 = _norm_text(fav_row.get("PRIMER APELLIDO", ""))
    av_a2 = _norm_text(fav_row.get("SEGUNDO APELLIDO", ""))

    comps = [("PRIMER NOMBRE", av_p1), ("SEGUNDO NOMBRE", av_p2),
             ("PRIMER APELLIDO", av_a1), ("SEGUNDO APELLIDO", av_a2)]
    evaluados = [(lbl, piece) for (lbl, piece) in comps if piece]
    if not evaluados:
        return ["ND-AV NOMBRE COMPLETO"]

    fallos = [lbl for (lbl, piece) in evaluados if piece not in re_full]
    return ["OK"] if not fallos else [f"FALLO {lbl}" for lbl in fallos]

# -------------------- Comparador --------------------
class ComparadorAvista:
    def __init__(self, carpeta_excel_reestructurado: str, carpeta_bases_avista: str | Path, carpeta_salida: str | Path):
        self.carpeta_excel_reestructurado = Path(carpeta_excel_reestructurado)
        self.carpeta_bases_avista = Path(carpeta_bases_avista)
        self.carpeta_salida = Path(carpeta_salida)
        self.logger = logging.getLogger("ComparadorAvista")

    def _listar_avista_validos(self):
        if not self.carpeta_bases_avista.exists(): return []
        archivos = [p for p in self.carpeta_bases_avista.glob("*.xlsx") if p.is_file() and not p.name.startswith("~$")]
        archivos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return archivos

    def _leer_avista(self) -> tuple[pd.DataFrame | None, Path | None]:
        candidatos = self._listar_avista_validos()
        if not candidatos:
            self.logger.error(f"No hay .xlsx válidos en {self.carpeta_bases_avista}")
            return None, None
        ultimo_error = None
        for p in candidatos:
            try:
                df = pd.read_excel(p)
                df.columns = [_norm_header(c) for c in df.columns]
                self.logger.info(f"Usando Base Avista: {p.name}")
                return df, p
            except Exception as e:
                self.logger.warning(f"No se pudo abrir {p.name}: {e}")
                ultimo_error = e
        self.logger.error(f"No fue posible abrir ninguna base Avista. Último error: {ultimo_error}")
        return None, None

    def _ultimo_reestructurado(self) -> Path | None:
        archivos = list(self.carpeta_excel_reestructurado.glob("clon_json_*_reestructurado.xlsx"))
        if not archivos:
            self.logger.error("No se encontraron excels reestructurados.")
            return None
        archivos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        ruta = archivos[0]
        self.logger.info(f"Usando Reestructurado: {ruta.name}")
        return ruta

    def _col_operacion(self, df_avista: pd.DataFrame) -> str | None:
        for original in df_avista.columns:
            if _norm_header(original) == "OPERACION":
                return original
        for original in df_avista.columns:
            if "OPER" in _norm_header(original):
                return original
        self.logger.error("No se detectó columna OPERACIÓN.")
        return None

    def _leer_reestructurado(self, ruta: Path) -> pd.DataFrame | None:
        try:
            return pd.read_excel(ruta, dtype=str)
        except Exception as e:
            self.logger.exception(f"Error leyendo reestructurado {ruta}: {e}")
            return None

    def comparar(self) -> bool:
        ruta_reestr = self._ultimo_reestructurado()
        if not ruta_reestr:
            return False

        df_avista, ruta_base = self._leer_avista()
        if df_avista is None or df_avista.empty:
            self.logger.error("No se pudo cargar la base Avista.")
            return False

        col_oper = self._col_operacion(df_avista)
        if not col_oper:
            return False

        df_res = self._leer_reestructurado(ruta_reestr)
        if df_res is None or df_res.empty:
            self.logger.error("No se pudo cargar el reestructurado.")
            return False

        if "Numero credito" not in df_res.columns:
            self.logger.error("Reestructurado no contiene 'Numero credito'.")
            return False

        df_res["_NUM_CRED_NORM_"] = df_res["Numero credito"].apply(_norm_num_like)

        hoja = df_avista.copy(deep=True)
        for doc in config.DOCUMENTOS:
            if doc not in hoja.columns:
                hoja[doc] = ""

        for idx, fav in hoja.iterrows():
            op_raw = fav.get(col_oper, "")
            op_norm = _norm_num_like(op_raw)
            candidatos = df_res[df_res["_NUM_CRED_NORM_"] == op_norm]

            if candidatos.empty:
                for doc in config.DOCUMENTOS:
                    hoja.at[idx, doc] = "NO ENCONTRADO EN REESTRUCTURADO"
                continue

            fila_res = candidatos.iloc[0]

            for doc in config.DOCUMENTOS:
                campos = config.DOCUMENTOS_MAPEO.get(doc, {})
                evidencias = []

                for campo_avista, spec in campos.items():
                    # ---- Soportar lista de specs o un dict ----
                    specs = spec if isinstance(spec, list) else [spec]

                    # Valor Avista (una sola vez)
                    av_val = _avista_val(fav, campo_avista)

                    # Si AVISTA no trae valor, marca ND-AV para cada spec
                    if _is_blank(av_val):
                        for _ in specs:
                            evidencias.append(f"ND-AV {campo_avista}")
                        continue

                    for sp in specs:
                        # RE vs RE
                        if sp.get("comparar_recontra_re"):
                            re1 = sp.get("re"); re2 = sp.get("re2")
                            tipo = sp.get("tipo", "texto")
                            a = fila_res.get(re1, "")
                            b = fila_res.get(re2, "")
                            if _is_blank(a) and _is_blank(b):
                                evidencias.append(f"ND-RE {re1},{re2}")
                            elif _is_blank(a):
                                evidencias.append(f"ND-RE {re1}")
                            elif _is_blank(b):
                                evidencias.append(f"ND-RE {re2}")
                            else:
                                evidencias.append("OK" if _cmp(a, b, tipo) else f"FALLO {re1} vs {re2}")
                            continue

                        # Avista vs RE
                        re_col = sp.get("re")
                        tipo = sp.get("tipo", "texto")
                        special = sp.get("validacion_especial")

                        if not re_col or re_col not in fila_res.index:
                            evidencias.append(f"ND-RE {campo_avista}")
                            continue

                        re_val = fila_res.get(re_col, "")
                        if _is_blank(re_val):
                            evidencias.append(f"ND-RE {campo_avista}")
                            continue

                        # Un solo OK para nombres (DATACREDITO / FIANZA / FORMATO CONOCIMIENTO)
                        if _norm_header(doc) in {"DATACREDITO", "FIANZA", "FORMATO CONOCIMIENTO"} and _norm_header(campo_avista) in {
                            "NOMBRE COMPLETO", "NOMBRE COMPLETO 2"
                        }:
                            evidencias.extend(_ok_fullname_components(fav, re_val))
                            continue

                        if special == "max_3_meses_antes_mes_anio":
                            ok = _max_3_meses_antes_mes_anio(av_val, re_val)
                            evidencias.append("OK" if ok else ("ND-RE "+campo_avista if ok is None else "FALLO FECHA (3M)"))
                            continue

                        ok = _cmp(av_val, re_val, tipo)
                        evidencias.append("OK" if ok else f"FALLO {campo_avista}")

                hoja.at[idx, doc] = ", ".join(evidencias) if evidencias else ""

        self.carpeta_salida.mkdir(parents=True, exist_ok=True)
        base = Path(ruta_reestr).stem.replace("_reestructurado", "")
        ruta_evid = self.carpeta_salida / f"{base}_evidencia_avista_unica.xlsx"
        hoja.to_excel(ruta_evid, index=False, engine="openpyxl")

        if ruta_base:
            self.logger.info(f"Base Avista usada: {ruta_base}")
        self.logger.info(f"Evidencia Avista -> {ruta_evid}")
        return True
