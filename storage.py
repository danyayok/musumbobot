from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User

async def create_user(session: AsyncSession, user_id: int, data: dict, first_name: str, username: str = None):
    user = User(
        telegram_id=user_id,
        full_name=first_name,
        username=username,
        nickname=data['nickname'],
        rank=data['rank'],
        town=data['town'],
        awards=[],
        durdom=0,
        approve_work=1,
        news_svo=False,
        news_zhizhn=False,
        is_made=True,
        chudjo=0
    )
    session.add(user)
    await session.commit()
    return user

async def get_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    return result.scalar()

async def update_news_sub(session: AsyncSession, user_id: int, news_type: str, value: bool):
    await session.execute(
        update(User)
        .where(User.telegram_id == user_id)
        .values(**{f"news_{news_type}": value})
    )
    await session.commit()

async def get_all_users(session: AsyncSession):
    result = await session.execute(select(User))
    return {user.telegram_id: user for user in result.scalars()}

async def add_medal(session: AsyncSession, user_id: int, medal: str):
    user = await get_user(session, user_id)
    if medal not in user.awards:
        user.awards.append(medal)
        await session.commit()
    return user

async def remove_medal(session: AsyncSession, user_id: int, medal: str):
    user = await get_user(session, user_id)
    if medal in user.awards:
        user.awards.remove(medal)
        await session.commit()
    return user