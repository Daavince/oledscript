
import configparser
import logging
import time
from pathlib import Path
import requests
from PIL import Image

CONFIG_FILES = [
    "/home/pi/oledscript/oledstatuspi.conf",
    "/home/pi/oledscript/oledstatuspi.local.conf",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("oled2telegram")
config = configparser.ConfigParser()
config.read(CONFIG_FILES)
BOT_TOKEN = config["telegram"]["bot_token"]
CHAT_ID = str(config["telegram"]["bot_chatID"])
IMAGE_PATH = Path(config["telegram"]["ImageFilePath"])
OUTPUT_PATH = Path(config["telegram"]["ImageFilePathOut"])
CODEWORD = config["telegram"]["CODEWORD"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
POLL_TIMEOUT = 50
HTTP_TIMEOUT = (10, 65)
RETRY_DELAY = 5
MULTI_PI_DELAY = 7

session = requests.Session()

def telegram_request(method, endpoint, **kwargs):
    response = session.request(
        method,
        f"{API_URL}/{endpoint}",
        timeout=kwargs.pop("timeout", (10, 30)),
        **kwargs,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {result.get('error_code', 'unknown')}"
        )
    return result
def get_updates(offset):
    return telegram_request(
        "GET",
        "getUpdates",
        params={"offset": offset, "timeout": POLL_TIMEOUT},
        timeout=HTTP_TIMEOUT,
    ).get("result", [])
def send_image():
    with Image.open(IMAGE_PATH) as image:
        background = Image.new("RGB", (256, 130), (0, 0, 0))
        background.paste(image.convert("RGB"), (64, 1))
        background.save(OUTPUT_PATH)
    for attempt in range(1, 4):
        try:
            with OUTPUT_PATH.open("rb") as photo:
                telegram_request("POST", "sendPhoto", data={"chat_id": CHAT_ID}, files={"photo": photo}, timeout=(10, 60))
            logger.info("OLED image sent successfully")
            return
        except requests.RequestException as exc:
            logger.warning("Photo upload attempt %d/3 failed: %s", attempt, type(exc).__name__)
            if attempt == 3:
                raise
            time.sleep(5)

def main():
    offset = 0
    pending = False
    logger.info("Starting Telegram bot; waiting for OLED image")
    started = time.time()
    deadline = started + 60
    startup_sent = False
    while time.time() < deadline:
        try:
            if IMAGE_PATH.stat().st_mtime >= started:
                with Image.open(IMAGE_PATH) as image:
                    image.verify()
                send_image()
                startup_sent = True
                logger.info("Startup OLED image delivered")
                break
        except (OSError, ValueError, requests.RequestException, RuntimeError) as exc:
            logger.warning("Startup OLED image not ready: %s", type(exc).__name__)
        time.sleep(2)
    if not startup_sent:
        logger.warning("Startup OLED image not delivered within readiness window")
    while True:
        if pending:
            try:
                send_image()
                pending = False
                time.sleep(MULTI_PI_DELAY)
            except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
                logger.warning("Pending image delivery failed: %s", type(exc).__name__)
                time.sleep(RETRY_DELAY)
            continue
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = max(offset, update["update_id"] + 1)
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = str(message.get("chat", {}).get("id", ""))
                if chat_id == CHAT_ID and CODEWORD in text:
                    logger.info("Authorized codeword received")
                    pending = True
        except (requests.RequestException, ValueError, RuntimeError, KeyError, TypeError) as exc:
            logger.warning("Telegram polling error: %s", type(exc).__name__)
            time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
