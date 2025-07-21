from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from storage import get_user, update_news_sub

router = Router()

@router.callback_query(F.data == "news_sub")
async def sub_news(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала создай паспорт")
        return
    await callback.message.edit_text(
        f"Настройки новостей:\n"
        f"Важные: {'✅' if user.news_svo else '❌'}\n"
        f"Общие: {'✅' if user.news_zhizhn else '❌'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить важные", callback_data="toggle_svo")],
            [InlineKeyboardButton(text="Изменить общие", callback_data="toggle_zhizhn")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]
        ])
    )

@router.callback_query(F.data == "toggle_svo")
async def toggle_svo(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    await update_news_sub(session, user.telegram_id, "svo", not user.news_svo)
    await sub_news(callback, session)

@router.callback_query(F.data == "toggle_zhizhn")
async def toggle_zhizhn(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    await update_news_sub(session, user.telegram_id, "zhizhn", not user.news_zhizhn)
    await sub_news(callback, session)