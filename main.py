# main.py
import logging
from utils.logger import get_logger
import config
from pathlib import Path

# Servicios
from services.depurar import Depurador
from services.clonador_excel import ClonadorExcel
from services.reestructurador_excel import ReestructuradorExcel
from services.comparador_avista import ComparadorAvista
from services.normalizador_excel import NormalizadorExcel
from services.consolidador_final import ConsolidadorFinal

def _ask_path(prompt_txt: str, default_path: Path) -> str:
    """
    Permite al usuario cambiar una ruta. Enter = usa default.
    Devuelve siempre un string (la ruta elegida o la default).
    """
    print(f"\n{prompt_txt}\n[Enter para usar el valor por defecto]\nActual: {default_path}")
    r = input("Nueva ruta (opcional): ").strip('" ').strip()
    if not r:
        return str(default_path)
    p = Path(r)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return str(p)

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Iniciando sistema...")

    # 0) Permitir cambiar rutas (opcional)
    try:
        cambiar = input("¿Deseas cambiar rutas por defecto? [s/N]: ").strip().lower()
    except Exception:
        cambiar = "n"

    if cambiar == "s":
        config.RUTA_JSONS = _ask_path("Ruta de entrada de JSON:", Path(config.RUTA_JSONS))
        config.RUTA_NO_JSON = _ask_path("Ruta auxiliar (no JSON):", Path(config.RUTA_NO_JSON))
        config.CARPETA_RESULTADOS_DAVINCI = Path(_ask_path("Carpeta de resultados Davinci:", config.CARPETA_RESULTADOS_DAVINCI))
        # Alias internos recalculados al vuelo
        config.CARPETA_EXCEL_CLON = config.CARPETA_RESULTADOS_DAVINCI
        config.CARPETA_EXCEL_REESTRUCTURADO = config.CARPETA_RESULTADOS_DAVINCI
        config.CARPETA_EXCEL_NORMALIZADO = config.CARPETA_RESULTADOS_DAVINCI
        config.CARPETA_SALIDA_COMPARACION = config.CARPETA_RESULTADOS_DAVINCI
        config.CARPETA_EXCEL_UNIFICADO = config.CARPETA_RESULTADOS_DAVINCI
        # Base Avista opcional
        config.CARPETA_BASES_AVISTA = Path(_ask_path("Carpeta Base de Datos Avista:", config.CARPETA_BASES_AVISTA))

    # 1) ¿Desde dónde tomamos JSON?
    try:
        opt = input("¿Desde dónde quieres tomar JSON? [1=Carpeta Local / 2=SFTP-Davinci] (default 1): ").strip()
        modo = 2 if opt == "2" else 1
    except Exception:
        modo = config.MODO_INGESTA_DEFAULT

    # 2) Depuración NO debe detener el pipeline
    if modo == 1:
        # Modo local: los conflictos van a Escritorio/archivos conflicto (lo resuelve Depurador)
        dep = Depurador(
            carpeta_fuente=config.RUTA_JSONS,
            carpeta_conflicto_destino=None,
            modo_ingesta=1,
            logger=logger,
        )
    else:
        # Modo SFTP: mueve a <Resultados Davinci>/archivos conflicto
        dep = Depurador(
            carpeta_fuente=config.RUTA_JSONS,
            carpeta_conflicto_destino=config.CARPETA_RESULTADOS_DAVINCI / "archivos conflicto",
            modo_ingesta=2,
            logger=logger,
        )

    # Nota: ejecutar() SIEMPRE retorna True para no cortar el pipeline.
    dep.ejecutar()

    # 3) Clonación
    clon = ClonadorExcel(
        carpeta_json_local=config.RUTA_JSONS,
        carpeta_salida=str(config.CARPETA_EXCEL_CLON),
        modo_ingesta=modo
    )
    if not clon.generar_excel():
        logger.error("Fallo en clonación.")
        raise SystemExit(1)
    logger.info("Clonación completada correctamente.")

    # 4) Reestructurado
    reestr = ReestructuradorExcel(
        carpeta_excel_origen=str(config.CARPETA_EXCEL_CLON),
        carpeta_excel_destino=str(config.CARPETA_EXCEL_REESTRUCTURADO),
    )
    if not reestr.reestructurar():
        logger.error("Fallo reestructurando.")
        raise SystemExit(1)

    logger.info("Continuando con el proceso de validación...")

    # 5) Comparación AVISTA
    comp = ComparadorAvista(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_bases_avista=str(config.CARPETA_BASES_AVISTA),
        carpeta_salida=str(config.CARPETA_SALIDA_COMPARACION),
    )
    comp.comparar()

    # 6) Normalización
    normalizador = NormalizadorExcel(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_salida=str(config.CARPETA_EXCEL_NORMALIZADO),
        umbral_similitud=float(config.TOLERANCIA_TEXTO),
    )
    normalizador.normalizar()

    # 7) Unificado final
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
