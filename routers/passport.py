from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from storage import create_user, get_user

router = Router()


class PassCreate(StatesGroup):
    nickname = State()
    rank = State()
    town = State()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    if await get_user(session, message.from_user.id):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]
            ]
        )
        await message.answer("Вы certified musumba ситизен", reply_markup=keyboard)
        return

    await message.answer("Привет! Нажми кнопку, чтобы продолжить:",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Продолжить", callback_data="continue_pressed")]
                         ]))


@router.callback_query(F.data == "continue_pressed")
async def on_continue(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи свой nickname:")
    await state.set_state(PassCreate.nickname)


@router.message(PassCreate.nickname)
async def get_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer("Теперь введи свой ранг:")
    await state.set_state(PassCreate.rank)


@router.message(PassCreate.rank)
async def get_rank(message: Message, state: FSMContext):
    await state.update_data(rank=message.text)
    await message.answer("Из какого города:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мощный Мусумба", callback_data="gorod1")],
        [InlineKeyboardButton(text="Слабый Луба", callback_data="gorod2")],
        [InlineKeyboardButton(text="Мусумбаград-на-Конго", callback_data="gorod3")]
    ]))
    await state.set_state(PassCreate.town)


@router.callback_query(F.data.startswith("gorod"))
async def get_town(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    town_map = {
        "gorod1": "Мощный Мусумба",
        "gorod2": "Слабый Луба",
        "gorod3": "Мусумбаград-на-Конго"
    }
    data = await state.get_data()
    data["town"] = town_map.get(callback.data, "Неизвестно")

    await create_user(
        session=session,
        user_id=callback.from_user.id,
        data=data,
        first_name=callback.from_user.full_name,
        username=callback.from_user.username
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]
        ]
    )
    await callback.message.answer("✅ Паспорт создан!", reply_markup=keyboard)
    await state.clear()
    user = await session.get(User, callback.from_user.id)
    print(user)

@router.message(F.text == "/passport")
async def show_passport(message: Message, session: AsyncSession):
    user = await get_user(session, message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай паспорт через /start")
        return

    # Форматируем дату (если created_at есть в модели)
    arrival_date = user.created_at.strftime("%d.%m.%Y") if hasattr(user, 'created_at') else "не указана"

    # Формируем текст паспорта
    passport_text = (
        "📄 Твой паспорт:\n"
        f"👤 Никнейм: {user.nickname}\n"
        f"📛 Имя: {user.full_name}\n"
        f"🎖 Ранг: {user.rank}\n"
        f"🏘 Город: {user.town}\n"
        f"📅 Дата прибытия: {arrival_date}\n"
        f"🎖 Награды: {', '.join(user.awards) if user.awards else 'нет'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]
        ]
    )
    await message.answer(passport_text, reply_markup=keyboard)


@router.callback_query(F.data == "menu_passport")
async def passport_via_callback(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Сначала создай паспорт через /start", show_alert=True)
        return

    # Форматируем дату
    arrival_date = user.created_at.strftime("%d.%m.%Y") if hasattr(user, 'created_at') else "не указана"

    # Формируем текст паспорта
    passport_text = (
        "📄 Твой паспорт:\n"
        f"👤 Никнейм: {user.nickname}\n"
        f"📛 Имя: {user.full_name}\n"
        f"🎖 Ранг: {user.rank}\n"
        f"🏘 Город: {user.town}\n"
        f"📅 Дата прибытия: {arrival_date}\n"
        f"🎖 Награды: {', '.join(user.awards) if user.awards else 'нет'}"
    )

    # Клавиатура с кнопкой "Назад"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu")]
        ]
    )

    # Редактируем существующее сообщение вместо отправки нового
    await callback.message.answer(
        text=passport_text,
        reply_markup=keyboard
    )
    await callback.answer()  # Убираем "часики" на кнопке