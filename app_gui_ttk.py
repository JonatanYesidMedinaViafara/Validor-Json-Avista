# app_gui_ttk.py
# GUI unificado con ttkbootstrap: "Completo" + "Por Etapas"
# pip install ttkbootstrap

from __future__ import annotations
import os
import sys
import json
import queue
import shutil
import logging
import threading
import re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, END

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

# ----- Tu código existente -----
import config
from utils.logger import get_logger
from services.depurar import Depurador
from services.clonador_excel import ClonadorExcel
from services.reestructurador_excel import ReestructuradorExcel
from services.comparador_avista import ComparadorAvista
from services.normalizador_excel import NormalizadorExcel
from services.consolidador_final import ConsolidadorFinal


# =========================
# Persistencia de settings
# =========================
SETTINGS_FILE = Path(__file__).with_name("gui_settings.json")

def _load_settings():
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            # Asegurar que 'modo' sea un entero
            if 'modo' in settings:
                if isinstance(settings['modo'], str):
                    # Extraer el número si está en formato "Carpeta Local (1)"
                    if '(' in settings['modo'] and ')' in settings['modo']:
                        match = re.search(r'\((\d+)\)', settings['modo'])
                        if match:
                            settings['modo'] = int(match.group(1))
                        else:
                            settings['modo'] = 1  # Valor por defecto
                    else:
                        try:
                            settings['modo'] = int(settings['modo'])
                        except ValueError:
                            settings['modo'] = 1
                # Asegurar que sea 1 o 2
                settings['modo'] = 1 if settings['modo'] == 1 else 2
            return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            pass
    return {
        "theme": "flatly",
        "modo": 1,
        "MOSTRAR_DETALLE_TASA": bool(getattr(config, "MOSTRAR_DETALLE_TASA", True)),
        "TASA_TOLERANCIA": float(getattr(config, "TASA_TOLERANCIA", 0.001)),
        "RUTA_JSONS": str(config.RUTA_JSONS),
        "RUTA_NO_JSON": str(config.RUTA_NO_JSON),
        "CARPETA_RESULTADOS_DAVINCI": str(config.CARPETA_RESULTADOS_DAVINCI),
        "CARPETA_BASES_AVISTA": str(config.CARPETA_BASES_AVISTA),
    }

def _save_settings(values):
    # Asegurar que el modo sea un entero
    modo_value = values["modo"]
    if isinstance(modo_value, str):
        if '(' in modo_value and ')' in modo_value:
            match = re.search(r'\((\d+)\)', modo_value)
            if match:
                modo_value = int(match.group(1))
            else:
                modo_value = 1
        else:
            try:
                modo_value = int(modo_value)
            except ValueError:
                modo_value = 1
    
    data = {
        "theme": values["theme"],
        "modo": 1 if modo_value == 1 else 2,  # Asegurar que sea 1 o 2
        "MOSTRAR_DETALLE_TASA": bool(values["detalle_tasa"]),
        "TASA_TOLERANCIA": float(values["tol_tasa"]),
        "RUTA_JSONS": values["ruta_jsons"],
        "RUTA_NO_JSON": values["ruta_nojson"],
        "CARPETA_RESULTADOS_DAVINCI": values["ruta_resultados"],
        "CARPETA_BASES_AVISTA": values["ruta_avista"],
    }
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# =========================
# Logging -> GUI
# =========================
class GuiQueueHandler(logging.Handler):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record):
        try:
            self.q.put(self.format(record))
        except Exception:
            pass


# =========================
# Utilidades Depuración
# =========================
def _es_json(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() == ".json"

def _desktop_conflict_folder() -> Path:
    # Escritorio del usuario, cross-platform
    if sys.platform.startswith("win"):
        desktop = Path(os.path.join(os.path.expanduser("~"), "Desktop"))
    elif sys.platform == "darwin":
        desktop = Path.home() / "Desktop"
    else:
        desktop = Path.home() / "Escritorio"
        if not desktop.exists():
            desktop = Path.home() / "Desktop"
    return desktop / "archivos conflicto"

def _mover_no_json(carpeta_src: Path, carpeta_destino: Path, log_fn):
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    movidos = 0
    for p in Path(carpeta_src).iterdir():
        if p.is_file() and not _es_json(p):
            try:
                destino = carpeta_destino / p.name
                # evitar overwrite
                if destino.exists():
                    destino = carpeta_destino / f"{destino.stem}_{datetime.now().strftime('%H%M%S')}{destino.suffix}"
                shutil.move(str(p), str(destino))
                movidos += 1
            except Exception as e:
                log_fn(f"⚠️ No se pudo mover '{p.name}': {e}")
    if movidos == 0:
        log_fn("ℹ️ No se encontraron archivos en conflicto (no-JSON).")
    else:
        log_fn(f"📦 Movidos {movidos} archivo(s) no-JSON a: {carpeta_destino}")


def _depurar_wrapper(modo: int, log_fn) -> bool:
    """
    Depuración tolerante:
    - Si no hay no-JSON, no corta the pipeline.
    - Mueve no-JSON a 'archivos conflicto' según modo.
    - Soporta versión 'nueva' o 'vieja' de Depurador (constructor flexible).
    """
    src = Path(str(config.RUTA_JSONS))
    if not src.exists():
        log_fn(f"⚠️ Carpeta de JSON no existe: {src}")
        return True  # no cortamos

    # mover no-JSON primero, según modo
    if modo == 1:
        conflict = _desktop_conflict_folder()
    else:
        conflict = Path(str(config.CARPETA_RESULTADOS_DAVINCI)) / "archivos conflicto"
    _mover_no_json(src, conflict, log_fn)

    # Ejecutar Depurador "oficial" por compatibilidad (si falla no detenemos)
    try:
        # Nueva firma
        dep = Depurador(
            carpeta_fuente=str(config.RUTA_JSONS),
            carpeta_conflicto_destino=str(conflict),
            modo_ingesta=modo,
            logger=get_logger()
        )
        ok = dep.ejecutar()
        if ok:
            log_fn("✅ Depuración completada (nueva firma).")
            return True
        else:
            log_fn("⚠️ Depuración reportó fallo, continuaremos.")
            return True
    except TypeError:
        # Firma antigua: Depurador(RUTA_JSONS, RUTA_NO_JSON)
        try:
            dep = Depurador(str(config.RUTA_JSONS), str(config.RUTA_NO_JSON))
            ok = dep.ejecutar()
            if ok:
                log_fn("✅ Depuración completada (firma antigua).")
            else:
                log_fn("⚠️ Depuración antigua reportó fallo, continuaremos.")
        except Exception as e:
            log_fn(f"⚠️ Depurador no ejecutado: {e}")
        return True
    except Exception as e:
        log_fn(f"⚠️ Depuración no pudo correr: {e}")
        return True


# =========================
# Wrappers de etapas
# =========================
def etapa_depurar(modo, log):     return _depurar_wrapper(modo, log)
def etapa_clonar(modo, log):
    c = ClonadorExcel(
        carpeta_json_local=config.RUTA_JSONS,
        carpeta_salida=str(config.CARPETA_EXCEL_CLON),
        modo_ingesta=modo
    )
    ok = c.generar_excel()
    if not ok: log("❌ Error en Clonación")
    return ok

def etapa_reestructurar(log):
    r = ReestructuradorExcel(
        carpeta_excel_origen=str(config.CARPETA_EXCEL_CLON),
        carpeta_excel_destino=str(config.CARPETA_EXCEL_REESTRUCTURADO),
    )
    ok = r.reestructurar()
    if not ok: log("❌ Error en Reestructurado")
    return ok

def etapa_comparar(log):
    c = ComparadorAvista(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_bases_avista=str(config.CARPETA_BASES_AVISTA),
        carpeta_salida=str(config.CARPETA_SALIDA_COMPARACION),
    )
    return c.comparar()

def etapa_normalizar(log):
    n = NormalizadorExcel(
        carpeta_excel_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_salida=str(config.CARPETA_EXCEL_NORMALIZADO),
        umbral_similitud=float(config.TOLERANCIA_TEXTO),
    )
    return n.normalizar()

def etapa_consolidar(log):
    z = ConsolidadorFinal(
        carpeta_clon=str(config.CARPETA_EXCEL_CLON),
        carpeta_reestructurado=str(config.CARPETA_EXCEL_REESTRUCTURADO),
        carpeta_normalizado=str(config.CARPETA_EXCEL_NORMALIZADO),
        carpeta_comparacion=str(config.CARPETA_SALIDA_COMPARACION),
        carpeta_salida_unificado=str(config.CARPETA_EXCEL_UNIFICADO),
    )
    salida = z.consolidar()
    if salida:
        log(f"✅ Unificado final creado: {salida}")
        return True
    log("⚠️ No se pudo crear el unificado final")
    return False


# =========================
# App GUI
# =========================
class App(tb.Window):
    def __init__(self):
        self.settings = _load_settings()
        super().__init__(title="Validador Davinci __JYMV_BOT__", themename=self.settings["theme"], size=(1180, 760))

        # logger->GUI
        self.log_queue = queue.Queue()
        self.logger = get_logger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(GuiQueueHandler(self.log_queue))

        # estado
        self.thread = None
        self.stop_event = threading.Event()
        self.running = False

        # UI
        self._build_ui()
        self._pump_logs()

    # ---------- UI ----------
    def _build_ui(self):
        self.nb = tb.Notebook(self, bootstyle=SECONDARY)
        self.nb.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Pestañas
        self.page_full   = tb.Frame(self.nb)   # Completo
        self.page_steps  = tb.Frame(self.nb)   # Por etapas (antiguo)
        self.page_config = tb.Frame(self.nb)   # Configuración
        self.page_logs   = tb.Frame(self.nb)   # Logs

        self.nb.add(self.page_full,   text="Completo")
        self.nb.add(self.page_steps,  text="Por Etapas")
        self.nb.add(self.page_config, text="Configuración")
        self.nb.add(self.page_logs,   text="Logs")

        # Construir contenido
        self._build_full()       # Pestaña NUEVA (pipeline completo)
        self._build_steps()      # Pestaña ANTIGUA (unit tests)
        self._build_config()     # Config
        self._build_logs()       # Consola

    # ======= pestaña "Completo" =======
    def _build_full(self):
        # Marco superior
        top = tb.Frame(self.page_full)
        top.pack(fill=X, padx=12, pady=12)

        # Tema
        tb.Label(top, text="Tema:", anchor="w").pack(side=LEFT, padx=(0, 6))
        self.theme_var = tk.StringVar(value=self.style.theme_use())
        theme_menu = tb.Combobox(top, textvariable=self.theme_var, state="readonly",
                                 values=sorted(tb.Style().theme_names()), width=16)
        theme_menu.pack(side=LEFT)
        theme_menu.bind("<<ComboboxSelected>>", self._on_theme_change)

        # Modo
        tb.Label(top, text="  Modo:", anchor="w").pack(side=LEFT, padx=(16, 6))
        
        # Asegurar que el valor del modo sea un entero
        modo_value = self.settings.get("modo", 1)
        if isinstance(modo_value, str):
            if '(' in modo_value and ')' in modo_value:
                match = re.search(r'\((\d+)\)', modo_value)
                if match:
                    modo_value = int(match.group(1))
                else:
                    modo_value = 1
            else:
                try:
                    modo_value = int(modo_value)
                except ValueError:
                    modo_value = 1
        
        self.modo_full = tk.IntVar(value=modo_value)
        tb.Radiobutton(top, text="1 - Local", variable=self.modo_full, value=1, bootstyle="info-toolbutton").pack(side=LEFT)
        tb.Radiobutton(top, text="2 - SFTP",  variable=self.modo_full, value=2, bootstyle="secondary-toolbutton").pack(side=LEFT)

        # Botones
        self.btn_parar_full = tb.Button(top, text="Detener", bootstyle="danger-outline", command=self.cancel_run, state="disabled")
        self.btn_parar_full.pack(side=RIGHT, padx=(6,0))
        self.btn_iniciar_full = tb.Button(top, text="Iniciar Proceso", bootstyle="success", command=self.run_all_full)
        self.btn_iniciar_full.pack(side=RIGHT)

        # Frame de rutas
        self._paths_block(self.page_full)

        # Frame de progreso y estado
        frm_actions = tb.Frame(self.page_full)
        frm_actions.pack(fill=X, padx=12, pady=(0,12))

        self.pb_full = tb.Progressbar(frm_actions, mode="indeterminate", bootstyle="info-striped")
        self.pb_full.pack(fill=X, expand=True, side=LEFT)

        self.lbl_status_full = tb.Label(frm_actions, text="Listo.", anchor="e")
        self.lbl_status_full.pack(side=RIGHT, padx=(8,0))

        # Frame para mostrar el progreso de etapas
        self.etapas_frame = tb.Frame(self.page_full)
        self.etapas_frame.pack(fill=X, padx=12, pady=(0,12))
        
        # Crear etiquetas para cada etapa
        self.etapas = [
            "Depurar", "Clonar", "Reestructurar", 
            "Comparar", "Normalizar", "Consolidar"
        ]
        self.etapa_labels = {}
        
        for i, etapa in enumerate(self.etapas):
            frame = tb.Frame(self.etapas_frame)
            frame.pack(fill=X, pady=2)
            
            lbl_name = tb.Label(frame, text=etapa, width=15, anchor="w")
            lbl_name.pack(side=LEFT)
            
            lbl_status = tb.Label(frame, text="⏳ Pendiente", foreground="gray")
            lbl_status.pack(side=LEFT, padx=(10,0))
            
            self.etapa_labels[etapa] = lbl_status

    def _paths_block(self, parent):
        frm = tb.Labelframe(parent, text="Rutas", padding=10)
        frm.pack(fill=X, padx=8, pady=6)

        def row(label, var, init, browse=True):
            r = tb.Frame(frm)
            r.pack(fill=X, pady=4)
            tb.Label(r, text=label, width=28, anchor="w").pack(side=LEFT)
            ent = tb.Entry(r, textvariable=var)
            ent.pack(side=LEFT, fill=X, expand=YES, padx=6)
            var.set(init)
            if browse:
                tb.Button(r, text="Examinar…", bootstyle=SECONDARY,
                          command=lambda v=var: self._browse_dir(v)).pack(side=LEFT)

        self.var_jsons = tk.StringVar()
        self.var_nojson = tk.StringVar()
        self.var_result = tk.StringVar()
        self.var_avista = tk.StringVar()

        row("Ruta de JSON:", self.var_jsons, str(config.RUTA_JSONS))
        row("Ruta (aux) no JSON:", self.var_nojson, str(config.RUTA_NO_JSON))
        row("Carpeta Resultados Davinci:", self.var_result, str(config.CARPETA_RESULTADOS_DAVINCI))
        row("Carpeta Base de Datos Avista:", self.var_avista, str(config.CARPETA_BASES_AVISTA))

        tb.Label(frm, text="* En modo 1: no-JSON → Escritorio/archivos conflicto\n"
                           "* En modo 2: no-JSON → Resultados Davinci/archivos conflicto",
                 justify="left").pack(anchor="w", pady=(4,0))

    # ======= pestaña "Por Etapas" (tu GUI anterior) =======
    def _build_steps(self):
        top = tb.Frame(self.page_steps)
        top.pack(fill=X, padx=6, pady=(8, 4))
        tb.Label(top, text="Ejecución por Etapas (Pruebas Unitarias)", font="-size 13 -weight bold").pack(side=LEFT)

        tb.Button(top, text="Ejecutar TODO", bootstyle=SUCCESS, command=self.run_all_steps).pack(side=RIGHT, padx=4)
        tb.Button(top, text="Cancelar", bootstyle=DANGER, command=self.cancel_run).pack(side=RIGHT)

        # Progreso general
        self.total_steps = 6
        self.pb_steps_total = tb.Progressbar(self.page_steps, mode="determinate", bootstyle=INFO, maximum=self.total_steps)
        self.pb_steps_total.pack(fill=X, padx=12, pady=(6, 12))
        self.steps_completed = 0

        grid = tb.Frame(self.page_steps)
        grid.pack(fill=BOTH, expand=YES, padx=8, pady=2)

        self.steps = [
            ("Depurar", self.run_depurar_single),
            ("Clonar", self.run_clonar_single),
            ("Reestructurar", self.run_reestructurar_single),
            ("Comparar", self.run_comparar_single),
            ("Normalizar", self.run_normalizar_single),
            ("Consolidar", self.run_consolidar_single),
        ]
        self.step_badges = {}
        self.step_spinners = {}

        for i, (name, fn) in enumerate(self.steps):
            card = tb.Labelframe(grid, text=name, bootstyle=PRIMARY)
            r = i // 3
            c = i % 3
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            grid.grid_columnconfigure(c, weight=1)
            grid.grid_rowconfigure(r, weight=1)

            badge = tb.Label(card, text="IDLE", bootstyle=SECONDARY, padding=(8,4))
            badge.pack(side=TOP, anchor="e", padx=8, pady=6)
            self.step_badges[name] = badge

            spin = tb.Progressbar(card, mode="indeterminate", bootstyle=WARNING)
            spin.pack(fill=X, padx=10, pady=4)
            self.step_spinners[name] = spin

            tb.Button(card, text=f"Ejecutar {name}", bootstyle=OUTLINE, command=fn).pack(pady=(6, 8))
            tb.Separator(card).pack(fill=X, padx=8, pady=8)
            tb.Label(card, text=f"Estado de {name}").pack(pady=(0,6))

    # ======= pestaña "Configuración" =======
    def _build_config(self):
        left = tb.Frame(self.page_config)
        left.pack(side=LEFT, fill=Y, padx=(8,4), pady=8)
        right = tb.Frame(self.page_config)
        right.pack(side=RIGHT, fill=BOTH, expand=YES, padx=(4,8), pady=8)

        # Tema
        tb.Label(left, text="Tema", font="-size 11 -weight bold").pack(anchor="w")
        self.cmb_theme = tb.Combobox(left, values=sorted(tb.Style().theme_names()), width=22)
        self.cmb_theme.set(self.settings["theme"])
        self.cmb_theme.pack(anchor="w", pady=(0,10))
        tb.Button(left, text="Aplicar tema", bootstyle=INFO, command=self.apply_theme).pack(anchor="w", pady=4)

        tb.Separator(left).pack(fill=X, pady=8)
        tb.Label(left, text="Origen de JSON", font="-size 11 -weight bold").pack(anchor="w")
        
        # Asegurar que el valor del modo sea un entero
        modo_value = self.settings.get("modo", 1)
        if isinstance(modo_value, str):
            if '(' in modo_value and ')' in modo_value:
                match = re.search(r'\((\d+)\)', modo_value)
                if match:
                    modo_value = int(match.group(1))
                else:
                    modo_value = 1
            else:
                try:
                    modo_value = int(modo_value)
                except ValueError:
                    modo_value = 1
        
        self.cmb_modo = tb.Combobox(left, values=["Carpeta Local (1)", "SFTP-Davinci (2)"], width=22)
        self.cmb_modo.set("Carpeta Local (1)" if modo_value == 1 else "SFTP-Davinci (2)")
        self.cmb_modo.pack(anchor="w", pady=(0,10))

        tb.Separator(left).pack(fill=X, pady=8)
        tb.Label(left, text="Comparación de Tasa", font="-size 11 -weight bold").pack(anchor="w")
        self.chk_detalle = tb.Checkbutton(left, text="Mostrar detalle en evidencia", bootstyle=SUCCESS)
        if self.settings["MOSTRAR_DETALLE_TASA"]:
            self.chk_detalle.invoke()
        self.ent_tol = tb.Entry(left, width=10)
        self.ent_tol.insert(0, str(self.settings["TASA_TOLERANCIA"]))
        row_tol = tb.Frame(left); row_tol.pack(anchor="w", pady=4)
        tb.Label(row_tol, text="Tolerancia (fracción): ").pack(side=LEFT)
        self.ent_tol.pack(in_=row_tol, side=LEFT)

        tb.Separator(left).pack(fill=X, pady=8)
        tb.Button(left, text="Guardar preferencias", bootstyle=SECONDARY, command=self.save_prefs).pack(anchor="w", pady=6)

        # Rutas
        tb.Label(right, text="Rutas del Proyecto", font="-size 11 -weight bold").pack(anchor="w")
        self.ent_jsons  = tb.Entry(right); self.ent_jsons.insert(0, str(config.RUTA_JSONS))
        self.ent_nojson = tb.Entry(right); self.ent_nojson.insert(0, str(config.RUTA_NO_JSON))
        self.ent_result = tb.Entry(right); self.ent_result.insert(0, str(config.CARPETA_RESULTADOS_DAVINCI))
        self.ent_avista = tb.Entry(right); self.ent_avista.insert(0, str(config.CARPETA_BASES_AVISTA))

        self._labeled(right, "JSON Local", self.ent_jsons, True)
        self._labeled(right, "No JSON (aux)", self.ent_nojson, True)
        self._labeled(right, "Resultados Davinci (todas las salidas)", self.ent_result, True)
        self._labeled(right, "Carpeta Bases Avista", self.ent_avista, True)

        tb.Button(right, text="Abrir carpeta de resultados", bootstyle=LINK, command=self.open_results).pack(anchor="w", pady=(6,0))

    def _labeled(self, parent, label, widget, with_button=False):
        row = tb.Frame(parent); row.pack(fill=X, pady=6)
        tb.Label(row, text=label, width=28, anchor="w").pack(side=LEFT)
        widget.pack(in_=row, side=LEFT, fill=X, expand=YES)
        if with_button:
            b = tb.Button(row, text="Examinar…", bootstyle=SECONDARY,
                          command=lambda v=widget: self._browse_dir_widget(v))
            b.pack(side=LEFT, padx=6)

    # ======= pestaña "Logs" =======
    def _build_logs(self):
        top = tb.Frame(self.page_logs)
        top.pack(fill=X, padx=8, pady=(10,4))
        tb.Label(top, text="Consola", font="-size 12 -weight bold").pack(side=LEFT)
        tb.Button(top, text="Limpiar", bootstyle=SECONDARY, command=self.clear_logs).pack(side=RIGHT)
        self.txt_logs = tb.ScrolledText(self.page_logs, height=26)
        self.txt_logs.pack(fill=BOTH, expand=YES, padx=8, pady=8)

    # ---------- Helpers UI ----------
    def _browse_dir(self, var: tk.StringVar):
        p = filedialog.askdirectory(title="Seleccionar carpeta")
        if p: var.set(p)

    def _browse_dir_widget(self, entry: tb.Entry):
        p = filedialog.askdirectory(title="Seleccionar carpeta")
        if p: entry.delete(0, END) or entry.insert(0, p)

    def _on_theme_change(self, event=None):
        try:
            self.style.theme_use(self.theme_var.get())
        except Exception:
            pass

    def apply_theme(self):
        theme = self.cmb_theme.get()
        try:
            self.style.theme_use(theme)
            self.settings["theme"] = theme
            Messagebox.ok(f"Tema aplicado: {theme}", "Tema")
        except Exception as e:
            Messagebox.show_warning(str(e), "Error de tema")

    def save_prefs(self):
        values = {
            "theme": self.cmb_theme.get(),
            "modo": 1 if self.cmb_modo.get().startswith("Carpeta") else 2,
            "detalle_tasa": bool(self.chk_detalle.instate(["selected"])),
            "tol_tasa": self.ent_tol.get(),
            "ruta_jsons": self.ent_jsons.get(),
            "ruta_nojson": self.ent_nojson.get(),
            "ruta_resultados": self.ent_result.get(),
            "ruta_avista": self.ent_avista.get(),
        }
        _save_settings(values)
        Messagebox.ok("Preferencias guardadas.", "Listo")

    def _modo_config(self) -> int:
        return 1 if self.cmb_modo.get().startswith("Carpeta") else 2

    def _apply_runtime_config(self, jsons, nojson, resultados, avista):
        # toggles de tasa
        config.MOSTRAR_DETALLE_TASA = bool(self.chk_detalle.instate(["selected"]))
        try:
            config.TASA_TOLERANCIA = float(self.ent_tol.get())
        except Exception:
            pass
        # rutas
        config.RUTA_JSONS = jsons
        config.RUTA_NO_JSON = nojson
        base = Path(resultados)
        base.mkdir(parents=True, exist_ok=True)
        for attr in ("CARPETA_RESULTADOS_DAVINCI","CARPETA_EXCEL_CLON","CARPETA_EXCEL_REESTRUCTURADO",
                     "CARPETA_EXCEL_NORMALIZADO","CARPETA_EXCEL_FALLOS","CARPETA_SALIDA_COMPARACION",
                     "CARPETA_EXCEL_UNIFICADO"):
            setattr(config, attr, base)
        config.CARPETA_BASES_AVISTA = Path(avista)

    def append_log(self, s):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert(END, f"[{ts}] {s}\n")
        self.txt_logs.see(END)

    def clear_logs(self):
        self.txt_logs.delete("1.0", END)

    def _pump_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.append_log(msg)
        except queue.Empty:
            pass
        self.after(120, self._pump_logs)

    def open_results(self):
        path = Path(self.ent_result.get())
        try:
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:
                os.system(f"xdg-open '{path}'")
        except Exception as e:
            Messagebox.show_warning(str(e), "Error al abrir carpeta")

    def update_etapa_status(self, etapa, status, color="black"):
        """Actualiza el estado de una etapa específica"""
        if etapa in self.etapa_labels:
            self.etapa_labels[etapa].configure(text=status, foreground=color)

    # ---------- COMPLETO ----------
    def _set_full_busy(self, busy: bool):
        if busy:
            self.pb_full.start(12)
            self.btn_iniciar_full.configure(state="disabled")
            self.btn_parar_full.configure(state="normal")
            self.lbl_status_full.configure(text="Procesando…")
            self.running = True
            
            # Resetear todos los estados de etapa
            for etapa in self.etapas:
                self.update_etapa_status(etapa, "⏳ Pendiente", "gray")
        else:
            self.pb_full.stop()
            self.btn_iniciar_full.configure(state="normal")
            self.btn_parar_full.configure(state="disabled")
            self.lbl_status_full.configure(text="Listo.")
            self.running = False

    def _apply_full_paths(self):
        self._apply_runtime_config(
            self.var_jsons.get(),
            self.var_nojson.get(),
            self.var_result.get(),
            self.var_avista.get()
        )

    def run_all_full(self):
        if self.thread and self.thread.is_alive():
            Messagebox.show_warning("Ya hay una ejecución activa.", "Aviso")
            return
        self._apply_full_paths()
        modo = int(self.modo_full.get())
        self.stop_event.clear()
        self._set_full_busy(True)

        def job():
            try:
                etapas = [
                    ("Depurar", lambda: etapa_depurar(modo, self.append_log)),
                    ("Clonar", lambda: etapa_clonar(modo, self.append_log)),
                    ("Reestructurar", lambda: etapa_reestructurar(self.append_log)),
                    ("Comparar", lambda: etapa_comparar(self.append_log)),
                    ("Normalizar", lambda: etapa_normalizar(self.append_log)),
                    ("Consolidar", lambda: etapa_consolidar(self.append_log)),
                ]
                
                for nombre, funcion in etapas:
                    if self.stop_event.is_set():
                        self.append_log("⏹ Proceso cancelado por el usuario.")
                        break
                    
                    # Actualizar la etapa actual en la GUI
                    self.after(0, lambda n=nombre: self.update_etapa_status(n, "▶️ Ejecutando...", "blue"))
                    self.append_log(f"▶ {nombre}…")
                    ok = funcion()
                    
                    if not ok:
                        self.append_log(f"❌ Pipeline detenido en: {nombre}")
                        self.after(0, lambda n=nombre: self.update_etapa_status(n, "❌ Error", "red"))
                        break
                        
                    self.append_log(f"✅ {nombre} completado.")
                    self.after(0, lambda n=nombre: self.update_etapa_status(n, "✅ Completado", "green"))
                    
                else:
                    self.append_log("🎉 Proceso COMPLETO.")
                    self.after(0, lambda: Messagebox.ok("Proceso completado con éxito.", "Listo"))
                    
            except Exception as e:
                self.append_log(f"❗ Error: {e}")
            finally:
                self.after(0, lambda: self._set_full_busy(False))

        self.thread = threading.Thread(target=job, daemon=True)
        self.thread.start()

    # ---------- POR ETAPAS ----------
    def _apply_paths_from_config_tab(self):
        self._apply_runtime_config(
            self.ent_jsons.get(),
            self.ent_nojson.get(),
            self.ent_result.get(),
            self.ent_avista.get()
        )

    def _reset_steps_progress(self):
        self.steps_completed = 0
        self.pb_steps_total.configure(value=0)
        for name, _ in self.steps:
            self.step_badges[name].configure(text="IDLE", bootstyle=SECONDARY)
            self.step_spinners[name].stop()

    def _set_step(self, name, running=None, status=None, style=None):
        if running is not None:
            if running:
                self.step_spinners[name].start(10)
            else:
                self.step_spinners[name].stop()
        if status is not None:
            self.step_badges[name].configure(text=status, bootstyle=(style or SECONDARY))

    def _run_single(self, name, fn):
        if self.thread and self.thread.is_alive():
            Messagebox.show_warning("Ya hay una ejecución activa.", "Aviso")
            return
        self._apply_paths_from_config_tab()
        modo = 1 if self.cmb_modo.get().startswith("Carpeta") else 2
        self.stop_event.clear()
        self._set_step(name, running=True, status="RUNNING", style=INFO)

        def job():
            try:
                ok = fn(modo) if name == "Depurar" else fn()
                self._set_step(name, running=False, status=("OK" if ok else "ERROR"), style=(SUCCESS if ok else DANGER))
                self.steps_completed += 1
                self.pb_steps_total.configure(value=self.steps_completed)
            except Exception as e:
                self.append_log(f"❗ Error en {name}: {e}")
                self._set_step(name, running=False, status="ERROR", style=DANGER)

        self.thread = threading.Thread(target=job, daemon=True)
        self.thread.start()

    def run_all_steps(self):
        if self.thread and self.thread.is_alive():
            Messagebox.show_warning("Ya hay una ejecución activa.", "Aviso")
            return
        self._apply_paths_from_config_tab()
        modo = self._modo_config()
        self.stop_event.clear()
        self._reset_steps_progress()

        def job():
            try:
                steps = [
                    ("Depurar", lambda: etapa_depurar(modo, self.append_log)),
                    ("Clonar", etapa_clonar, True),
                    ("Reestructurar", etapa_reestructurar, False),
                    ("Comparar", etapa_comparar, False),
                    ("Normalizar", etapa_normalizar, False),
                    ("Consolidar", etapa_consolidar, False),
                ]
                for name, fn, *rest in steps:
                    self._set_step(name, running=True, status="RUNNING", style=INFO)
                    ok = fn(modo, self.append_log) if rest and rest[0] else fn(self.append_log)
                    self._set_step(name, running=False, status=("OK" if ok else "ERROR"), style=(SUCCESS if ok else DANGER))
                    self.steps_completed += 1
                    self.pb_steps_total.configure(value=self.steps_completed)
                    if not ok:
                        self.append_log(f"❌ Pipeline detenido en: {name}")
                        break
                else:
                    self.append_log("🎉 Proceso COMPLETO (por etapas).")
                    self.after(0, lambda: Messagebox.ok("Proceso por etapas completado.", "Listo"))
            except Exception as e:
                self.append_log(f"❗ Error: {e}")

        self.thread = threading.Thread(target=job, daemon=True)
        self.thread.start()

    def run_depurar_single(self):      self._run_single("Depurar", lambda modo: etapa_depurar(modo, self.append_log))
    def run_clonar_single(self):       self._run_single("Clonar",  lambda _=None: etapa_clonar(self._modo_config(), self.append_log))
    def run_reestructurar_single(self):self._run_single("Reestructurar", lambda _=None: etapa_reestructurar(self.append_log))
    def run_comparar_single(self):     self._run_single("Comparar", lambda _=None: etapa_comparar(self.append_log))
    def run_normalizar_single(self):   self._run_single("Normalizar", lambda _=None: etapa_normalizar(self.append_log))
    def run_consolidar_single(self):   self._run_single("Consolidar", lambda _=None: etapa_consolidar(self.append_log))

    def cancel_run(self):
        self.stop_event.set()
        self.append_log("Cancelando ejecución actual…")
        self.running = False

    # ---------- misc ----------
    def place_window_center(self):
        self.update_idletasks()
        w = self.winfo_width(); h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

# ---- Arranque ----
if __name__ == "__main__":
    app = App()
    app.place_window_center()
    app.mainloop()