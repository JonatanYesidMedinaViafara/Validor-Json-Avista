# main.py
import logging
from utils.logger import get_logger
import config

# IMPORTS de servicios
from services.depurar import Depurador                     # <- el archivo es depurar.py
from services.clonador_excel import ClonadorExcel
from services.reestructurador_excel import ReestructuradorExcel
from services.comparador_avista import ComparadorAvista
from services.normalizador_excel import NormalizadorExcel
from services.consolidador_final import ConsolidadorFinal

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Iniciando sistema...")

    # 1) ¿Desde dónde tomamos JSON?
    try:
        opt = input("¿Desde dónde quieres tomar JSON? [1=Carpeta Local / 2=SFTP-Davinci] (default 1): ").strip()
        modo = 2 if opt == "2" else 1
    except Exception:
        modo = config.MODO_INGESTA_DEFAULT

    # 2) Depuración (solo local): mueve lo que NO es .json a RUTA_NO_JSON
    if modo == 1:
        dep = Depurador(config.RUTA_JSONS, config.RUTA_NO_JSON)
        dep.ejecutar()

    # 3) Clonación (lee local o SFTP) → guarda en Resultados Davinci
    clon = ClonadorExcel(
        carpeta_json_local=config.RUTA_JSONS,
        carpeta_salida=str(config.CARPETA_EXCEL_CLON),
        modo_ingesta=modo
    )
    if clon.generar_excel():
        logger.info("Clonación completada correctamente.")
    else:
        logger.error("Fallo en clonación.")
        raise SystemExit(1)

    # 4) Reestructurado → guarda en Resultados Davinci
    reestr = ReestructuradorExcel(
        carpeta_excel_origen=str(config.CARPETA_EXCEL_CLON),
        carpeta_excel_destino=str(config.CARPETA_EXCEL_REESTRUCTURADO),
    )
    if not reestr.reestructurar():
        logger.error("Fallo reestructurando.")
        raise SystemExit(1)

    logger.info("Continuando con el proceso de validación...")

    # 5) Comparación AVISTA (toma SIEMPRE el último Excel de Avista)
    comp = ComparadorAvista(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_bases_avista=str(config.CARPETA_BASES_AVISTA),
        carpeta_salida=str(config.CARPETA_SALIDA_COMPARACION),
    )
    comp.comparar()   # genera SOLO '..._evidencia_avista_unica.xlsx' en Resultados Davinci

    # 6) Normalización (un único archivo con columna 'Estado Normalizado')
    normalizador = NormalizadorExcel(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_salida=str(config.CARPETA_EXCEL_NORMALIZADO),
        umbral_similitud=float(config.TOLERANCIA_TEXTO),
    )
    normalizador.normalizar()

    # 7) Unificado final (un solo Excel con hojas: Clonación Json, Reestructurado, Resultado Normalizado, Avista Evidencia)
    consol = ConsolidadorFinal(
        carpeta_clon=str(config.CARPETA_EXCEL_CLON),
        carpeta_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_normalizado=str(config.CARPETA_EXCEL_NORMALIZADO),
        carpeta_comparacion=str(config.CARPETA_SALIDA_COMPARACION),
        carpeta_salida_unificado=str(config.CARPETA_EXCEL_UNIFICADO),
    )
    salida = consol.consolidar()
    if salida:
        logger.info(f"Archivo unificado final creado: {salida}")
    else:
        logger.warning("No se pudo crear el archivo unificado final.")
