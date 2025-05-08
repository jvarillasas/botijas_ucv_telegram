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
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from dotenv import load_dotenv

# --- Configuración inicial para Railway (Chromium) ---
# Instalar dependencias del sistema (solo en entornos Linux como Railway)
if os.name == 'posix':
    os.system("apt-get update")
    os.system("apt install -y chromium chromium-driver")

# Cargar variables de entorno
load_dotenv()

# --- Variables de entorno ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
BLACKBOARD_USER = os.getenv('BLACKBOARD_USER')
BLACKBOARD_PASS = os.getenv('BLACKBOARD_PASS')
BLACKBOARD_URL = os.getenv('BLACKBOARD_URL')

# --- Configuración del bot de Telegram ---
application = Application.builder().token(TELEGRAM_TOKEN).build()
bot_active = False  # Control de estado

# --- Funciones auxiliares ---
async def send_telegram_message(message: str):
    """Envía un mensaje de texto al chat de Telegram."""
    try:
        message = message.encode('ascii', 'ignore').decode('ascii')
        await application.bot.send_chat_action(chat_id=CHAT_ID, action=ChatAction.TYPING)
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Error enviando mensaje: {str(e)}")

async def send_photo_to_telegram(photo_path: str, caption: str = ""):
    """Envía una foto al chat de Telegram y elimina el archivo después."""
    try:
        if not os.path.exists(photo_path):
            await send_telegram_message(f"⚠️ Archivo no encontrado: {photo_path}")
            return False
        
        await application.bot.send_chat_action(chat_id=CHAT_ID, action=ChatAction.UPLOAD_PHOTO)
        with open(photo_path, 'rb') as photo:
            await application.bot.send_photo(
                chat_id=CHAT_ID,
                photo=photo,
                caption=caption[:1024]  # Límite de caracteres en Telegram
            )
        os.remove(photo_path)
        return True
    except Exception as e:
        print(f"📸 Error enviando foto: {str(e)}")
        return False

def setup_chrome_driver():
    """Configura el navegador Chrome/Chromium en modo headless."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configuración específica para Railway
    chrome_options.binary_location = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    
    return webdriver.Chrome(
        service=Service(chromedriver_path),
        options=chrome_options
    )

# --- Lógica principal ---
async def process_page(driver, url: str, page_name: str):
    """Procesa una página, toma capturas y las envía a Telegram."""
    try:
        await send_telegram_message(f"🔄 Procesando {page_name}...")
        driver.get(url)
        time.sleep(8)  # Espera a que cargue la página
        
        screenshot_path = f"{page_name}.png"
        driver.save_screenshot(screenshot_path)
        await send_photo_to_telegram(screenshot_path, f"📌 {page_name.upper()}")
        
    except WebDriverException as e:
        await send_telegram_message(f"🚨 Error en {page_name}: {str(e)}")
    except Exception as e:
        await send_telegram_message(f"❌ Error inesperado: {str(e)}")

async def check_blackboard():
    """Función principal que maneja el flujo de Blackboard."""
    global bot_active
    driver = None
    
    try:
        driver = setup_chrome_driver()
        await send_telegram_message("🔑 Iniciando sesión en Blackboard...")
        
        # Login
        driver.get(BLACKBOARD_URL)
        time.sleep(5)
        driver.find_element(By.ID, "user_id").send_keys(BLACKBOARD_USER)
        driver.find_element(By.ID, "password").send_keys(BLACKBOARD_PASS)
        driver.find_element(By.ID, "entry-login").click()
        time.sleep(8)
        
        # Páginas a procesar
        pages = {
            "Actividad Reciente": "https://ucv.blackboard.com/ultra/stream",
            "Calendario": "https://ucv.blackboard.com/ultra/calendar",
            "Calificaciones": "https://ucv.blackboard.com/ultra/grades"
        }
        
        for name, url in pages.items():
            await process_page(driver, url, name)
            
        await send_telegram_message("✅ Proceso completado!")
        
    except NoSuchElementException:
        await send_telegram_message("🔍 No se encontró un elemento en la página. ¿Cambió la estructura de Blackboard?")
    except Exception as e:
        await send_telegram_message(f"💥 Error crítico: {str(e)}")
    finally:
        if driver:
            driver.quit()
        bot_active = False

# --- Comandos de Telegram ---
async def start(update: Update, context: CallbackContext):
    global bot_active
    if bot_active:
        await update.message.reply_text("⏳ El bot ya está en proceso. Espera a que termine.")
    else:
        bot_active = True
        await update.message.reply_text("🚀 Iniciando bot...")
        await check_blackboard()

# --- Ejecución ---
if __name__ == "__main__":
    # Registro de comandos
    application.add_handler(CommandHandler("start", start))
    
    # Mensaje de inicio (útil para logs)
    print("🤖 Bot iniciado. Esperando comandos...")
    
    # Iniciar el bot
    application.run_polling()
