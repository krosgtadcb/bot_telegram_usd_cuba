import requests
import logging
import asyncio
import threading
from datetime import datetime
from bs4 import BeautifulSoup
import re
from telegram import Bot
from flask import Flask

# ================= CONFIG =================

TELEGRAM_TOKEN = "8204621263:AAFWiXWdMH-vvRmGUb91eK45Ill_tJtRVFo"
CHAT_ID = "-1003728489867"

INTERVALO_MINUTOS = 5
TIMEOUT_SEGUNDOS = 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

bot_activo = True

# ================= WEB SIMPLE =================

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>BOT USD</h1>"

# ================= SCRAPER =================

def obtener_precio_eltoque():
    try:
        url = "https://eltoque.com/precio-del-dolar-en-el-mercado-informal-en-cuba-hoy"
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=TIMEOUT_SEGUNDOS)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        texto = soup.get_text(" ")

        datos = {
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "monedas": {}
        }

        patrones = {
            "USD": [r"USD[^0-9]{0,20}(\d{2,4})", r"dólar[^0-9]{0,20}(\d{2,4})"],
            "ZELLE": [r"Zelle[^0-9]{0,20}(\d{2,4})"],
            "MLC": [r"MLC[^0-9]{0,20}(\d{2,4})"]
        }

        for moneda, lista in patrones.items():
            for patron in lista:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    datos["monedas"][moneda] = int(match.group(1))
                    break

        return datos if datos["monedas"] else None

    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        return None

# ================= TELEGRAM =================

async def enviar_precio_telegram(datos):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        emojis = {"USD":"💵","ZELLE":"📱","MLC":"🏦"}

        msg = "💱 <b>TASAS DE CAMBIO - CUBA</b>\n"
        msg += f"🕒 {datos['fecha']}\n"
        msg += "━━━━━━━━━━━━━━\n"

        for moneda, precio in datos["monedas"].items():
            msg += f"{emojis.get(moneda,'💱')} <b>{moneda}</b>: <code>{precio}</code> CUP\n"

        msg += "━━━━━━━━━━━━━━\n📊 Fuente: elToque.com"

        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")
        logger.info("Mensaje enviado a Telegram")

    except Exception as e:
        logger.error(f"Error enviando a Telegram: {e}")

# ================= LOOP BOT =================

def loop_bot():
    while bot_activo:
        datos = obtener_precio_eltoque()

        if datos:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(enviar_precio_telegram(datos))
            loop.close()
        else:
            logger.warning("⚠️ No se obtuvieron los precios")

        threading.Event().wait(INTERVALO_MINUTOS * 60)

# ================= MAIN =================

if __name__ == "__main__":
    logger.info("🤖 Bot USD iniciado")

    hilo = threading.Thread(target=loop_bot, daemon=True)
    hilo.start()

    # Iniciar web simple
    app.run(host="0.0.0.0", port=0.0.0.0)
