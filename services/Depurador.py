import shutil
from pathlib import Path
import logging

class Depurador:
    def __init__(self, carpeta_origen: str, carpeta_destino: str):
        self.carpeta_origen = Path(carpeta_origen)
        self.carpeta_destino = Path(carpeta_destino)
        self.logger = logging.getLogger("Depurador")

    def depurar(self):
        if not self.carpeta_origen.exists():
            raise FileNotFoundError(f"La carpeta origen '{self.carpeta_origen}' no existe.")
        if not self.carpeta_destino.exists():
            self.carpeta_destino.mkdir(parents=True, exist_ok=True)

        archivos_movidos = []
        for archivo in self.carpeta_origen.iterdir():
            if archivo.is_file() and archivo.suffix.lower() != '.json':
                destino_archivo = self.carpeta_destino / archivo.name
                shutil.move(str(archivo), destino_archivo)
                archivos_movidos.append(archivo.name)

        if archivos_movidos:
            self.logger.info(f"Se movieron {len(archivos_movidos)} archivos no JSON a '{self.carpeta_destino}'")
        else:
            self.logger.info("No se encontraron archivos no JSON para mover.")
        return archivos_movidos
