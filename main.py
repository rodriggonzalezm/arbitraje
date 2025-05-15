import requests
import time
import os
from flask import Flask
import threading

app = Flask(__name__)

# === CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ===
MIN_GANANCIA_ARS = float(os.environ.get("MIN_GANANCIA_ARS", 10000))
CANTIDAD_ARS = float(os.environ.get("CANTIDAD_ARS", 880000))
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# === FUNCIONES ===

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        r = requests.post(url, data=data)
        if r.status_code != 200:
            print(f"Error al enviar mensaje Telegram: {r.status_code} - {r.text}")
        else:
            print("Mensaje Telegram enviado correctamente.")
    except Exception as e:
        print(f"Excepción al enviar Telegram: {e}")

def obtener_precio_binance_p2p(fiat, trans_type):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    data = {
        "page": 1,
        "rows": 1,
        "payTypes": [],
        "asset": "USDT",
        "fiat": fiat,
        "tradeType": trans_type,
        "publisherType": None,
    }
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        r.raise_for_status()
        res = r.json()
        return float(res["data"][0]["adv"]["price"])
    except Exception as e:
        print(f"Error obteniendo precio Binance P2P {fiat} {trans_type}: {e}")
        return None

def obtener_tipo_cambio_usd(destino):
    # Usamos API pública para obtener tipo de cambio USD -> destino
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data["result"] == "success" and destino in data["rates"]:
            return float(data["rates"][destino])
        else:
            print(f"No se encontró tipo de cambio para USD->{destino}")
            return None
    except Exception as e:
        print(f"Error obteniendo tipo de cambio USD->{destino}: {e}")
        return None

def chequear_arbitraje():
    precio_compra_ars = obtener_precio_binance_p2p("ARS", "BUY")
    precio_venta_clp = obtener_precio_binance_p2p("CLP", "SELL")

    if precio_compra_ars is None or precio_venta_clp is None:
        print("❌ No se pudo obtener precio USDT en ARS o CLP")
        return

    # Calculamos cuántos USDT compramos con ARS
    usdt_comprados = CANTIDAD_ARS / precio_compra_ars
    # Cuánto CLP obtenemos al vender esos USDT en Chile
    clp_recibidos = usdt_comprados * precio_venta_clp

    # Obtener tipo de cambio USD -> CLP y USD -> ARS para convertir CLP a ARS
    usd_clp = obtener_tipo_cambio_usd("CLP")
    usd_ars = obtener_tipo_cambio_usd("ARS")

    if usd_clp is None or usd_ars is None:
        print("❌ No se pudo obtener tipo de cambio USD -> CLP o USD -> ARS")
        return

    # Convertimos CLP a USD y luego USD a ARS para valorar la ganancia final en ARS
    usd_equivalente = clp_recibidos / usd_clp
    valor_en_ars = usd_equivalente * usd_ars

    ganancia_ars = valor_en_ars - CANTIDAD_ARS

    print(f"💱 Compra ARS: {precio_compra_ars:.2f} | Venta CLP: {precio_venta_clp:.2f} | Ganancia: {ganancia_ars:.2f} ARS")

    if ganancia_ars >= MIN_GANANCIA_ARS:
        mensaje = f"""📢 ¡Oportunidad de arbitraje detectada!

Compra USDT en 🇦🇷 ARS a: {precio_compra_ars:.2f}
Vende USDT en 🇨🇱 CLP a: {precio_venta_clp:.2f}

Ganancia estimada: {ganancia_ars:,.2f} ARS ✅
"""
        enviar_telegram(mensaje)

# === SERVIDOR PARA RAILWAY ===
@app.route("/")
def home():
    return "Bot de arbitraje en ejecución 🟢"

# === LOOP CON THREAD PARA ARBITRAJE ===
def loop():
    while True:
        chequear_arbitraje()
        time.sleep(300)  # 5 minutos

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
