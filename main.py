# main.py (solo el inicio relevante)
import logging
from utils.logger import get_logger
import config
from services.Depurador import Depurador
from services.clonador_excel import ClonadorExcel
from services.reestructurador_excel import ReestructuradorExcel
from services.comparador_avista import ComparadorAvista

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Iniciando sistema...")

    # 1) ¿Desde dónde tomamos JSON?
    try:
        opt = input("¿Desde dónde quieres tomar JSON? [1=Carpeta Local / 2=SFTP-Davinci] (default 1): ").strip()
        modo = 2 if opt == "2" else 1
    except Exception:
        modo = config.MODO_INGESTA_DEFAULT

    # 2) Depuración solo si es local
    if modo == 1:
        dep = Depurador(config.RUTA_JSONS, config.RUTA_NO_JSON)
        dep.ejecutar()

    # 3) Clon (lee de local o SFTP)
    clon = ClonadorExcel(config.RUTA_JSONS, str(config.CARPETA_EXCEL_CLON), modo_ingesta=modo)
    if clon.generar_excel():
        logger.info("Clonación completada correctamente.")
    else:
        logger.error("Fallo en clonación.")
        raise SystemExit(1)

    # 4) Reestructurar
    reestr = ReestructuradorExcel(str(config.CARPETA_EXCEL_CLON), str(config.CARPETA_EXCEL_REESTRUCTURADO))
    if not reestr.reestructurar():
        logger.error("Fallo reestructurando.")
        raise SystemExit(1)

    logger.info("Continuando con el proceso de validación...")

    # 5) Comparación AVISTA (base dinámica: toma el último .xlsx de la carpeta)
    comp = ComparadorAvista(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_bases_avista=str(config.CARPETA_BASES_AVISTA),
        carpeta_salida=str(config.CARPETA_SALIDA_COMPARACION),
    )
    comp.comparar()
    # # Paso 6: Normalizador Excel
    # normalizador = NormalizadorExcel(config.CARPETA_EXCEL_REESTRUCTURADO, config.CARPETA_EXCEL_NORMALIZADO, config.CARPETA_EXCEL_FALLOS)
    # if normalizador.normalizar():
    #     logger.info("Normalización completada correctamente. Archivos generados.")
    # else:
    #     logger.warning("No se pudo normalizar el Excel.")