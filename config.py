# config.py
from pathlib import Path

# --- Rutas base del proyecto ---
RUTA_JSONS = r"C:\Users\jymv1575\Desktop\Archivos Json a Validar"
RUTA_NO_JSON = r"C:\Users\jymv1575\Desktop\Archivos no Json"
CARPETA_EXCEL_CLON = Path(r"C:\Users\jymv1575\Desktop\Excel Inicial")
CARPETA_EXCEL_REESTRUCTURADO = Path(r"C:\Users\jymv1575\Desktop\Excel Reestructurado")
CARPETA_EXCEL_NORMALIZADO = Path(r"C:\Users\jymv1575\Desktop\Excel Normalizado")
CARPETA_EXCEL_FALLOS = Path(r"C:\Users\jymv1575\Desktop\Excel Fallos")

# --- Comparación Avista ---
RUTA_BASE_AVISTA = r"C:\Users\jymv1575\Desktop\Base de Datos Avista\Base de Datos Avista.xlsx"
CARPETA_SALIDA_COMPARACION = r"C:\Users\jymv1575\Desktop\Resultado de la comparacion positivo"

# --- Documentos (definen las 9 columnas de evidencia en la hoja única) ---
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

# Tolerancia para comparaciones de texto (SequenceMatcher)
TOLERANCIA_TEXTO = 0.70

# --- Mapeo por DOCUMENTO ---
# clave izquierda = columna en AVISTA
# valor["re"]      = columna en el Excel REESTRUCTURADO
# valor["tipo"]    = "texto" | "numero" | "fecha"
# *Evita claves repetidas en un mismo dict: usa sufijos " 2", " 3", etc.*
DOCUMENTOS_MAPEO = {
    # ---------------------------
    # CEDULA COMPARADA
    # ---------------------------
    "CEDULA COMPARADA": {
        "CEDULA":             {"re": "Cedula",                  "tipo": "numero"},
        "CEDULA":             {"re": "Cedula Cedula",           "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Cedula Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Cedula Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Cedula Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Cedula Segundo Nombre",   "tipo": "texto"},
        "FECHA NACIMIENTO":   {"re": "cedula_fecha_nacimiento", "tipo": "fecha"},
    },

    # ---------------------------
    # DATACREDITO
    # ---------------------------
    "DATACREDITO": {
        "PRIMER APELLIDO":    {"re": "Datacredito Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Datacredito Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Datacredito Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Datacredito Segundo Nombre",   "tipo": "texto"},
    },

    # ---------------------------
    # SEGURO DE VIDA
    # ---------------------------
    "SEGURO DE VIDA": {
        "CEDULA":             {"re": "Seguro De Vida Cedula",                            "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Seguro De Vida Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Seguro De Vida Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Seguro De Vida Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Seguro De Vida Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "PRIMER APELLIDO":  {"re": "Seguro De Vida Primer Apellido",                    "tipo": "texto"},
        "PRIMER NOMBRE":    {"re": "Seguro De Vida Primer Nombre",                      "tipo": "texto"},
        "SEGUNDO APELLIDO": {"re": "Seguro De Vida Segundo Apellido",                   "tipo": "texto"},
        "SEGUNDO NOMBRE":   {"re": "Seguro De Vida Segundo Nombre",                     "tipo": "texto"},
    },

    # ---------------------------
    # FIANZA
    # ---------------------------
    "FIANZA": {
        "CEDULA":             {"re": "Solicitud Fianza Cedula",                            "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Solicitud Fianza Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Solicitud Fianza Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Solicitud Fianza Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Solicitud Fianza Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "PRIMER APELLIDO":  {"re": "Solicitud Fianza Primer Apellido",                    "tipo": "texto"},
        "PRIMER NOMBRE":    {"re": "Solicitud Fianza Primer Nombre",                      "tipo": "texto"},
        "SEGUNDO APELLIDO": {"re": "Solicitud Fianza Segundo Apellido",                   "tipo": "texto"},
        "SEGUNDO NOMBRE":   {"re": "Solicitud Fianza Segundo Nombre",                     "tipo": "texto"},
    },

    # ---------------------------
    # DESPRENDIBLE
    # ---------------------------
    "DESPRENDIBLE": {
        "CEDULA":             {"re": "Desprendible Nomina Cedula",          "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Desprendible Nomina Primer Apellido", "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Desprendible Nomina Primer Nombre",   "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Desprendible Nomina Segundo Apellido","tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Desprendible Nomina Segundo Nombre",  "tipo": "texto"},
        "EMISOR":             {"re": "desprendible_nomina_pagaduria",       "tipo": "texto"},
        "SALARIO":            {"re": "desprendible_nomina_salario",         "tipo": "numero"},
        # Vigencia debe ser <= 3 meses antes de FECHA DESEMBOLSO (Avista)
        "FECHA DESEMBOLSO":   {
            "re": "desprendible_nomina_vigencia",
            "tipo": "fecha",
            "validacion_especial": "max_3_meses_antes"
        },
    },

    # ---------------------------
    # FORMATO CONOCIMIENTO
    # ---------------------------
    "FORMATO CONOCIMIENTO": {
        "PRIMER APELLIDO":    {"re": "Formato Conocimiento Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Formato Conocimiento Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Formato Conocimiento Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Formato Conocimiento Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "CEDULA":             {"re": "formato_conocimiento_cedula_firma_electronica",           "tipo": "numero"},
        "PLAZO INICIAL":      {"re": "formato_conocimiento_plazo_meses",                         "tipo": "numero"},
        "MONTO INICIAL":      {"re": "formato_conocimiento_valor_total_credito",                 "tipo": "numero"},
    },

    # ---------------------------
    # LIBRANZA
    # ---------------------------
    "LIBRANZA": {
        "CEDULA":             {"re": "Libranza Cedula",                             "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Libranza Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Libranza Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Libranza Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Libranza Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "PRIMER APELLIDO":  {"re": "Libranza Primer Apellido",                    "tipo": "texto"},
        "PRIMER NOMBRE":    {"re": "Libranza Primer Nombre",                      "tipo": "texto"},
        "SEGUNDO APELLIDO": {"re": "Libranza Segundo Apellido",                   "tipo": "texto"},
        "SEGUNDO NOMBRE":   {"re": "Libranza Segundo Nombre",                     "tipo": "texto"},
        "CEDULA":           {"re": "libranza_cedula_firma_electronica",           "tipo": "numero"},
        "OPERACIÓN":          {"re": "libranza_numero_credito",                     "tipo": "numero"},
        "EMISOR":             {"re": "libranza_pagaduria",                          "tipo": "texto"},
        "PLAZO INICIAL":      {"re": "libranza_plazo",                              "tipo": "numero"},
        "CUOTA CORRIENTE":    {"re": "libranza_valor_cuota",                        "tipo": "numero"},
        "MONTO INICIAL":      {"re": "libranza_valor_prestamo",                     "tipo": "numero"},
    },

    # ---------------------------
    # SOLICITUD DE CREDITO
    # ---------------------------
    "SOLICITUD DE CREDITO": {
        # Avista vs Reestructurado
        "OPERACIÓN":          {"re": "Numero credito",                         "tipo": "numero"},
        "CEDULA":             {"re": "Solicitud Credito Cedula",               "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Solicitud Credito Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Solicitud Credito Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Solicitud Credito Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Solicitud Credito Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "PRIMER APELLIDO":  {"re": "Solicitud Credito Primer Apellido",                    "tipo": "texto"},
        "PRIMER NOMBRE":    {"re": "Solicitud Credito Primer Nombre",                      "tipo": "texto"},
        "SEGUNDO APELLIDO": {"re": "Solicitud Credito Segundo Apellido",                   "tipo": "texto"},
        "SEGUNDO NOMBRE":   {"re": "Solicitud Credito Segundo Nombre",                     "tipo": "texto"},
        "CEDULA":           {"re": "solicitud_credito_cedula_firma_electronica",           "tipo": "numero"},
        "OPERACIÓN":        {"re": "solicitud_credito_numero_credito",                     "tipo": "numero"},

        # Reestructurado vs Reestructurado (se reporta en la misma columna)
        "RE_vs_RE__SOLICITUD": {
            "re":  "solicitud_credito_solicitud",
            "re2": "amortizacion_numero_solicitud",
            "tipo": "numero",
            "comparar_recontra_re": True
        },
    },

    # ---------------------------
    # AMORTIZACION
    # ---------------------------
    "AMORTIZACION": {
        "OPERACIÓN":          {"re": "Numero credito",                          "tipo": "numero"},
        "CEDULA":             {"re": "amortizacion_cedula_firma_electronica",   "tipo": "numero"},
        "PRIMER APELLIDO":    {"re": "Amortizacion Firma Electrónica Primer Apellido",  "tipo": "texto"},
        "PRIMER NOMBRE":      {"re": "Amortizacion Firma Electrónica Primer Nombre",    "tipo": "texto"},
        "SEGUNDO APELLIDO":   {"re": "Amortizacion Firma Electrónica Segundo Apellido", "tipo": "texto"},
        "SEGUNDO NOMBRE":     {"re": "Amortizacion Firma Electrónica Segundo Nombre",   "tipo": "texto"},
        "EMISOR":             {"re": "amortizacion_pagaduria",                  "tipo": "texto"},
        "PLAZO INICIAL":      {"re": "amortizacion_plazo_meses",                "tipo": "numero"},
        "CUOTA CORRIENTE":    {"re": "amortizacion_valor_cuota",                "tipo": "numero"},
        "MONTO INICIAL":      {"re": "amortizacion_valor_credito",              "tipo": "numero"},

        # Avista (TASA NOMINAL mensual) vs cálculo mensual desde amortizacion_tasa_interes (anual %)
        "TASA NOMINAL":       {
            "re": "amortizacion_tasa_interes",
            "tipo": "numero",
            "validacion_especial": "tasa_mensual_redondeada_4"
        },

        # Reestructurado vs Reestructurado: amortizacion_numero_solicitud <-> solicitud_credito_solicitud
        "RE_vs_RE__AMORT_SOL": {
            "re":  "amortizacion_numero_solicitud",
            "re2": "solicitud_credito_solicitud",
            "tipo": "numero",
            "comparar_recontra_re": True
        },
    },
}
