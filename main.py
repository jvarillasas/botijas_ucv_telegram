import asyncio
import os
import time
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.constants import ChatAction
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
BLACKBOARD_USER = os.getenv('BLACKBOARD_USER')
BLACKBOARD_PASS = os.getenv('BLACKBOARD_PASS')
BLACKBOARD_URL = os.getenv('BLACKBOARD_URL')

# Crear bot de Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Estado para evitar que el bot siga enviando fotos
bot_active = False  # Estado para saber si el bot está en proceso o no

# Enviar mensaje
async def send_telegram_message(message: str):
    try:
        message = message.encode('ascii', 'ignore').decode('ascii')
        await application.bot.send_chat_action(chat_id=CHAT_ID, action=ChatAction.TYPING)
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Error enviando mensaje: {str(e)}")

# Enviar foto
async def send_photo_to_telegram(photo_path: str, caption: str):
    try:
        if not os.path.exists(photo_path):
            await send_telegram_message(f"Archivo no encontrado: {photo_path}")
            return False
        caption = caption.encode('ascii', 'ignore').decode('ascii')
        await application.bot.send_chat_action(chat_id=CHAT_ID, action=ChatAction.UPLOAD_PHOTO)
        with open(photo_path, 'rb') as photo:
            await application.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=caption)
        os.remove(photo_path)  # Eliminar la foto después de enviarla
        return True
    except Exception as e:
        print(f"Error enviando foto: {str(e)}")
        return False

# Captura de pantalla (solo la parte superior)
def take_screenshots(driver, page_name):
    try:
        top_filename = f"{page_name}_top.png"
        driver.save_screenshot(top_filename)
        time.sleep(2)  # Espera después de la captura de la parte superior
        return top_filename  # Solo devuelve la captura de la parte superior
    except Exception as e:
        print(f"Error en capturas de {page_name}: {str(e)}")
        return None

# Procesar página
async def process_page(driver, url, page_name):
    await send_telegram_message(f"Procesando {page_name}...")
    driver.get(url)
    time.sleep(8)
    top_file = take_screenshots(driver, page_name)  # Solo obtenemos la parte superior
    if top_file:
        await send_photo_to_telegram(top_file, f"PARTE SUPERIOR - {page_name}")
    else:
        await send_telegram_message(f"Fallo la captura de {page_name}")

# Función para iniciar el proceso desde Telegram
async def start(update: Update, context: CallbackContext):
    global bot_active
    if bot_active:
        await update.message.reply_text("El proceso ya ha sido completado. Esperando el próximo comando '/start'.")
    else:
        bot_active = True  # Activamos el estado del bot para que inicie el proceso
        await update.message.reply_text("Bot iniciado. Procesando...")
        await check_blackboard()  # Llamar a la función que maneja el proceso de Blackboard

# Función principal para iniciar sesión en Blackboard y procesar las páginas
async def check_blackboard():
    global bot_active
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = os.getenv("GOOGLE_CHROME_BIN", shutil.which("chromium"))
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", shutil.which("chromedriver"))
    driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    try:
        await send_telegram_message("Iniciando sesion en Blackboard...")
        driver.get(BLACKBOARD_URL)
        time.sleep(5)
        driver.find_element(By.ID, "user_id").send_keys(BLACKBOARD_USER)
        driver.find_element(By.ID, "password").send_keys(BLACKBOARD_PASS)
        driver.find_element(By.ID, "entry-login").click()
        time.sleep(8)
        await process_page(driver, "https://ucv.blackboard.com/ultra/stream", "ACTIVIDAD_RECIENTE")
        await process_page(driver, "https://ucv.blackboard.com/ultra/calendar", "CALENDARIO")
        await process_page(driver, "https://ucv.blackboard.com/ultra/grades", "CALIFICACIONES")
        await send_telegram_message("Proceso completado.")
    except Exception as e:
        await send_telegram_message(f"Error global: {str(e)}")
    finally:
        bot_active = False  # El bot vuelve al estado inactivo
        driver.quit()

# Registrar el handler para el comando '/start'
application.add_handler(CommandHandler("start", start))

# Ejecutar el bot de Telegram
if __name__ == "__main__":
    application.run_polling()