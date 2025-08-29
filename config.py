# config.py
from pathlib import Path

# --- Orígenes de JSON ---
# 1 = Carpeta local, 2 = SFTP
MODO_INGESTA_DEFAULT = 1

# Local
RUTA_JSONS = r"C:\Users\jymv1575\Desktop\Archivos Json a Validar"
RUTA_NO_JSON = r"C:\Users\jymv1575\Desktop\Archivos no Json"

# SFTP (usa almacenamiento seguro para credenciales en producción)
SFTP_HOST = "securefile.coomeva.com.co"
SFTP_PORT = 2224
SFTP_USER = "davinci"
SFTP_PASS = "LoIlmC4H31FBAJG"
SFTP_DIR_JSONS = "davinci/procesados-qa"   # carpeta remota donde están los .json

# --- ÚNICA carpeta de resultados ---
CARPETA_RESULTADOS_DAVINCI = Path(r"C:\Users\jymv1575\Desktop\Resultados Davinci")
CARPETA_RESULTADOS_DAVINCI.mkdir(parents=True, exist_ok=True)

# Alias internos → todo apunta a la misma carpeta
CARPETA_EXCEL_CLON = CARPETA_RESULTADOS_DAVINCI              # "Clonación Json"
CARPETA_EXCEL_REESTRUCTURADO = CARPETA_RESULTADOS_DAVINCI    # "Reestructurado"
CARPETA_EXCEL_NORMALIZADO = CARPETA_RESULTADOS_DAVINCI       # "Resultado Normalizado"
CARPETA_EXCEL_FALLOS = CARPETA_RESULTADOS_DAVINCI            # (si se usa)
CARPETA_SALIDA_COMPARACION = CARPETA_RESULTADOS_DAVINCI      # "Avista Evidencia"
CARPETA_EXCEL_UNIFICADO = CARPETA_RESULTADOS_DAVINCI         # "Davinci_Resultado" final

# --- Bases Avista (dinámico = toma el último .xlsx de la carpeta) ---
CARPETA_BASES_AVISTA = Path(r"C:\Users\jymv1575\Desktop\Base de Datos Avista")

# --- Evidencia por documento (9 columnas) ---
DOCUMENTOS = [
    "CEDULA COMPARADA",
    "DESPRENDIBLE",
    "DATACREDITO",
    "FORMATO CONOCIMIENTO",
    "LIBRANZA",
    "SOLICITUD DE CREDITO",
    "FIANZA",
    "SEGURO DE VIDA",
    "AMORTIZACION",
]

# Tolerancia (texto) para SequenceMatcher
TOLERANCIA_TEXTO = 0.70

# ---- Mapeos (resumido a nombre completo donde aplique) ----
DOCUMENTOS_MAPEO = {
    "CEDULA COMPARADA": {
        "NOMBRE COMPLETO": {"re": "Cedula Nombre Completo", "tipo": "texto"},
        "CEDULA":          {"re": "Cedula",                 "tipo": "numero"},
        "CEDULA":          {"re": "cedula_numero_documento","tipo": "numero"},
        "FECHA NACIMIENTO":{"re": "cedula_fecha_nacimiento","tipo": "fecha"},
    },
    "DATACREDITO": {
        "NOMBRE COMPLETO": {"re": "Datacredito Nombre Completo", "tipo": "texto"},
    },
    "SEGURO DE VIDA": {
        "NOMBRE COMPLETO":   {"re": "Seguro De Vida Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Seguro De Vida Firma Electrónica Nombre Completo", "tipo": "texto"},
        "CEDULA":            {"re": "Seguro De Vida Cedula",                            "tipo": "numero"},
    },
    "FIANZA": {
        "NOMBRE COMPLETO":   {"re": "Solicitud Fianza Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Solicitud Fianza Firma Electrónica Nombre Completo", "tipo": "texto"},
        "CEDULA":            {"re": "Solicitud Fianza Cedula",                            "tipo": "numero"},
    },
    "DESPRENDIBLE": {
        "NOMBRE COMPLETO": {"re": "Desprendible Nomina Nombre Completo", "tipo": "texto"},
        "CEDULA":          {"re": "Desprendible Nomina Cedula",          "tipo": "numero"},
        "EMISOR":          {"re": "desprendible_nomina_pagaduria",       "tipo": "texto"},
        "SALARIO":         {"re": "desprendible_nomina_salario",         "tipo": "numero"},
        # Especial: vigencia debe estar entre (desembolso-3m, desembolso), comparando por mes/año
        "FECHA DESEMBOLSO": {
            "re": "desprendible_nomina_vigencia",
            "tipo": "fecha",
            "validacion_especial": "max_3_meses_antes_mes_anio"
        },
    },
    "FORMATO CONOCIMIENTO": {
        "NOMBRE COMPLETO":   {"re": "Formato Conocimiento Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Formato Conocimiento Firma Electrónica Nombre Completo", "tipo": "texto"},
        "CEDULA":            {"re": "formato_conocimiento_cedula_firma_electronica",          "tipo": "numero"},
        "PLAZO INICIAL":     {"re": "formato_conocimiento_plazo_meses",                        "tipo": "numero"},
        "MONTO INICIAL":     {"re": "formato_conocimiento_valor_total_credito",                "tipo": "numero"},
    },
    "LIBRANZA": {
        "NOMBRE COMPLETO":   {"re": "Libranza Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Libranza Firma Electrónica Nombre Completo", "tipo": "texto"},
        "CEDULA":            {"re": "Libranza Cedula",                            "tipo": "numero"},
        "CEDULA 2":          {"re": "libranza_cedula_firma_electronica",          "tipo": "numero"},
        "OPERACIÓN":         {"re": "libranza_numero_credito",                    "tipo": "numero"},
        "EMISOR":            {"re": "libranza_pagaduria",                         "tipo": "texto"},
        "PLAZO INICIAL":     {"re": "libranza_plazo",                             "tipo": "numero"},
        "CUOTA CORRIENTE":   {"re": "libranza_valor_cuota",                       "tipo": "numero"},
        "MONTO INICIAL":     {"re": "libranza_valor_prestamo",                    "tipo": "numero"},
    },
    "SOLICITUD DE CREDITO": {
        "NOMBRE COMPLETO":   {"re": "Solicitud Credito Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Solicitud Credito Firma Electrónica Nombre Completo", "tipo": "texto"},
        "OPERACIÓN":         {"re": "Numero credito",                           "tipo": "numero"},
        "CEDULA":            {"re": "Solicitud Credito Cedula",                 "tipo": "numero"},
        "OPERACIÓN 2":       {"re": "solicitud_credito_numero_credito",         "tipo": "numero"},
        "RE_vs_RE__SOLICITUD": {
            "re":  "solicitud_credito_solicitud",
            "re2": "amortizacion_numero_solicitud",
            "tipo": "numero",
            "comparar_recontra_re": True
        },
    },
    "AMORTIZACION": {
        "NOMBRE COMPLETO":   {"re": "Amortizacion Nombre Completo",                   "tipo": "texto"},
        "NOMBRE COMPLETO 2": {"re": "Amortizacion Firma Electrónica Nombre Completo", "tipo": "texto"},
    },
}
