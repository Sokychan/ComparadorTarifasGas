import json
import logging
import re
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

USER_AGENT_REAL = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Configuración del navegador optimizada para Xvfb en GitHub Actions
LAUNCH_ARGS = {
    "headless": False,
    "args": ["--window-position=-2000,-2000", "--no-sandbox", "--disable-dev-shm-usage"]
}
TIMEOUT_MS = 30000
JSON_FILENAME = "tarifas_gas_mercado.json"

# =============================================================
# FUNCIONES DE EXTRACCIÓN
# =============================================================

def extraer_iberdrola(p):
    logging.info("Extrayendo Iberdrola Gas...")
    url = "https://www.iberdrola.es/gas/tarifas/plan-gas-hogar"
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        try:
            pagina.click("#onetrust-accept-btn-handler", timeout=3000)
        except Exception:
            pass

        pagina.wait_for_selector("#precios-dinamicos", timeout=TIMEOUT_MS)

        nombre_tarifa = pagina.locator("#precios-dinamicos .titulo-plan").first.text_content().strip()
        pagina.locator("#precios-dinamicos .select-potencia button").filter(has_text="Tarifa RL.1").dispatch_event("click")

        termino_fijo = float(pagina.locator("#precios-dinamicos .seccion-potencia .precio-potencia .precio-con-descuento").first.text_content().strip().replace(",", "."))
        termino_variable = float(pagina.locator("#detalle .seccion-energia .precio-hora").first.text_content().strip().split()[0].replace(",", "."))

        navegador.close()
        return {
            "Comercializadora": "Iberdrola",
            "Nombre_Tarifa": nombre_tarifa,
            "Termino_Fijo_Dia": round(termino_fijo, 6),
            "Termino_Variable_kWh": round(termino_variable, 6)
        }
    except Exception as e:
        logging.error(f"Error al extraer Iberdrola Gas: {e}")
        return None


def extraer_tur(p):
    logging.info("Extrayendo Curenergía (TUR)...")
    url = "https://www.curenergia.es/tarifa-regulada-gas/ultimo-recurso-gas"
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        try:
            pagina.click("#onetrust-accept-btn-handler", timeout=3000)
        except Exception:
            pass

        pagina.wait_for_selector("#tab1", timeout=TIMEOUT_MS)

        bloque_tur = pagina.locator("#tab1 .contenedor-total-tabla-precios-123 .tabla-completa123").filter(has_text="TUR.1")
        nombre_tarifa = bloque_tur.locator(".titulo-tabla123").first.text_content().strip()
        termino_fijo = float(bloque_tur.locator(".tabla-precios123 .fijo-tabla-precios123 .precio-sin-impuestos-tabla-precios123 .tur1-psi-fijo").first.text_content().strip().replace(",", "."))
        termino_variable = float(bloque_tur.locator(".tabla-precios123 .variable-tabla-precios123 .precio-sin-impuestos-tabla-precios123 .tur1-psi-variable").first.text_content().strip().replace(",", "."))

        navegador.close()
        return {
            "Comercializadora": "Curenergía (TUR)",
            "Nombre_Tarifa": nombre_tarifa,
            "Termino_Fijo_Dia": round(termino_fijo, 6),
            "Termino_Variable_kWh": round(termino_variable, 6)
        }
    except Exception as e:
        logging.error(f"Error al extraer TUR Gas: {e}")
        return None


def extraer_endesa(p):
    logging.info("Extrayendo Endesa Gas...")
    tarifas_endesa = []
    urls = [
        ("One Gas", "https://www.endesa.com/es/luz-y-gas/gas/tarifa-one-gas"),
        ("Conecta Gas", "https://www.endesa.com/es/luz-y-gas/gas/conecta-de-endesa")
    ]

    for etiqueta, url in urls:
        try:
            navegador = p.chromium.launch(**LAUNCH_ARGS)
            contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
            pagina = contexto.new_page()
            pagina.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

            try:
                pagina.click("#onetrust-accept-btn-handler", timeout=3000)
            except Exception:
                pass

            pagina.wait_for_selector(".floating-card-container", timeout=TIMEOUT_MS)

            nombre_tarifa = pagina.locator(".floating-card-container .commodity-card-xs__content__body__information__product__title").first.text_content().strip()
            tv_raw = pagina.locator(".commodity-card-xs__content__body__information__price").filter(has_text="Término variable").locator(".commodity-card-xs__content__body__information__price__detail__price__discounted").first.text_content().strip().replace(",", ".")
            tf_raw = pagina.locator(".commodity-card-xs__content__body__information__price").filter(has_text="Término fijo").locator(".commodity-card-xs__content__body__information__price__detail__price__discounted").first.text_content().strip().replace(",", ".")

            termino_variable = float(tv_raw)
            termino_fijo_dia = float(tf_raw) / 30.0

            navegador.close()
            tarifas_endesa.append({
                "Comercializadora": "Endesa",
                "Nombre_Tarifa": nombre_tarifa,
                "Termino_Fijo_Dia": round(termino_fijo_dia, 6),
                "Termino_Variable_kWh": round(termino_variable, 6)
            })
        except Exception as e:
            logging.error(f"Error al extraer Endesa ({etiqueta}): {e}")

    return tarifas_endesa


def extraer_totalenergies(p):
    logging.info("Extrayendo TotalEnergies Gas...")
    tarifas_te = []
    urls = [
        ("A Tu Aire", "https://www.totalenergies.es/es/hogares/tarifas-gas/a-tu-aire"),
        ("4 Estaciones", "https://www.totalenergies.es/es/hogares/tarifas-gas/trimestrales-4-estaciones")
    ]

    for etiqueta, url in urls:
        try:
            navegador = p.chromium.launch(**LAUNCH_ARGS)
            contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
            pagina = contexto.new_page()
            pagina.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

            try:
                pagina.click("#onetrust-accept-btn-handler", timeout=3000)
            except Exception:
                pass

            pagina.wait_for_selector("#bloque-redisenio-toogle-gas", timeout=TIMEOUT_MS)

            nombre_tarifa = pagina.locator("#bloque-redisenio-toogle-gas h2.item--title").first.text_content().strip()
            bloque_rl1 = pagina.locator("#bloque-redisenio-toogle-gas .precios--toogle-region-content").filter(has_text="RL1")

            tf_raw = bloque_rl1.locator(".precios--lista .main-content").first.text_content().strip().split()[0].replace(",", ".")
            tv_raw = bloque_rl1.locator(".contenido-plegado .precios--lista .precio-secondary").first.text_content().strip().split()[0].replace(",", ".")

            termino_fijo_mes = float(tf_raw)
            termino_variable = float(tv_raw)

            navegador.close()
            tarifas_te.append({
                "Comercializadora": "TotalEnergies",
                "Nombre_Tarifa": nombre_tarifa,
                "Termino_Fijo_Dia": round((termino_fijo_mes * 12) / 365.0, 6),
                "Termino_Variable_kWh": round(termino_variable, 6)
            })
        except Exception as e:
            logging.error(f"Error al extraer TotalEnergies ({etiqueta}): {e}")

    return tarifas_te


def extraer_octopus(p):
    logging.info("Extrayendo Octopus Energy Gas...")
    url = "https://octopusenergy.es/precios"
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        pagina.wait_for_selector("#content .gpHZqY", timeout=TIMEOUT_MS)
        pagina.locator("#content .gpHZqY button").filter(has_text="Gas").first.dispatch_event("click")

        bloque_gas = pagina.locator("#content #tarifas-octopus-energy")
        nombre_tarifa = bloque_gas.locator("h2.cxYASs").first.text_content().strip()

        bloque_rl1 = bloque_gas.locator(".gpHZqY").filter(has_text="RL1")
        tf_raw = bloque_rl1.locator(".zyUhF.dewUnf.dDWCpe.jdmOZf.cMGtQw.fPSBzf.ZWNVL.gTvoMs").filter(has_text="fijo").locator(".cxYASs.fFnYom.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",", ".")
        
        texto_variable = bloque_rl1.locator(".zyUhF.dewUnf.dDWCpe").filter(has_text="variable").text_content()
        tv_raw = re.search(r"variable *\s*([\d,]+)", texto_variable).group(1).replace(",", ".")

        termino_fijo = float(tf_raw)
        termino_variable = float(tv_raw)

        navegador.close()
        return {
            "Comercializadora": "Octopus Energy",
            "Nombre_Tarifa": nombre_tarifa,
            "Termino_Fijo_Dia": round(termino_fijo, 6),
            "Termino_Variable_kWh": round(termino_variable, 6)
        }
    except Exception as e:
        logging.error(f"Error al extraer Octopus Gas: {e}")
        return None

# =============================================================
# ORQUESTADOR PRINCIPAL
# =============================================================

def actualizar_todas_las_tarifas_gas_json():
    logging.info("🚀 Iniciando extracción de tarifas de gas...")
    lista_tarifas = []

    with sync_playwright() as p:
        res_iberdrola = extraer_iberdrola(p)
        if res_iberdrola:
            lista_tarifas.append(res_iberdrola)

        res_tur = extraer_tur(p)
        if res_tur:
            lista_tarifas.append(res_tur)

        res_endesa = extraer_endesa(p)
        if res_endesa:
            lista_tarifas.extend(res_endesa)

        res_te = extraer_totalenergies(p)
        if res_te:
            lista_tarifas.extend(res_te)

        res_octopus = extraer_octopus(p)
        if res_octopus:
            lista_tarifas.append(res_octopus)

    if lista_tarifas:
        with open(JSON_FILENAME, "w", encoding="utf-8") as f:
            json.dump(lista_tarifas, f, ensure_ascii=False, indent=2)
        logging.info(f"Éxito: Se han guardado {len(lista_tarifas)} tarifas en '{JSON_FILENAME}'.")
        return True
    else:
        logging.warning("No se obtuvieron datos en la extracción de gas.")
        return False


if __name__ == "__main__":
    actualizar_todas_las_tarifas_gas_json()
