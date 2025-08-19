import logging
from pathlib import Path

def get_logger(nombre="ValidadorJSON", log_file="logs/validador.log"):
    # Crear carpeta de logs si no existe
    log_path = Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)

    # Evitar múltiples handlers
    if not logger.handlers:
        # Handler para consola
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(ch)

        # Handler para archivo
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)

    return logger
