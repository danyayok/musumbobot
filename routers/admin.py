from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.exc import SQLAlchemyError

from storage import get_user, get_all_users
from config import ADMIN_IDS
from database.models import User

router = Router()

MEDALS = ["🎖 За взятие за щёку", "🥉 За терпение", "🥈 За тряску", "🏅 За постройку Z", "🌟 Звезда Мусумбы"]


class AdminStates(StatesGroup):
    news_type = State()
    news_text = State()
    medal_action = State()
    medal_user = State()
    medal_select = State()


async def commit_with_rollback(session: AsyncSession):
    """Безопасное сохранение изменений с откатом при ошибке"""
    try:
        await session.commit()
        return True
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        await session.rollback()
        return False


# ===== Управление новостями =====
@router.callback_query(F.data == "admin_news")
async def admin_news_start(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Важные новости", callback_data="news_type_svo")],
        [InlineKeyboardButton(text="🔵 Общие новости", callback_data="news_type_zhizhn")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])
    await callback.message.edit_text(
        "📢 <b>Админ-панель рассылки</b>\nВыберите тип новостей:",
        reply_markup=keyboard
    )
    await session.close()


@router.callback_query(F.data.startswith("news_type_"))
async def select_news_type(callback: CallbackQuery, state: FSMContext):
    news_type = callback.data.split("_")[2]
    await state.update_data(news_type=news_type)
    await state.set_state(AdminStates.news_text)

    await callback.message.edit_text(
        f"✍️ Введите текст {'важных' if news_type == 'svo' else 'общих'} новостей:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
        ])
    )


@router.message(AdminStates.news_text)
async def send_news_to_users(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    news_type = data.get("news_type")

    if not news_type:
        await message.answer("❌ Произошла ошибка. Попробуйте снова.")
        await state.clear()
        return

    try:
        stmt = select(User).where(
            User.news_svo == True if news_type == "svo" else User.news_zhizhn == True
        )
        result = await session.execute(stmt)
        subscribers = result.scalars().all()

        success = 0
        for user in subscribers:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"📢 <b>{'🔴 Важная новость' if news_type == 'svo' else '🔵 Общая новость'}</b>\n\n"
                         f"{message.text}"
                )
                success += 1
            except Exception as e:
                print(f"Ошибка отправки для {user.telegram_id}: {e}")

        await message.answer(
            f"✅ Рассылка завершена\n"
            f"Тип: {'важные' if news_type == 'svo' else 'общие'} новости\n"
            f"Доставлено: {success}/{len(subscribers)} пользователей",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]]
            )
        )
    except SQLAlchemyError as e:
        await message.answer("❌ Ошибка при работе с базой данных")
        print(f"Database error: {e}")
    finally:
        await state.clear()
        await session.close()


# ===== Управление медалями =====
@router.callback_query(F.data == "admin_medals")
async def admin_medals_start(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎖 Выдать медаль", callback_data="medal_action_give")],
        [InlineKeyboardButton(text="❌ Изъять медаль", callback_data="medal_action_take")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])
    await callback.message.edit_text(
        "🏅 Управление наградами\nВыберите действие:",
        reply_markup=keyboard
    )
    await session.close()


@router.callback_query(F.data.startswith("medal_action_"))
async def medal_action_select(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    action = callback.data.split("_")[2]
    if action not in ["give", "take"]:
        await callback.answer("❌ Неизвестное действие")
        return

    await state.update_data(medal_action=action)
    await state.set_state(AdminStates.medal_user)

    try:
        # Получаем всех пользователей
        result = await session.execute(select(User))
        all_users = result.scalars().all()

        # Фильтруем в Python, а не в SQL
        if action == "take":
            users = [u for u in all_users if u.awards and len(u.awards) > 0]
            if not users:
                await callback.answer("❌ Нет пользователей с наградами")
                return
        else:
            users = all_users

        # Создаём кнопки
        keyboard_buttons = [
            [InlineKeyboardButton(
                text=f"{user.full_name} (@{user.username})" if user.username else user.full_name,
                callback_data=f"medal_user_{user.telegram_id}"
            )] for user in users
        ]
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_medals")])

        await callback.message.edit_text(
            f"Выберите пользователя для {'вручения' if action == 'give' else 'изъятия'} медали:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
    except Exception as e:
        await callback.answer("❌ Ошибка при получении пользователей")
        print(f"Error: {e}")
    finally:
        await session.close()


@router.callback_query(F.data.startswith("medal_user_"), AdminStates.medal_user)
async def medal_user_select(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(callback.data.split("_")[2])
        user = await get_user(session, user_id)

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        await state.update_data(medal_user=user_id)
        data = await state.get_data()
        action = data.get("medal_action")

        if action == "take" and not user.awards:
            await callback.answer("❌ У пользователя нет наград")
            return

        medals_list = MEDALS if action == "give" else user.awards

        keyboard_buttons = [
            [InlineKeyboardButton(text=medal, callback_data=f"medal_select_{medal}")]
            for medal in medals_list
        ]
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_medals")])

        await callback.message.edit_text(
            f"Выберите медаль для {'вручения' if action == 'give' else 'изъятия'} "
            f"пользователю {user.full_name}:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        )
        await state.set_state(AdminStates.medal_select)
    except (IndexError, ValueError, SQLAlchemyError) as e:
        await callback.answer("❌ Ошибка обработки запроса")
        print(f"Error: {e}")
    finally:
        await session.close()


@router.callback_query(F.data.startswith("medal_select_"), AdminStates.medal_select)
async def medal_final_action(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    try:
        # 1. Разбираем callback данные
        medal_name = callback.data.split("_", 2)[2]
        print(f"Выбрана медаль: {medal_name}")  # Логирование для отладки

        # 2. Получаем сохранённые данные из состояния
        data = await state.get_data()
        user_id = data.get("medal_user")
        action = data.get("medal_action")
        print(f"Данные из состояния: user_id={user_id}, action={action}")

        if not user_id or not action:
            await callback.answer("❌ Ошибка: данные сессии утеряны", show_alert=True)
            await state.clear()
            return

        # 3. Получаем пользователя
        print(f"Пытаемся найти пользователя с telegram_id={user_id}")
        user = await get_user(session, user_id)

        if not user:
            print("Пользователь не найден в базе")
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        # 4. Обрабатываем действие
        if action == "give":
            if medal_name in user.awards:
                await callback.answer("ℹ️ У пользователя уже есть эта медаль")
                return

            # Добавляем медаль
            new_awards = user.awards + [medal_name]
            user.awards = new_awards
            success_msg = f"✅ Медаль {medal_name} выдана пользователю {user.full_name}"
            user_msg = f"🎉 Вам вручена медаль: {medal_name}"

        elif action == "take":
            if medal_name not in user.awards:
                await callback.answer("ℹ️ У пользователя нет этой медали")
                return

            # Удаляем медаль
            new_awards = [m for m in user.awards if m != medal_name]
            user.awards = new_awards
            success_msg = f"✅ Медаль {medal_name} изъята у {user.full_name}"
            user_msg = f"😔 У вас изъята медаль: {medal_name}"

        else:
            await callback.answer("❌ Неизвестное действие", show_alert=True)
            return

        # 5. Сохраняем изменения
        session.add(user)
        try:
            await session.commit()

            # 6. Отправляем уведомление пользователю
            try:
                await bot.send_message(user_id, user_msg)
            except Exception as e:
                print(f"Не удалось отправить уведомление: {e}")

            # 7. Обновляем сообщение админа
            await callback.message.edit_text(
                success_msg,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu")]
                ])
            )
            await callback.answer()

        except Exception as e:
            await session.rollback()
            await callback.answer(f"❌ Ошибка сохранения: {str(e)}", show_alert=True)
            print(f"Ошибка БД: {e}")

    except Exception as e:
        print(f"Общая ошибка: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        await state.clear()

# ===== Общие функции =====
@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ])
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка новостей", callback_data="admin_news")],
        [InlineKeyboardButton(text="🏅 Управление медалями", callback_data="admin_medals")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu")]
    ])
    await callback.message.edit_text(
        "👑 <b>Административное меню</b>\nВыберите раздел:",
        reply_markup=keyboard
    )