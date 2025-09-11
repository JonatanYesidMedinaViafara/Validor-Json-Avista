# services/depurar.py
from __future__ import annotations
import shutil
from pathlib import Path
import logging
import datetime as dt

class Depurador:
    """
    Mueve cualquier archivo que NO sea .json desde `carpeta_fuente`
    hacia una carpeta de 'archivos conflicto', distinta por modo:
      - modo 1 (Local):   <Escritorio>/archivos conflicto
      - modo 2 (SFTP):    <CARPETA_RESULTADOS_DAVINCI>/archivos conflicto

    Si no hay archivos por mover, NO es error: devuelve True igualmente.
    """
    def __init__(
        self,
        carpeta_fuente: str | Path,
        carpeta_conflicto_destino: str | Path | None,
        modo_ingesta: int = 1,
        logger: logging.Logger | None = None,
    ):
        self.carpeta_fuente = Path(carpeta_fuente)
        self.carpeta_conflicto_destino = Path(carpeta_conflicto_destino) if carpeta_conflicto_destino else None
        self.modo_ingesta = int(modo_ingesta)
        self.logger = logger or logging.getLogger("Depurador")

    def _default_conflict_dir(self) -> Path:
        if self.modo_ingesta == 2:
            # “Davinci/archivos conflicto” (se pasa desde main)
            return self.carpeta_conflicto_destino
        # Modo 1: Escritorio/archivos conflicto
        escritorio = Path.home() / "Desktop"
        return escritorio / "archivos conflicto"

    def _ensure_unique(self, dst: Path) -> Path:
        """Evita colisiones: agrega sufijo (1), (2), ... si el archivo existe."""
        if not dst.exists():
            return dst
        stem, suf = dst.stem, dst.suffix
        i = 1
        while True:
            nuevo = dst.with_name(f"{stem} ({i}){suf}")
            if not nuevo.exists():
                return nuevo
            i += 1

    def ejecutar(self) -> bool:
        try:
            if not self.carpeta_fuente.exists():
                self.logger.warning(f"La carpeta de origen no existe: {self.carpeta_fuente}")
                return True  # No es fatal: continuamos

            archivos = [p for p in self.carpeta_fuente.iterdir() if p.is_file()]
            no_json = [p for p in archivos if p.suffix.lower() != ".json"]

            if not no_json:
                self.logger.info("Depuración: no se encontraron archivos distintos a .json. Continuando…")
                return True  # ¡Nada que mover y seguimos!

            conflict_dir = self._default_conflict_dir()
            conflict_dir.mkdir(parents=True, exist_ok=True)

            movidos = 0
            for src in no_json:
                dst = self._ensure_unique(conflict_dir / src.name)
                try:
                    shutil.move(str(src), str(dst))
                    movidos += 1
                except Exception as e:
                    self.logger.warning(f"No se pudo mover {src.name} -> {dst}: {e}")

            self.logger.info(f"Depuración: {movidos} archivo(s) movidos a '{conflict_dir}'.")
            return True
        except Exception as e:
            self.logger.exception(f"Error en Depurador: {e}")
            # Aún así, para no detener el pipeline, devolvemos True
            return True
