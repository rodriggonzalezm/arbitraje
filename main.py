import requests
import time
import os
from flask import Flask

app = Flask(__name__)

# === CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ===
MIN_GANANCIA_ARS = float(os.environ.get("MIN_GANANCIA_ARS", 10000))
CANTIDAD_ARS = float(os.environ.get("CANTIDAD_ARS", 880000))
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# === FUNCIONES ===

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{7552465649:AAHFaGSFt-UaYyPyPvbwEJmy_ySgpgXNHzw}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

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
    r = requests.post(url, json=data, headers=headers)
    res = r.json()
    try:
        return float(res["data"][0]["adv"]["price"])
    except:
        return None

def chequear_arbitraje():
    precio_compra_ars = obtener_precio_binance_p2p("ARS", "BUY")
    precio_venta_clp = obtener_precio_binance_p2p("CLP", "SELL")

    if not precio_compra_ars or not precio_venta_clp:
        print("❌ No se pudo obtener precio")
        return

    usdt_comprados = CANTIDAD_ARS / precio_compra_ars
    clp_recibidos = usdt_comprados * precio_venta_clp

    usd_en_chile = clp_recibidos / 945
    valor_en_ars = usd_en_chile * 1200

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
import threading

def loop():
    while True:
        chequear_arbitraje()
        time.sleep(300)

threading.Thread(target=loop).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
