from services.Depurador import Depurador
from services.clonador_excel import ClonadorExcel
from services.reestructurador_excel import ReestructuradorExcel
from services.normalizador_excel import NormalizadorExcel
from utils.logger import get_logger
from services.comparador_avista import ComparadorAvista
import config

logger = get_logger()

if __name__ == "__main__":
    logger.info("Iniciando sistema...")

    # Paso 1: Depurar carpeta
    depurador = Depurador(config.RUTA_JSONS, config.RUTA_NO_JSON)
    archivos_movidos = depurador.depurar()
    if archivos_movidos:
        logger.info(f"Archivos no JSON movidos: {archivos_movidos}")
    else:
        logger.info("No se encontraron archivos no JSON.")
    
    # Paso 2: Clonador JSON → Excel con nombre dinámico
    clonador = ClonadorExcel(config.RUTA_JSONS, config.CARPETA_EXCEL_CLON)
    if clonador.generar_excel():
        logger.info("Clonación completada correctamente.")
    else:
        logger.warning("No se pudo generar el Excel de clonación.")

    logger.info("Continuando con el proceso de validación...")

    # Paso 3: Reestructurar Excel (añadir columnas NN, Numero credito, Cedula)
    reestructurador = ReestructuradorExcel(config.CARPETA_EXCEL_CLON, config.CARPETA_EXCEL_REESTRUCTURADO)
    if reestructurador.reestructurar():
        logger.info("Reestructuración completada correctamente. Excel modificado creado.")
    else:
        logger.warning("No se pudo reestructurar el Excel.")

    comparador = ComparadorAvista(
        carpeta_excel_reestructurado=config.CARPETA_EXCEL_REESTRUCTURADO,
        ruta_avista_excel=config.RUTA_BASE_AVISTA,
        carpeta_salida=config.CARPETA_SALIDA_COMPARACION
    )
    comparador.comparar()

    # # Paso 4: Normalizador Excel
    # normalizador = NormalizadorExcel(config.CARPETA_EXCEL_REESTRUCTURADO, config.CARPETA_EXCEL_NORMALIZADO, config.CARPETA_EXCEL_FALLOS)
    # if normalizador.normalizar():
    #     logger.info("Normalización completada correctamente. Archivos generados.")
    # else:
    #     logger.warning("No se pudo normalizar el Excel.")