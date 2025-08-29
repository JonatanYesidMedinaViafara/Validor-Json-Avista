# services/normalizador_excel.py
import pandas as pd
from pathlib import Path
import logging
from difflib import SequenceMatcher

class NormalizadorExcel:
    """
    Produce un único archivo *_resultado_normalizado.xlsx con columna 'Estado Normalizado'.
    Reglas básicas (puedes ajustarlas según avances).
    """
    def __init__(self, carpeta_excel_reestructurado: str, carpeta_salida: str, umbral_similitud: float = 0.70):
        self.carpeta_excel_reestructurado = Path(carpeta_excel_reestructurado)
        self.carpeta_salida = Path(carpeta_salida)
        self.umbral = umbral_similitud
        self.logger = logging.getLogger("NormalizadorExcel")

    def _ultimo_reestructurado(self) -> Path | None:
        files = list(self.carpeta_excel_reestructurado.glob("clon_json_*_reestructurado.xlsx"))
        if not files:
            self.logger.error("No se encontraron archivos reestructurados.")
            return None
        return max(files, key=lambda f: f.stat().st_mtime)

    def _sim(self, a: str, b: str) -> float:
        return SequenceMatcher(None, str(a).strip().upper(), str(b).strip().upper()).ratio()

    def _bloque_ok(self, row, cols) -> bool:
        vals = [row.get(c, "") for c in cols if c in row.index and pd.notna(row.get(c, ""))]
        vals = [str(v) for v in vals if str(v).strip() != ""]
        if not vals:  # sin datos -> lo marcamos como error de bloque
            return False
        if len(vals) == 1:
            return True
        # similitud promedio
        pares = []
        for i in range(len(vals)):
            for j in range(i+1, len(vals)):
                pares.append(self._sim(vals[i], vals[j]))
        return (sum(pares)/len(pares)) >= self.umbral if pares else True

    def normalizar(self) -> bool:
        archivo = self._ultimo_reestructurado()
        if not archivo: return False
        self.logger.info(f"Normalizando: {archivo.name}")

        df = pd.read_excel(archivo, dtype=str)

        # Bloques de ejemplo (ajústalos si cambiaste nombres de columnas)
        bloques = [
            ["desprendible_nomina_pagaduria", "amortizacion_pagaduria", "libranza_pagaduria"],
            ["formato_conocimiento_plazo_meses", "amortizacion_plazo_meses", "libranza_plazo"],
            ["libranza_valor_cuota", "amortizacion_valor_cuota"],
            ["libranza_valor_prestamo", "amortizacion_valor_credito", "formato_conocimiento_valor_total_credito"],
            ["solicitud_credito_solicitud", "amortizacion_numero_solicitud"],
        ]

        estados = []
        for _, row in df.iterrows():
            ok_all = True
            for cols in bloques:
                present = [c for c in cols if c in df.columns]
                if present and (not self._bloque_ok(row, present)):
                    ok_all = False
                    break
            estados.append("OK" if ok_all else "CON ERRORES")

        df_out = df.copy()
        df_out["Estado Normalizado"] = estados

        self.carpeta_salida.mkdir(parents=True, exist_ok=True)
        out = self.carpeta_salida / archivo.name.replace("_reestructurado.xlsx", "_resultado_normalizado.xlsx")
        df_out.to_excel(out, index=False, engine="openpyxl")
        self.logger.info(f"Resultado Normalizado -> {out}")
        return True
