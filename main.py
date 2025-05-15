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
        "rows": 5,
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
        orders = res.get("data", [])
        if not orders:
            print(f"No se encontraron órdenes para {fiat} {trans_type}")
            return None
        total_amount = 0.0
        total_price_volume = 0.0
        for order in orders:
            adv = order["adv"]
            price = float(adv["price"])
            amount = float(adv.get("minSingleTransAmount", 0))
            if amount > 0:
                total_amount += amount
                total_price_volume += price * amount
            else:
                total_amount += 1
                total_price_volume += price
        if total_amount == 0:
            return None
        precio_promedio = total_price_volume / total_amount
        return precio_promedio
    except Exception as e:
        print(f"Error obteniendo precio Binance P2P {fiat} {trans_type}: {e}")
        return None

def chequear_arbitraje():
    precio_compra_ars = obtener_precio_binance_p2p("ARS", "BUY")
    precio_venta_clp = obtener_precio_binance_p2p("CLP", "SELL")

    if not precio_compra_ars or not precio_venta_clp:
        print("❌ No se pudo obtener precio")
        return

    usdt_comprados = CANTIDAD_ARS / precio_compra_ars
    clp_recibidos = usdt_comprados * precio_venta_clp

    # Tipo de cambio oficiales (pueden actualizarse si querés usar otras fuentes)
    usd_to_ars = 1200
    usd_to_clp = 945

    usd_en_chile = clp_recibidos / usd_to_clp
    valor_en_ars = usd_en_chile * usd_to_ars

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
        time.sleep(300)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
