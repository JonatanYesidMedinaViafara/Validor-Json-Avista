# services/consolidador_final.py
from pathlib import Path
import logging
from datetime import datetime
import pandas as pd

class ConsolidadorFinal:
    def __init__(
        self,
        carpeta_clon: str,
        carpeta_reestructurado: str,
        carpeta_normalizado: str,
        carpeta_comparacion: str,
        carpeta_salida_unificado: str,
    ):
        self.carpeta_clon = Path(carpeta_clon)
        self.carpeta_reestructurado = Path(carpeta_reestructurado)
        self.carpeta_normalizado = Path(carpeta_normalizado)
        self.carpeta_comparacion = Path(carpeta_comparacion)
        self.carpeta_salida_unificado = Path(carpeta_salida_unificado)
        self.logger = logging.getLogger("ConsolidadorFinal")

    def _ultimo(self, folder: Path, pattern: str) -> Path | None:
        files = list(folder.glob(pattern))
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_mtime)

    def _leer(self, p: Path | None) -> pd.DataFrame:
        if not p or not p.exists():
            return pd.DataFrame()
        try:
            return pd.read_excel(p)
        except Exception as e:
            self.logger.error(f"No pude leer {p}: {e}")
            return pd.DataFrame()

    def consolidar(self) -> Path | None:
        # Busca SIEMPRE el último de cada tipo, en la misma carpeta de resultados
        clon = self._leer(self._ultimo(self.carpeta_clon, "clon_json_*.xlsx"))
        rees = self._leer(self._ultimo(self.carpeta_reestructurado, "clon_json_*_reestructurado.xlsx"))
        norm = self._leer(self._ultimo(self.carpeta_normalizado, "clon_json_*_resultado_normalizado.xlsx"))
        evid = self._leer(self._ultimo(self.carpeta_comparacion, "clon_json_*_evidencia_avista_unica.xlsx"))

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = self.carpeta_salida_unificado / f"Davinci_Resultado_{ts}.xlsx"
        self.carpeta_salida_unificado.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            if not clon.empty:
                clon.to_excel(writer, sheet_name="Clonacion Json", index=False)
            if not rees.empty:
                rees.to_excel(writer, sheet_name="Reestructurado", index=False)
            if not norm.empty:
                norm.to_excel(writer, sheet_name="Resultado Normalizado", index=False)
            if not evid.empty:
                evid.to_excel(writer, sheet_name="Avista Evidencia", index=False)

        self.logger.info(f"Excel unificado creado: {out}")
        return out
