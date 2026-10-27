import json
import os
import sys
import subprocess
import urllib.request
import threading
import ctypes
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- REPORTLAB PARA GENERACIÓN DE PDF ---
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- TRUCO PARA MOSTRAR ICONO PERSONALIZADO EN LA BARRA DE TAREAS DE WINDOWS ---
try:
    myappid = 'sokychan.energycompare.gas.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# --- CONFIGURACIÓN DE VERSIÓN Y RUTAS REMOTAS ---
VERSION_ACTUAL = "1.0.0"
URL_VERSION_REMOTA = "https://raw.githubusercontent.com/Sokychan/ComparadorTarifasGas/main/version.json"
URL_TARIFAS_RAW = "https://raw.githubusercontent.com/Sokychan/ComparadorTarifasGas/main/tarifas_gas_mercado.json"

# --- PALETA DE COLORES MODERNA ---
COLOR_BG_MAIN = "#0F172A"       
COLOR_CARD_BG = "#1E293B"       
COLOR_CARD_BORDER = "#334155"   
COLOR_ACCENT_BLUE = "#1F6AA5"   
COLOR_ACCENT_GREEN = "#2FA572"  
COLOR_TEXT_MAIN = "#F8FAFC"     
COLOR_TEXT_MUTED = "#94A3B8"    
COLOR_ACCENT_GOLD = "#F59E0B"
COLOR_ACCENT_ORANGE = "#EA580C"

DATA_FILE = "tarifas_gas_mercado.json"

# --- COSTES REGULADOS NORMADOS DEL GAS NATURAL ---
IMPUESTO_HIDROCARBUROS_KWH = 0.00234   # €/kWh Impuesto especial sobre hidrocarburos
ALQUILER_CONTADOR_DIARIO = 0.058       # €/día equipo de medida gas doméstico
IVA_RATE = 0.21                        # 21% IVA

# --- DATOS DE SEMILLA (Fallback inicial) ---
DATOS_SEMILLA_GAS = [
    {"Comercializadora": "Curenergía (TUR)", "Nombre_Tarifa": "TUR.1 / TUR.2", "Termino_Fijo_Dia": 0.1570, "Termino_Variable_kWh": 0.0512},
    {"Comercializadora": "Endesa", "Nombre_Tarifa": "Conecta Gas", "Termino_Fijo_Dia": 0.1600, "Termino_Variable_kWh": 0.0570},
    {"Comercializadora": "Endesa", "Nombre_Tarifa": "One Gas", "Termino_Fijo_Dia": 0.1650, "Termino_Variable_kWh": 0.0590},
    {"Comercializadora": "Octopus Energy", "Nombre_Tarifa": "Octopus Gas", "Termino_Fijo_Dia": 0.1620, "Termino_Variable_kWh": 0.0565},
    {"Comercializadora": "TotalEnergies", "Nombre_Tarifa": "A Tu Aire Gas", "Termino_Fijo_Dia": 0.1700, "Termino_Variable_kWh": 0.0610},
    {"Comercializadora": "TotalEnergies", "Nombre_Tarifa": "4 Estaciones Gas", "Termino_Fijo_Dia": 0.1680, "Termino_Variable_kWh": 0.0585},
    {"Comercializadora": "Iberdrola", "Nombre_Tarifa": "Plan Gas Hogar", "Termino_Fijo_Dia": 0.1750, "Termino_Variable_kWh": 0.0620}
]

def inicializar_json_si_no_existe():
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DATOS_SEMILLA_GAS, f, ensure_ascii=False, indent=2)

# --- FUNCIONES DE ACTUALIZACIÓN AUTOMÁTICA DEL EJECUTABLE ---
def verificar_actualizacion_app(parent_window):
    """Lanza la comprobación de versión en un hilo secundario."""
    threading.Thread(target=_ejecutar_comprobacion_app, args=(parent_window,), daemon=True).start()

def _ejecutar_comprobacion_app(parent_window):
    try:
        req = urllib.request.Request(URL_VERSION_REMOTA, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

        version_remota = data.get("version", VERSION_ACTUAL)
        download_url = data.get("download_url", "")
        changelog = data.get("changelog", "Mejoras generales y actualización de precios de gas.")

        if version_remota > VERSION_ACTUAL:
            parent_window.after(0, lambda: _notificar_y_descargar(parent_window, version_remota, download_url, changelog))
    except Exception as e:
        print(f"No se pudo consultar el servidor de actualizaciones de gas: {e}")

def _notificar_y_descargar(parent_window, nueva_version, download_url, changelog):
    respuesta = messagebox.askyesno(
        "Nueva actualización disponible 🔥",
        f"Se ha encontrado la versión v{nueva_version} de EnergyCompare Gas.\n\n"
        f"Novedades:\n{changelog}\n\n"
        f"¿Deseas descargar la actualización automáticamente ahora?"
    )

    if respuesta and download_url:
        _ejecutar_proceso_actualizacion(download_url)

def _ejecutar_proceso_actualizacion(download_url):
    try:
        exe_actual = sys.executable
        directorio_actual = os.path.dirname(exe_actual)
        nuevo_exe = os.path.join(directorio_actual, "EnergyCompareGas_nueva_version.exe")
        bat_updater = os.path.join(directorio_actual, "updater_gas.bat")

        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(nuevo_exe, 'wb') as out_file:
            out_file.write(response.read())

        contenido_bat = f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{nuevo_exe}" "{exe_actual}"
start "" "{exe_actual}"
del "%~f0"
"""
        with open(bat_updater, "w") as f:
            f.write(contenido_bat)

        subprocess.Popen([bat_updater], shell=True)
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Error al actualizar", f"Ocurrió un error al instalar la actualización:\n{e}")

ctk.set_appearance_mode("Dark")

class AppProGasDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EnergyCompare Gas Pro")
        self.geometry("1180x820")
        self.minsize(1000, 700)
        self.configure(fg_color=COLOR_BG_MAIN)

        if os.path.exists("icono.ico"):
            try:
                self.iconbitmap("icono.ico")
            except Exception:
                pass

        self.mostrar_tarifa_actual = False
        self.ultimos_resultados = []
        self.ultimo_consumo_kwh = 0.0
        inicializar_json_si_no_existe()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.crear_sidebar()
        self.crear_area_principal()
        
        # Sincronización asíncrona de las tarifas desde GitHub Actions
        self.sincronizar_tarifas_github()

        # Comprobar si existe un ejecutable más nuevo en GitHub
        verificar_actualizacion_app(self)

    def sincronizar_tarifas_github(self):
        """Descarga la versión más reciente del JSON de tarifas desde GitHub Raw."""
        def _tarea_descarga():
            try:
                req = urllib.request.Request(URL_TARIFAS_RAW, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    datos = json.loads(response.read().decode('utf-8'))

                if datos:
                    with open(DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(datos, f, ensure_ascii=False, indent=2)

                    self.lbl_status_dot.configure(text_color=COLOR_ACCENT_GREEN)
                    self.lbl_status.configure(text="Tarifas sincronizadas desde GitHub")
            except Exception:
                self.lbl_status_dot.configure(text_color=COLOR_ACCENT_GOLD)
                self.lbl_status.configure(text="Modo offline (Tarifas locales)")

        threading.Thread(target=_tarea_descarga, daemon=True).start()

    def crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=320, corner_radius=0, 
            fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # 1. Cabecera
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=15, pady=(12, 8), sticky="w")
        
        ctk.CTkLabel(logo_frame, text="🔥", font=ctk.CTkFont(size=20)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            logo_frame, text="EnergyCompare Gas", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), 
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_CARD_BORDER).grid(row=1, column=0, padx=15, pady=(0, 6), sticky="ew")

        # 2. CONTENEDOR CON SCROLL
        self.scroll_form = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=COLOR_CARD_BORDER,
            scrollbar_button_hover_color=COLOR_ACCENT_BLUE
        )
        self.scroll_form.grid(row=2, column=0, padx=5, pady=0, sticky="nsew")
        self.scroll_form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.scroll_form, text="DATOS DE FACTURA DE GAS", 
            font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=10, pady=(2, 4))

        # Inputs
        self.frame_inputs = ctk.CTkFrame(self.scroll_form, fg_color="transparent")
        self.frame_inputs.pack(fill="x", padx=10)

        self.crear_label_input(self.frame_inputs, "Días de Facturación")
        self.entry_dias_factura = self.crear_entry_estilizado(self.frame_inputs, "Ej: 30 o 60")

        self.crear_label_input(self.frame_inputs, "Consumo Total de Gas (kWh)")
        self.entry_energia_kwh = self.crear_entry_estilizado(self.frame_inputs, "Ej: 450")

        # Desplegable Tarifa Actual
        self.btn_toggle_actual = ctk.CTkButton(
            self.scroll_form, 
            text="▶  Comparar con mi Tarifa Actual", 
            fg_color="transparent", 
            hover_color=COLOR_CARD_BORDER,
            anchor="w", height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            command=self.toggle_tarifa_actual
        )
        self.btn_toggle_actual.pack(fill="x", padx=5, pady=(12, 4))

        self.frame_tarifa_actual = ctk.CTkFrame(
            self.scroll_form, fg_color=COLOR_BG_MAIN, 
            border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=6
        )

        self.crear_label_input(self.frame_tarifa_actual, "Término Fijo (€/mes)", pad_x=10)
        self.entry_precio_fijo_mes = self.crear_entry_estilizado(self.frame_tarifa_actual, "Ej: 5.25", pad_x=10)

        self.crear_label_input(self.frame_tarifa_actual, "Término Variable (€/kWh)", pad_x=10)
        self.entry_precio_variable_kwh = self.crear_entry_estilizado(self.frame_tarifa_actual, "Ej: 0.0610", pad_x=10)

        # 3. BOTÓN DE CÁLCULO PRINCIPAL
        btn_calcular = ctk.CTkButton(
            self.sidebar, text="Calcular Ahorro Gas 🚀", 
            fg_color=COLOR_ACCENT_ORANGE, hover_color="#C2410C",
            height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=6,
            command=self.calcular_ahorro
        )
        btn_calcular.grid(row=3, column=0, padx=15, pady=(8, 6), sticky="ew")

        # Footer Status
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.grid(row=4, column=0, padx=15, pady=(0, 8), sticky="s")
        
        self.lbl_status_dot = ctk.CTkLabel(status_frame, text="●", text_color=COLOR_ACCENT_GREEN, font=ctk.CTkFont(size=10))
        self.lbl_status_dot.pack(side="left", padx=(0, 4))
        
        self.lbl_status = ctk.CTkLabel(status_frame, text="Conectando...", font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED)
        self.lbl_status.pack(side="left")

    def toggle_tarifa_actual(self):
        self.mostrar_tarifa_actual = not self.mostrar_tarifa_actual
        if self.mostrar_tarifa_actual:
            self.btn_toggle_actual.configure(text="▼  Comparar con mi Tarifa Actual")
            self.frame_tarifa_actual.pack(fill="x", padx=5, pady=(0, 6))
        else:
            self.btn_toggle_actual.configure(text="▶  Comparar con mi Tarifa Actual")
            self.frame_tarifa_actual.pack_forget()

    def crear_area_principal(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.frame_kpis = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frame_kpis.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.frame_kpis.grid_columnconfigure((0, 1), weight=1, uniform="kpi")

        self.card_mejor = self.crear_card_kpi(self.frame_kpis, 0, "MEJOR TARIFA DE GAS ENCONTRADA", "-- €", "Rellena los datos y calcula", color_val=COLOR_ACCENT_GREEN)
        self.card_ahorro = self.crear_card_kpi(self.frame_kpis, 1, "AHORRO ESTIMADO", "-- €/periodo", "Ingresa tu tarifa actual", color_val=COLOR_ACCENT_BLUE)

        self.frame_resultados = ctk.CTkFrame(
            self.main_area, corner_radius=10, 
            fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1
        )
        self.frame_resultados.grid(row=1, column=0, sticky="nsew")

        header_frame = ctk.CTkFrame(self.frame_resultados, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(header_frame, text="Ranking de Comercializadoras de Gas", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left")

        self.scroll_list = ctk.CTkScrollableFrame(self.frame_resultados, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def crear_card_kpi(self, parent, col, titulo, valor, subtitulo, color_val=COLOR_TEXT_MAIN):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1)
        card.grid(row=0, column=col, padx=5, sticky="ew")

        lbl_tit = ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_tit.pack(anchor="w", padx=14, pady=(10, 2))
        
        lbl_val = ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=20, weight="bold"), text_color=color_val)
        lbl_val.pack(anchor="w", padx=14, pady=0)
        
        lbl_sub = ctk.CTkLabel(card, text=subtitulo, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", padx=14, pady=(2, 10))
        return {"card": card, "val": lbl_val, "sub": lbl_sub}

    def crear_label_input(self, parent, texto, pad_x=0):
        lbl = ctk.CTkLabel(
            parent, text=texto, 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#E2E8F0"
        )
        lbl.pack(anchor="w", pady=(3, 1), padx=pad_x)
        return lbl

    def crear_entry_estilizado(self, parent, placeholder, pad_x=0):
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            fg_color=COLOR_BG_MAIN, border_color=COLOR_CARD_BORDER, border_width=1,
            text_color=COLOR_TEXT_MAIN, placeholder_text_color="#64748B",
            height=28, corner_radius=5, font=ctk.CTkFont(size=11)
        )
        entry.pack(fill="x", padx=pad_x, pady=(0, 2))
        return entry

    # --- MOTOR DE CÁLCULO DE GAS ---
    def calcular_ahorro(self):
        try:
            dias_raw = self.entry_dias_factura.get().strip()
            kwh_raw = self.entry_energia_kwh.get().strip()

            if not dias_raw or not kwh_raw:
                messagebox.showwarning("Campos obligatorios", "Por favor, introduce los 'Días de Facturación' y el 'Consumo Total (kWh)'.")
                return

            dias = int(dias_raw)
            consumo_kwh = float(kwh_raw)

            if dias <= 0 or consumo_kwh <= 0:
                messagebox.showwarning("Atención", "Los días y el consumo deben ser mayores que 0.")
                return

            if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
                inicializar_json_si_no_existe()

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                tarifas = json.load(f)

            resultados = []
            for t in tarifas:
                tf_dia = t.get("Termino_Fijo_Dia", 0.16)
                tv_kwh = t.get("Termino_Variable_kWh", 0.06)

                coste_tf_base = tf_dia * dias
                coste_tv_base = consumo_kwh * tv_kwh
                coste_hidrocarburos_base = consumo_kwh * IMPUESTO_HIDROCARBUROS_KWH
                coste_alquiler_base = dias * ALQUILER_CONTADOR_DIARIO

                subtotal_base = coste_tf_base + coste_tv_base + coste_hidrocarburos_base + coste_alquiler_base
                coste_total = subtotal_base * (1 + IVA_RATE)

                resultados.append({
                    "Comercializadora": t.get("Comercializadora", "Desconocida"),
                    "Nombre_Tarifa": t.get("Nombre_Tarifa", "Tarifa Gas"),
                    "Termino_Fijo_Dia": tf_dia,
                    "Termino_Variable_kWh": tv_kwh,
                    "Coste_Término_Fijo": round(coste_tf_base * (1 + IVA_RATE), 2),
                    "Coste_Término_Variable": round(coste_tv_base * (1 + IVA_RATE), 2),
                    "Coste_Total": round(coste_total, 2),
                    "es_actual": False
                })

            # --- INCLUSIÓN DE TU TARIFA ACTUAL DE GAS EN EL RANKING ---
            if self.mostrar_tarifa_actual:
                tf_mes_s = self.entry_precio_fijo_mes.get().strip()
                tv_kwh_s = self.entry_precio_variable_kwh.get().strip()

                if tf_mes_s and tv_kwh_s:
                    tf_mes_usr = float(tf_mes_s)
                    tv_kwh_usr = float(tv_kwh_s)
                    tf_dia_usr = (tf_mes_usr * 12) / 365.0

                    coste_tf_usr = tf_dia_usr * dias
                    coste_tv_usr = consumo_kwh * tv_kwh_usr
                    coste_hidrocarburos_usr = consumo_kwh * IMPUESTO_HIDROCARBUROS_KWH
                    coste_alquiler_usr = dias * ALQUILER_CONTADOR_DIARIO

                    subtotal_usr = coste_tf_usr + coste_tv_usr + coste_hidrocarburos_usr + coste_alquiler_usr
                    coste_usr_total = subtotal_usr * (1 + IVA_RATE)

                    resultados.append({
                        "Comercializadora": "Tu Tarifa Actual",
                        "Nombre_Tarifa": "Configurada",
                        "Termino_Fijo_Dia": tf_dia_usr,
                        "Termino_Variable_kWh": tv_kwh_usr,
                        "Coste_Término_Fijo": round(coste_tf_usr * (1 + IVA_RATE), 2),
                        "Coste_Término_Variable": round(coste_tv_usr * (1 + IVA_RATE), 2),
                        "Coste_Total": round(coste_usr_total, 2),
                        "es_actual": True
                    })

            resultados = sorted(resultados, key=lambda x: x["Coste_Total"])
            self.ultimos_resultados = resultados
            self.ultimo_consumo_kwh = consumo_kwh

            self.actualizar_interfaz_resultados(resultados, dias)

        except ValueError:
            messagebox.showerror("Error", "Introduce únicamente valores numéricos en todos los campos.")
        except Exception as e:
            messagebox.showerror("Error", f"Detalle técnico del error: {e}")

    def actualizar_interfaz_resultados(self, resultados, dias=30):
        top = resultados[0]
        self.card_mejor["val"].configure(text=f"{top['Coste_Total']:.2f} € / {dias}d")
        self.card_mejor["sub"].configure(text=f"{top['Comercializadora']} ({top['Nombre_Tarifa']})")

        tarifa_usr_item = next((x for x in resultados if x.get("es_actual")), None)

        if tarifa_usr_item:
            coste_actual = tarifa_usr_item["Coste_Total"]
            ahorro = coste_actual - top["Coste_Total"]
            if top.get("es_actual"):
                self.card_ahorro["val"].configure(text="0.00 €", text_color=COLOR_ACCENT_GREEN)
                self.card_ahorro["sub"].configure(text=f"¡Tu tarifa actual ({coste_actual:.2f} €) ya es la más óptima!")
            elif ahorro > 0:
                pct = (ahorro / coste_actual) * 100
                self.card_ahorro["val"].configure(text=f"{ahorro:.2f} € ahorro", text_color=COLOR_ACCENT_GREEN)
                self.card_ahorro["sub"].configure(text=f"Ahorras un {pct:.1f}% respecto a tu tarifa ({coste_actual:.2f} €)")
            else:
                self.card_ahorro["val"].configure(text="0.00 €", text_color=COLOR_TEXT_MAIN)
                self.card_ahorro["sub"].configure(text=f"Tu tarifa actual ({coste_actual:.2f} €) es la mejor opción.")
        else:
            diff = resultados[-1]["Coste_Total"] - top["Coste_Total"]
            self.card_ahorro["val"].configure(text=f"Hasta {diff:.2f} € dif.", text_color=COLOR_ACCENT_BLUE)
            self.card_ahorro["sub"].configure(text="Diferencia entre la opción más barata y más cara")

        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        for rank, res in enumerate(resultados, start=1):
            self.agregar_fila_resultado(rank, res, es_mejor=(rank == 1))

    def agregar_fila_resultado(self, ranking, res, es_mejor=False):
        es_actual = res.get("es_actual", False)

        if es_actual and es_mejor:
            border_color = COLOR_ACCENT_GREEN
            bg_color = "#13231B"
        elif es_actual:
            border_color = COLOR_ACCENT_BLUE
            bg_color = "#1E293B"
        elif es_mejor:
            border_color = COLOR_ACCENT_GREEN
            bg_color = "#13231B"
        else:
            border_color = COLOR_CARD_BORDER
            bg_color = COLOR_BG_MAIN

        row_frame = ctk.CTkFrame(
            self.scroll_list, corner_radius=10, 
            fg_color=bg_color, border_color=border_color, border_width=1
        )
        row_frame.pack(fill="x", pady=4, padx=2)

        rank_color = COLOR_ACCENT_GOLD if ranking == 1 else COLOR_TEXT_MUTED
        lbl_rank = ctk.CTkLabel(row_frame, text=f"#{ranking}", font=ctk.CTkFont(size=14, weight="bold"), text_color=rank_color, width=40)
        lbl_rank.pack(side="left", padx=(10, 0))

        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        title_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_frame.pack(anchor="w")

        nombre_completo = f"{res['Comercializadora']} - {res['Nombre_Tarifa']}"
        ctk.CTkLabel(title_frame, text=nombre_completo, font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left")

        if es_actual:
            badge_usr = ctk.CTkFrame(title_frame, fg_color="#1E3A8A", corner_radius=4)
            badge_usr.pack(side="left", padx=6)
            ctk.CTkLabel(badge_usr, text=" TU TARIFA ACTUAL ", font=ctk.CTkFont(size=9, weight="bold"), text_color="#60A5FA").pack(padx=4, pady=1)

        if es_mejor:
            badge_top = ctk.CTkFrame(title_frame, fg_color="#064E3B", corner_radius=4)
            badge_top.pack(side="left", padx=4)
            ctk.CTkLabel(badge_top, text=" MEJOR OPCIÓN ", font=ctk.CTkFont(size=9, weight="bold"), text_color=COLOR_ACCENT_GREEN).pack(padx=4, pady=1)

        txt_desglose = f"Término Fijo: {res['Coste_Término_Fijo']:.2f} €   |   Consumo Gas: {res['Coste_Término_Variable']:.2f} €"
        ctk.CTkLabel(info_frame, text=txt_desglose, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        precio_color = COLOR_ACCENT_GREEN if es_mejor else COLOR_TEXT_MAIN
        ctk.CTkLabel(row_frame, text=f"{res['Coste_Total']:.2f} €", font=ctk.CTkFont(size=16, weight="bold"), text_color=precio_color).pack(side="left", padx=15)

        btn_factura = ctk.CTkButton(
            row_frame, text="Generar PDF", width=95, height=30, 
            fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_BORDER,
            border_color=COLOR_CARD_BORDER, border_width=1,
            text_color=COLOR_TEXT_MAIN, corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda r=res: self.generar_pdf_tarifa_gas(r)
        )
        btn_factura.pack(side="right", padx=12, pady=8)

    # --- GENERACIÓN DEL PDF DE FACTURA DE GAS ---
    def generar_pdf_tarifa_gas(self, tarifa_data):
        try:
            filename_default = f"Factura_Gas_{tarifa_data['Comercializadora']}_{tarifa_data['Nombre_Tarifa']}".replace(" ", "_") + ".pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=filename_default,
                filetypes=[("Archivos PDF", "*.pdf")]
            )
            if not filepath:
                return

            dias = int(self.entry_dias_factura.get().strip() or 30)
            consumo_kwh = self.ultimo_consumo_kwh

            doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()

            style_title = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=13, textColor=colors.white, leading=16)
            style_header = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#333333"))
            style_header_right = ParagraphStyle('HeaderRightStyle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#333333"), alignment=2)

            style_bold = ParagraphStyle('BoldStyle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#111111"), leading=13)
            style_normal = ParagraphStyle('NormalStyle', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=12)
            style_normal_right = ParagraphStyle('NormalRightStyle', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#111111"), leading=12, alignment=2)
            style_total_label = ParagraphStyle('TotalLabel', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#000000"))
            style_total_val = ParagraphStyle('TotalVal', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#000000"), alignment=2)

            elements = []

            # Banner de Encabezado
            title_text = f"Detalle Factura Gas Natural - {tarifa_data['Comercializadora']} ({tarifa_data['Nombre_Tarifa']})"
            title_p = Paragraph(title_text, style_title)
            banner_table = Table([[title_p]], colWidths=[522])
            banner_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#D97706")),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(banner_table)
            elements.append(Spacer(1, 10))

            table_data = [
                [Paragraph("Concepto", style_header), Paragraph("", style_header), Paragraph("Importe €", style_header_right)]
            ]

            subtotal = 0.0

            # 1. Término Fijo de Gas
            tf_dia = tarifa_data.get("Termino_Fijo_Dia", 0.0)
            coste_tf = tf_dia * dias
            subtotal += coste_tf
            table_data.append([
                Paragraph("Término fijo", style_bold),
                Paragraph(f"{dias} días x {tf_dia:.6f} €/día", style_normal),
                Paragraph(f"{coste_tf:.2f} €", style_normal_right)
            ])

            # 2. Término Variable (Consumo Gas)
            tv_kwh = tarifa_data.get("Termino_Variable_kWh", 0.0)
            coste_tv = consumo_kwh * tv_kwh
            subtotal += coste_tv
            table_data.append([
                Paragraph("Término variable (Consumo)", style_bold),
                Paragraph(f"{consumo_kwh:.2f} kWh x {tv_kwh:.6f} €/kWh", style_normal),
                Paragraph(f"{coste_tv:.2f} €", style_normal_right)
            ])

            # 3. Impuesto Especial sobre Hidrocarburos
            coste_hidrocarburos = consumo_kwh * IMPUESTO_HIDROCARBUROS_KWH
            subtotal += coste_hidrocarburos
            table_data.append([
                Paragraph("Impuesto sobre Hidrocarburos", style_bold),
                Paragraph(f"{consumo_kwh:.2f} kWh x {IMPUESTO_HIDROCARBUROS_KWH:.6f} €/kWh", style_normal),
                Paragraph(f"{coste_hidrocarburos:.2f} €", style_normal_right)
            ])

            # 4. Alquiler contador de gas
            coste_alquiler = dias * ALQUILER_CONTADOR_DIARIO
            subtotal += coste_alquiler
            table_data.append([
                Paragraph("Alquiler equipo de medida (Gas)", style_bold),
                Paragraph(f"{dias} días x {ALQUILER_CONTADOR_DIARIO:.6f} €/día", style_normal),
                Paragraph(f"{coste_alquiler:.2f} €", style_normal_right)
            ])

            # Suma e Impuestos (Base e IVA)
            table_data.append([
                Paragraph("Base imponible", style_bold),
                Paragraph("", style_normal),
                Paragraph(f"{subtotal:.2f} €", style_normal_right)
            ])

            iva = subtotal * IVA_RATE
            table_data.append([
                Paragraph(f"IVA ({int(IVA_RATE*100)}%)", style_bold),
                Paragraph("", style_normal),
                Paragraph(f"{iva:.2f} €", style_normal_right)
            ])

            total = subtotal + iva
            table_data.append([
                Paragraph("TOTAL FACTURA GAS", style_total_label),
                Paragraph("", style_normal),
                Paragraph(f"{total:.2f} €", style_total_val)
            ])

            main_table = Table(table_data, colWidths=[160, 262, 100])
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FEF3C7")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor("#D97706")),
                ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor("#111111")),
            ]))

            elements.append(main_table)
            doc.build(elements)

        except Exception as e:
            messagebox.showerror("Error al generar PDF", f"Ocurrió un detalle técnico: {e}")

if __name__ == "__main__":
    app = AppProGasDashboard()
    app.mainloop()