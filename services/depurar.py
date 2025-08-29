# services/depurar.py
from pathlib import Path
import shutil
import logging

class Depurador:
    """
    Mueve todo lo que NO sea .json desde 'carpeta_origen' a 'carpeta_destino'.
    Uso:
        dep = Depurador(ruta_origen, ruta_destino)
        movidos = dep.ejecutar()
    """
    def __init__(self, carpeta_origen: str, carpeta_destino: str):
        self.carpeta_origen = Path(carpeta_origen)
        self.carpeta_destino = Path(carpeta_destino)
        self.logger = logging.getLogger("Depurador")

    def _es_json(self, p: Path) -> bool:
        return p.is_file() and p.suffix.lower() == ".json"

    def ejecutar(self) -> list[str]:
        """Realiza la depuración y devuelve la lista de nombres movidos."""
        if not self.carpeta_origen.exists():
            self.logger.warning(f"La carpeta de origen no existe: {self.carpeta_origen}")
            return []

        self.carpeta_destino.mkdir(parents=True, exist_ok=True)

        movidos: list[str] = []
        for p in self.carpeta_origen.iterdir():
            if not p.is_file():
                continue
            if self._es_json(p):
                continue
            try:
                destino = self.carpeta_destino / p.name
                # si ya existe, agrega sufijo para no chocar
                if destino.exists():
                    destino = self.carpeta_destino / f"{p.stem}_dup{destino.suffix or p.suffix}"
                shutil.move(str(p), str(destino))
                movidos.append(p.name)
            except Exception as e:
                self.logger.error(f"No se pudo mover '{p.name}': {e}")

        if movidos:
            self.logger.info(f"Archivos no JSON movidos: {movidos}")
        else:
            self.logger.info("No se encontraron archivos no JSON.")

        return movidos
