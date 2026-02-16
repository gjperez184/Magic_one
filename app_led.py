import streamlit as st
import subprocess
import sys

# ==========================================
# 🚑 BLOQUE DE AUTO-REPARACIÓN (EMERGENCIA)
# ==========================================
# Esto fuerza la instalación si el servidor ignoró el requirements.txt
try:
    import xlsxwriter
except ImportError:
    # Si no lo encuentra, lo instalamos a la fuerza usando pip desde adentro
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xlsxwriter"])
    import xlsxwriter

# ==========================================
# INICIO DEL PROGRAMA NORMAL
# ==========================================
import math
import pandas as pd
import io

# ==========================================
# 0. FUNCIÓN DE LOCALIZACIÓN Y EXPORTACIÓN
# ==========================================
def formato_latam(valor, decimales=2):
    if isinstance(valor, (int, float)):
        if decimales == 0:
            estandar = f"{int(valor):,}"
            return estandar.replace(',', '.')
        estandar = f"{valor:,.{decimales}f}"
        return estandar.replace(',', 'X').replace('.', ',').replace('X', '.')
    return valor

def generar_texto_reporte(req_w, req_h, res_hw, calc_proc, calc_pwr, calc_rig):
    texto = "=" * 70 + "\n"
    texto += "          REPORTE DE INGENIERIA - SISTEMA LEDSCREENCALC\n"
    texto += "=" * 70 + "\n\n"
    texto += f"[A] DISENO DE HARDWARE (MEDIDA SOLICITADA: {formato_latam(req_w/1000, 2)}m x {formato_latam(req_h/1000, 2)}m)\n\n"
    texto += "  --- OPCION 1: AJUSTE IDEAL ---\n"
    for k, v in res_hw["Opcion 1 (Ideal)"]["formatted"].items(): texto += f"    > {k}: {v}\n"
    texto += "\n  --- OPCION 2: AJUSTE INFERIOR ---\n"
    for k, v in res_hw["Opcion 2 (Inferior)"]["formatted"].items(): texto += f"    > {k}: {v}\n"
    texto += "\n  --- OPCION 3: AJUSTE SUPERIOR ---\n"
    for k, v in res_hw["Opcion 3 (Superior)"]["formatted"].items(): texto += f"    > {k}: {v}\n"
    texto += "\n" + "-" * 50 + "\n[B] CRITERIOS DE VISUALIZACION\n"
    for k, v in res_hw["Visualizacion"].items(): texto += f"  > {k}: {v}\n"
    texto += "\n" + "-" * 50 + "\n[C] INGENIERIA DE PROCESAMIENTO Y DATA\n"
    for k, v in calc_proc.calcular_procesamiento().items(): texto += f"  > {k}: {v}\n"
    texto += "\n" + "-" * 50 + "\n[D] HARDWARE DEL PROCESADOR (TOPOLOGIA)\n"
    for k, v in calc_proc.calcular_hardware_procesador().items(): texto += f"  > {k}: {v}\n"
    texto += "\n" + "-" * 50 + "\n[E] INGENIERIA ELECTRICA Y CLIMATIZACION (Opcion 1)\n"
    for k, v in calc_pwr.calcular_energia_y_clima().items(): texto += f"  > {k}: {v}\n"
    texto += "\n" + "-" * 50 + "\n[F] INGENIERIA ESTRUCTURAL E IZAJE (Opcion 1)\n"
    for k, v in calc_rig.calcular_izaje().items(): texto += f"  > {k}: {v}\n"
    texto += "\n" + "=" * 70 + "\nFIN DEL REPORTE TECNICO.\n" + "=" * 70 + "\n"
    return texto

def generar_excel_reporte(req_w, req_h, res_hw, calc_proc, calc_pwr, calc_rig):
    data = []
    
    # Encabezado
    data.append(["MEDIDA SOLICITADA", f"{formato_latam(req_w/1000, 2)}m (Ancho) x {formato_latam(req_h/1000, 2)}m (Alto)"])
    data.append(["", ""])
    
    # Opciones de Hardware
    opciones = [("OPCIÓN 1: AJUSTE IDEAL", "Opcion 1 (Ideal)"), 
                ("OPCIÓN 2: AJUSTE INFERIOR", "Opcion 2 (Inferior)"), 
                ("OPCIÓN 3: AJUSTE SUPERIOR", "Opcion 3 (Superior)")]
                
    for titulo, clave in opciones:
        data.append([f"--- {titulo} ---", ""])
        for k, v in res_hw[clave]["formatted"].items():
            data.append([k, v])
        data.append(["", ""])

    # Visualización
    data.append(["--- CRITERIOS DE VISUALIZACIÓN ---", ""])
    for k, v in res_hw["Visualizacion"].items(): data.append([k, v])
    data.append(["", ""])

    # Procesamiento y Data
    data.append(["--- INGENIERÍA DE PROCESAMIENTO Y DATA ---", ""])
    for k, v in calc_proc.calcular_procesamiento().items(): data.append([k, v])
    data.append(["", ""])

    # Hardware del Procesador
    data.append(["--- HARDWARE DEL PROCESADOR ---", ""])
    for k, v in calc_proc.calcular_hardware_procesador().items(): data.append([k, v])
    data.append(["", ""])

    # Energía
    data.append(["--- INGENIERÍA ELÉCTRICA Y CLIMATIZACIÓN ---", ""])
    for k, v in calc_pwr.calcular_energia_y_clima().items(): data.append([k, v])
    data.append(["", ""])

    # Rigging
    data.append(["--- INGENIERÍA ESTRUCTURAL E IZAJE ---", ""])
    for k, v in calc_rig.calcular_izaje().items(): data.append([k, v])

    # Convertir a DataFrame de Pandas y usar el motor XlsxWriter
    df = pd.DataFrame(data, columns=["Parámetro", "Especificación Técnica"])
    output = io.BytesIO()
    
    # Motor XlsxWriter explícito
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Ingeniería LED')
        worksheet = writer.sheets['Reporte Ingeniería LED']
        worksheet.set_column('A:A', 40)
        worksheet.set_column('B:B', 80)
        
    return output.getvalue()

# ==========================================
# 1. MÓDULOS DE CLASES (Core Lógico)
# ==========================================
class LedScreenProc:
    def __init__(self, uso, total_px, total_gabinetes, input_res, puerto, calidad, fps_video=60, 
                 distancia_cable_m=50, refresh_rate_hz=3840, shutter_speed_str="1/60",
                 res_w=0, res_h=0, fis_w_mm=0, fis_h_mm=0, num_entradas=1):
        self.uso = uso
        self.total_px = total_px
        self.total_gabinetes = total_gabinetes
        self.input_res = input_res
        self.puerto = puerto
        self.calidad = calidad
        self.fps = fps_video
        self.distancia_cable_m = distancia_cable_m
        self.refresh_rate_hz = refresh_rate_hz
        self.shutter_speed_str = shutter_speed_str
        self.res_w = res_w
        self.res_h = res_h
        self.fis_w_mm = int(fis_w_mm)
        self.fis_h_mm = int(fis_h_mm)
        self.num_entradas = num_entradas

    def _parsear_shutter(self):
        try:
            if "/" in self.shutter_speed_str:
                num, den = self.shutter_speed_str.split("/")
                return float(num) / float(den)
            else:
                return 1.0 / float(self.shutter_speed_str)
        except:
            return 1.0 / 60.0 

    def _calcular_ratio(self, w, h):
        if w == 0 or h == 0: return "N/A"
        divisor = math.gcd(w, h)
        return f"{w//divisor}:{h//divisor}"

    def calcular_procesamiento(self):
        capacidad_base_px = 650000 
        if "10-bit" in self.calidad or "12-bit" in self.calidad or "HDR" in self.calidad:
            capacidad_base_px = capacidad_base_px // 2 
        if self.fps > 60:
            capacidad_base_px = int(capacidad_base_px * (60.0 / self.fps))

        self.puertos_rj45 = max(1, math.ceil(self.total_px / capacidad_base_px))
        
        infraestructura = f"{self.puertos_rj45} puertos RJ45 (Cat6)."
        if self.distancia_cable_m > 100:
            infraestructura += " [!] Distancia crítica: requiere salto a fibra óptica."

        ratio_fisico = self._calcular_ratio(self.fis_w_mm, self.fis_h_mm)
        ratio_logico = self._calcular_ratio(self.res_w, self.res_h)

        shutter_segundos = self._parsear_shutter()
        ciclos_por_exposicion = self.refresh_rate_hz * shutter_segundos
        res_sync = f"Ciclos: {formato_latam(ciclos_por_exposicion, 1)} -> "
        res_sync += "🟢 ÓPTIMO" if ciclos_por_exposicion >= 50 else ("🟠 ADVERTENCIA" if ciclos_por_exposicion >= 25 else "🔴 CRÍTICO")

        return {
            "Total Px Calculados": f"{formato_latam(self.total_px, 0)} px",
            "Relación de Aspecto Lógica": f"{ratio_logico} (Mapeo) vs {ratio_fisico} (Física)",
            "Tasa de Refrescamiento": f"{formato_latam(self.refresh_rate_hz, 0)} Hz",
            "Sincronización de Cámara": res_sync,
            "Puertos RJ45 de Salida Req.": self.puertos_rj45,
            "Tarjetas Receptoras (R-Cards)": f"{self.total_gabinetes} tarjetas (1 por gabinete)",
            "Topología de Red": infraestructura
        }

    def calcular_hardware_procesador(self):
        capacidad_max_4k = 8800000
        equipos_4k_necesarios = max(1, math.ceil(self.total_px / capacidad_max_4k))
        capacidad_total_instalada = equipos_4k_necesarios * capacidad_max_4k
        
        if "8K" in self.input_res:
            base_cards = self.num_entradas * 4
            tarjetas_entrada = f"{self.num_entradas}x señal(es) 8K -> Req. {base_cards}x Entradas 4K (Quad-Link) o {self.num_entradas}x Tarjetas HDMI 2.1"
        elif "16K" in self.input_res:
            base_cards = self.num_entradas * 16
            tarjetas_entrada = f"{self.num_entradas}x señal(es) 16K -> Req. {base_cards}x Entradas 4K o {self.num_entradas * 4}x Tarjetas HDMI 2.1"
        elif "4K" in self.input_res:
            tarjetas_entrada = f"{self.num_entradas}x señal(es) 4K -> Req. {math.ceil(self.num_entradas/2)}x Tarjetas Dual-4K (o similar)"
        else:
            tarjetas_entrada = f"{self.num_entradas}x señal(es) HD -> Req. {math.ceil(self.num_entradas/4)}x Tarjetas Quad-HD"
            
        if not hasattr(self, 'puertos_rj45'):
            self.calcular_procesamiento()
            
        tarjetas_salida = max(1, math.ceil(self.puertos_rj45 / 16))
        opt_ports = math.ceil(self.puertos_rj45 / 10) 
        if self.distancia_cable_m > 100:
            interfaces_opt = f"SÍ: {opt_ports} puertos OPT 10G (Requiere {opt_ports} conversores CVT10 en pantalla)"
        else:
            interfaces_opt = "NO (Distancia segura < 100m)"

        return {
            "Formato y Calidad Base": f"{self.input_res} {self.calidad} @ {self.fps}fps",
            "Capacidad Máx. de Carga (Salida)": f"{formato_latam(capacidad_total_instalada, 0)} px ({equipos_4k_necesarios} núcleo(s) de procesamiento)",
            "Módulos de Entrada Req.": tarjetas_entrada,
            "Módulos de Salida Req.": f"{tarjetas_salida} tarjeta(s) de salida (Modular 16-port)",
            "Interfaces Ópticas (OPT)": interfaces_opt
        }

class LEDSCREENCALC:
    def __init__(self, uso, entorno, contenido, dim_req_w, dim_req_h, dist_vis_m, pitch, 
                 mod_res_w=None, mod_res_h=None, mod_w=None, mod_h=None, cab_w=None, cab_h=None):
        self.uso = uso
        self.entorno = entorno
        self.contenido = contenido
        self.req_w = dim_req_w
        self.req_h = dim_req_h
        self.dist_vis_m = dist_vis_m
        self.pitch = pitch
        self.mod_res_w = mod_res_w
        self.mod_res_h = mod_res_h
        self.mod_w = mod_w
        self.mod_h = mod_h
        
        self.datos_marca_suministrados = all(v is not None for v in [mod_res_w, mod_res_h, mod_w, mod_h, cab_w, cab_h])
        
        if self.datos_marca_suministrados:
            self.cab_w = cab_w
            self.cab_h = cab_h
            self.modulos_por_cab_w = int(self.cab_w // mod_w)
            self.modulos_por_cab_h = int(self.cab_h // mod_h)
            self.total_modulos_por_cab = self.modulos_por_cab_w * self.modulos_por_cab_h
            self.cab_res_w = int(mod_res_w * self.modulos_por_cab_w)
            self.cab_res_h = int(mod_res_h * self.modulos_por_cab_h)
        else:
            self.cab_w, self.cab_h = (600.0, 337.5) if self.entorno == "Indoor" else (960.0, 960.0)
            self.cab_res_w = int(self.cab_w / self.pitch)
            self.cab_res_h = int(self.cab_h / self.pitch)
            self.total_modulos_por_cab = 4 

    def _calcular_configuracion(self, columnas, filas):
        total_gabinetes = int(columnas * filas)
        total_modulos = int(total_gabinetes * self.total_modulos_por_cab)
        ancho_fisico = columnas * self.cab_w
        alto_fisico = filas * self.cab_h
        res_total_w = int(columnas * self.cab_res_w)
        res_total_h = int(filas * self.cab_res_h)
        total_px = res_total_w * res_total_h
        area_m2 = (ancho_fisico / 1000) * (alto_fisico / 1000)
        
        formatted = {}
        if self.datos_marca_suministrados:
            formatted["Resolución de módulos (px)"] = f"{formato_latam(self.mod_res_w, 0)} (Ancho) x {formato_latam(self.mod_res_h, 0)} (Alto)"
            formatted["Tamaño de módulo (mm)"] = f"{formato_latam(self.mod_w, 2)} (Ancho) x {formato_latam(self.mod_h, 2)} (Alto)"
            formatted["Tamaño del Gabinete (mm)"] = f"{formato_latam(self.cab_w, 2)} (Ancho) x {formato_latam(self.cab_h, 2)} (Alto)"
            formatted["Módulos x Gabinete"] = f"{self.modulos_por_cab_w} (W) x {self.modulos_por_cab_h} (H) = {self.total_modulos_por_cab} mód."
        else:
            formatted["Resolución de módulos (px)"] = "Cálculo Automático por Pitch"
            formatted["Tamaño de módulo (mm)"] = "Estándar"
            formatted["Tamaño del Gabinete (mm)"] = f"{formato_latam(self.cab_w, 2)} (Ancho) x {formato_latam(self.cab_h, 2)} (Alto)"
            formatted["Módulos x Gabinete"] = f"{self.total_modulos_por_cab} mód. (Estándar)"

        formatted["Gabinetes (Column x Filas)"] = f"{columnas} x {filas}"
        formatted["Piezas"] = f"{total_gabinetes} gabinetes ({total_modulos} módulos)"
        formatted["Resolución Total"] = f"{formato_latam(res_total_w, 0)} x {formato_latam(res_total_h, 0)} ({formato_latam(total_px, 0)} px)"
        formatted["Dimensiones Finales"] = f"{formato_latam(ancho_fisico, 1)} x {formato_latam(alto_fisico, 1)} mm"
        formatted["Tamaño en m²"] = f"{formato_latam(area_m2, 2)} m²"

        return {
            "raw": {"columnas": columnas, "filas": filas, "area_m2": area_m2, "total_px": total_px, 
                    "cab_w": self.cab_w, "total_gabinetes": total_gabinetes, "res_total_w": res_total_w, 
                    "res_total_h": res_total_h, "ancho_fisico": ancho_fisico, "alto_fisico": alto_fisico},
            "formatted": formatted
        }

    def generar_opciones(self):
        col_exact = self.req_w / self.cab_w
        fil_exact = self.req_h / self.cab_h
        
        opt_a = self._calcular_configuracion(max(1, round(col_exact)), max(1, round(fil_exact)))
        opt_b = self._calcular_configuracion(max(1, math.floor(col_exact)), max(1, math.floor(fil_exact)))
        opt_c = self._calcular_configuracion(max(1, math.ceil(col_exact)), max(1, math.ceil(fil_exact)))
        
        vis_min_m = self.pitch * 1
        vis_opt_m = self.pitch * 3
        agudeza_pies = self.pitch * 10
        
        return {"Opcion 1 (Ideal)": opt_a, "Opcion 2 (Inferior)": opt_b, "Opcion 3 (Superior)": opt_c, 
                "Visualizacion": {"Mínima": f"{formato_latam(vis_min_m, 2)} m", "Óptima": f"{formato_latam(vis_opt_m, 2)} m", "Retina (Agudeza)": f"{formato_latam(agudeza_pies, 2)} ft"}}

class LedPowerCalc:
    def __init__(self, area_m2, voltaje=220, entorno="Indoor"):
        self.area = area_m2
        self.voltaje = voltaje
        self.watts_max_m2 = 800 if entorno == "Outdoor" else 500

    def calcular_energia_y_clima(self):
        pot_max_w = self.area * self.watts_max_m2
        pot_prom_w = pot_max_w * 0.34 
        amp_total = pot_max_w / self.voltaje
        amp_fase = amp_total / 3
        btu_max_hr = pot_max_w * 3.412
        return {
            "Potencia Máxima": f"{formato_latam(pot_max_w / 1000, 2)} kW",
            "Potencia Promedio": f"{formato_latam(pot_prom_w / 1000, 2)} kW",
            f"Amperaje Total ({self.voltaje}V)": f"{formato_latam(amp_total, 2)} A",
            "Amperaje por Fase (3F)": f"{formato_latam(amp_fase, 2)} A / fase",
            "Carga Térmica (Max)": f"{formato_latam(btu_max_hr, 2)} BTU/hr",
            "HVAC Requerido": f"{formato_latam(btu_max_hr / 12000, 2)} Toneladas AC"
        }

class LedRiggingCalc:
    def __init__(self, columnas, filas, cab_w_mm, cab_peso_kg=11.0, factor_seguridad=8):
        self.columnas = columnas
        self.filas = filas
        self.cab_peso_kg = cab_peso_kg
        self.cab_w_m = cab_w_mm / 1000.0
        self.factor_seguridad = factor_seguridad

    def calcular_izaje(self):
        peso_pura = self.columnas * self.filas * self.cab_peso_kg
        peso_bumpers = self.columnas * 3.5 
        peso_cableado = peso_pura * 0.10
        carga_estatica = peso_pura + peso_bumpers + peso_cableado
        truss_m = math.ceil((self.columnas * self.cab_w_m) + 1.0)
        puntos_colgado = max(2, math.ceil(truss_m / 3.0) + 1)
        carga_por_punto = carga_estatica / puntos_colgado
        motor_sel = next((m for m in [250, 500, 1000, 2000] if m >= (carga_por_punto * self.factor_seguridad)), "Ing. Estructural Req.")

        return {
            "Carga Estática TOTAL (Dead Load)": f"{formato_latam(carga_estatica, 2)} kg",
            "Truss Sugerido (Min)": f"{formato_latam(truss_m, 2)} m",
            "Puntos de Motor": f"{puntos_colgado} puntos (Max 3m)",
            f"Capacidad Motor Req. (SF {self.factor_seguridad}:1)": f"{formato_latam(motor_sel, 0)} kg (WLL) / motor"
        }

# ==========================================
# 2. INTERFAZ GRÁFICA (Streamlit UI)
# ==========================================
st.set_page_config(page_title="LEDSCREENCALC | Broadcast Edition", layout="wide", page_icon="🖥️")

col_title, col_btn_txt, col_btn_xls = st.columns([2.5, 1, 1])
with col_title:
    st.title("🖥️ LEDSCREENCALC")
    st.markdown("### Simulador de Ingeniería para Pantallas LED (Broadcast & Live Events)")

st.divider()

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("⚙️ Parámetros del Proyecto")
    uso = st.selectbox("Uso", ["Cine", "TV", "Publicidad"])
    entorno = st.radio("Entorno", ["Indoor", "Outdoor"], horizontal=True)
    
    st.subheader("Medida Solicitada")
    col1, col2 = st.columns(2)
    with col1:
        req_w = st.number_input("Ancho (mm)", min_value=100.0, value=10000.0, step=100.0, format="%.1f")
    with col2:
        req_h = st.number_input("Alto (mm)", min_value=100.0, value=5000.0, step=100.0, format="%.1f")
    
    st.divider()
    st.header("🛠️ Configuración de Hardware")
    ingreso_manual = st.toggle("Ingresar Marca/Modelo Manual")
    
    mod_res_w = mod_res_h = mod_w = mod_h = cab_w = cab_h = None
    if ingreso_manual:
        pitch = st.number_input("Pixel Pitch (mm)", value=2.6, step=0.1, format="%.2f")
        st.markdown("**Tamaño Físico (mm)**")
        c_mw, c_mh = st.columns(2)
        with c_mw:
            mod_w = st.number_input("Módulo Ancho", value=250.0, step=10.0, format="%.1f")
            cab_w = st.number_input("Gab. Ancho", value=500.0, step=10.0, format="%.1f")
        with c_mh:
            mod_h = st.number_input("Módulo Alto", value=250.0, step=10.0, format="%.1f")
            cab_h = st.number_input("Gab. Alto", value=500.0, step=10.0, format="%.1f")
            
        st.markdown("**Resolución Módulo (px)**")
        c_rw, c_rh = st.columns(2)
        with c_rw:
            mod_res_w = st.number_input("Res. Ancho", value=104, step=1)
        with c_rh:
            mod_res_h = st.number_input("Res. Alto", value=104, step=1)
    else:
        pitch = st.number_input("Pixel Pitch estimado (mm)", value=2.6, step=0.1, format="%.2f")

    st.divider()
    st.header("🎛️ Procesamiento de Video")
    num_entradas = st.number_input("Cantidad de Entradas (Fuentes)", min_value=1, value=1, step=1)
    input_video = st.selectbox("Resolución de Entrada", ["HD (1080p)", "4K", "8K", "16K"], index=1)
    puerto_video = st.selectbox("Puerto de Conexión", ["HDMI 1.4", "HDMI 2.0", "HDMI 2.1", "DP 1.2", "DP 1.4", "12G-SDI"], index=1)
    calidad_video = st.selectbox("Profundidad de Color", ["SDR 8-bit", "HDR 10-bit", "HDR 12-bit"], index=1)
    dist_cable = st.number_input("Distancia a Control (m)", min_value=1.0, value=50.0, step=10.0, format="%.1f")

    hz_led = 3840.0
    shutter_cam = "1/60"
    if uso in ["Cine", "TV"]:
        st.divider()
        st.header("🎥 Setup de Cámara (Broadcast)")
        hz_led = st.selectbox("Refresco Pantalla (Hz)", [1920.0, 3840.0, 7680.0], index=1)
        shutter_cam = st.text_input("Shutter de Cámara", value="1/60")

# --- PROCESAMIENTO (LLAMADA A CLASES) ---
calc_hw = LEDSCREENCALC(uso, entorno, "Video", req_w, req_h, 10, pitch, mod_res_w, mod_res_h, mod_w, mod_h, cab_w, cab_h)
res_hw = calc_hw.generar_opciones()
base_raw = res_hw["Opcion 1 (Ideal)"]["raw"]

calc_proc = LedScreenProc(uso, base_raw["total_px"], base_raw["total_gabinetes"], input_video, puerto_video, calidad_video, 
                          distancia_cable_m=dist_cable, refresh_rate_hz=hz_led, shutter_speed_str=shutter_cam,
                          res_w=base_raw["res_total_w"], res_h=base_raw["res_total_h"],
                          fis_w_mm=base_raw["ancho_fisico"], fis_h_mm=base_raw["alto_fisico"], num_entradas=num_entradas)
                          
calc_pwr = LedPowerCalc(base_raw["area_m2"], voltaje=220, entorno=entorno)
calc_rig = LedRiggingCalc(base_raw["columnas"], base_raw["filas"], base_raw["cab_w"])

# --- BOTONES DE DESCARGA ---
with col_btn_txt:
    reporte_txt = generar_texto_reporte(req_w, req_h, res_hw, calc_proc, calc_pwr, calc_rig)
    st.download_button(label="📄 Descargar TXT", data=reporte_txt, file_name="Reporte_LED.txt", mime="text/plain", use_container_width=True)

with col_btn_xls:
    reporte_xls = generar_excel_reporte(req_w, req_h, res_hw, calc_proc, calc_pwr, calc_rig)
    st.download_button(label="📊 Descargar Excel", data=reporte_xls, file_name="Reporte_Ingenieria_LED.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# --- VISTA PRINCIPAL (RESULTADOS) ---
st.markdown(f"#### Medida Solicitada: **{formato_latam(req_w/1000, 2)} m (Ancho) x {formato_latam(req_h/1000, 2)} m (Alto)**")

tab1, tab2, tab3 = st.tabs(["⭐ Opción 1 (Ajuste Ideal)", "⬇️ Opción 2 (Ajuste Inferior)", "⬆️ Opción 3 (Ajuste Superior)"])

def render_dict(d):
    for k, v in d.items(): st.markdown(f"**{k}:** {v}")

with tab1: render_dict(res_hw["Opcion 1 (Ideal)"]["formatted"])
with tab2: render_dict(res_hw["Opcion 2 (Inferior)"]["formatted"])
with tab3: render_dict(res_hw["Opcion 3 (Superior)"]["formatted"])

st.divider()

colA, colB = st.columns(2)

with colA:
    with st.expander("👁️ CRITERIOS DE VISUALIZACIÓN", expanded=True): render_dict(res_hw["Visualizacion"])
    with st.expander("🔌 INGENIERÍA ELÉCTRICA Y CLIMA (220V)", expanded=True): render_dict(calc_pwr.calcular_energia_y_clima())

with colB:
    with st.expander("📡 DATA Y SEÑAL", expanded=True): render_dict(calc_proc.calcular_procesamiento())
    with st.expander("🎛️ HARDWARE DEL PROCESADOR", expanded=True): render_dict(calc_proc.calcular_hardware_procesador())
    with st.expander("🏗️ INGENIERÍA ESTRUCTURAL E IZAJE (DGUV-17)", expanded=True): render_dict(calc_rig.calcular_izaje())
