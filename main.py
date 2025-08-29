import asyncio
import logging
from bot.logger import setup_logging
from bot.handlers import build_app

def main():
    setup_logging()
    app = build_app()
    app.run_polling()

if __name__ == "__main__":
    main()