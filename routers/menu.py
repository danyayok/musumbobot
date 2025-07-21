from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS

router = Router()


@router.message(F.text == "/menu")
async def show_menu(message: Message):
    # Стандартные кнопки
    keyboard = [
        [InlineKeyboardButton(text="📄 Паспорт", callback_data="menu_passport")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ]

    if message.from_user.id in ADMIN_IDS:
        keyboard.extend([
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_news")],
            [InlineKeyboardButton(text="🏅 Медали", callback_data="admin_medals")]
        ])


    await message.answer(
        "🔘 Главное меню:\nВыбери раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="📄 Паспорт", callback_data="menu_passport")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="news_sub")]
    ]

    if callback.from_user.id in ADMIN_IDS:
        keyboard.extend([
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_news")],
            [InlineKeyboardButton(text="🏅 Медали", callback_data="admin_medals")]
        ])

    await callback.message.edit_text(
        "🔘 Главное меню:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )