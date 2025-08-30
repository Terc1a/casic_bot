from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
import asyncio

API_TOKEN = '8313008915:AAG8H7ewP12xDeyZF1fEI8-lT1X8z6W7FE0'

# Создаем бота и диспетчер
bot = Bot(token=API_TOKEN, default=DefaultBotProperties())
dp = Dispatcher()

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    web_app = WebAppInfo(url='https://cas.hikariplus.ru')
    button = KeyboardButton(text='Открыть веб-приложение', web_app=web_app)
    
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],  # Кнопки должны быть вложены в список списков
        resize_keyboard=True
    )
    
    await message.answer("Нажмите кнопку ниже для запуска веб-приложения:", reply_markup=keyboard)

async def main():
    try:
        print("Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
        print('Бот онлайн')
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")