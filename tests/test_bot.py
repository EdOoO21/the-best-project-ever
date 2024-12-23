import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram.types import Message, Update
from aiogram import types

from src.db.models import User, UserStatus
from bot.routers.start import router
from bot.main import bot
from bot.main import dp

@pytest.mark.asyncio
async def test_cmd_start():
    """
    Тест на обработчик /start.
    Проверяем, что бот отправляет нужное приветствие.
    """
    with patch.object(bot, 'send_message', new=AsyncMock()) as mock_send:
        message = Message(
            message_id=1,
            date=None,
            chat=types.Chat(id=12345, type='private'),
            from_user=types.User(id=12345, is_bot=False, first_name="Tester"),
            text="/start",
        )
        update = Update(update_id=1, message=message)

        dp.include_router(router)
        await dp.feed_update(bot, update)

        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert args[0] == 12345, "Неверный chat_id"
        assert "Добро пожаловать" in args[1], "Не найдено приветствие"


@pytest.mark.asyncio
async def test_cb_set_alert():
    """
    Тест на колбэк 'set_alert'.
    Проверяем, что бот просит пользователя ввести город отбытия.
    """
    with patch.object(bot, 'send_message', new=AsyncMock()) as mock_send, \
         patch.object(bot, 'answer_callback_query', new=AsyncMock()) as mock_cb_answer:

        cb_query = CallbackQuery(
            id="xyz",
            from_user=types.User(id=12345, is_bot=False, first_name="Tester"),
            message=Message(
                message_id=10,
                date=None,
                chat=types.Chat(id=12345, type='private'),
                from_user=types.User(id=12345, is_bot=False, first_name="Tester"),
                text="some text",
            ),
            data="set_alert",
        )
        update = Update(update_id=100, callback_query=cb_query)

        dp.include_router(router)
        await dp.feed_update(bot, update)
        mock_cb_answer.assert_called_once()
        mock_send.assert_awaited()
        args, kwargs = mock_send.call_args
        assert "Введите город отбытия" in args[1]


@pytest.mark.asyncio
@patch("bot.routers.subscriptions.session")
async def test_subscribe_command_ok(mock_session):
    """Тест на команду /subscribe, если пользователь не заблокирован, должна создаться подписка."""
    fake_user = MagicMock()
    fake_user.user_id = 12345
    fake_user.status = UserStatus.chill
    mock_session.query.return_value.filter_by.return_value.first.return_value = fake_user

    with patch("bot.routers.subscriptions.add_subscription", new=MagicMock()) as mock_add_sub, \
         patch.object(bot, 'send_message', new=AsyncMock()) as mock_send:

        dp.include_router(subs_router)

        message = Message(
            message_id=1,
            date=None,
            chat=types.Chat(id=12345, type='private'),
            from_user=types.User(id=12345, is_bot=False, first_name="Tester"),
            text="/subscribe 777",
        )
        update = Update(update_id=1, message=message)

        await dp.feed_update(bot, update)

        # Проверяем, что add_subscription был вызван
        mock_add_sub.assert_called_once_with(12345, 777)

        # Проверяем, что bot.send_message() был вызван
        mock_send.assert_awaited()
        args, kwargs = mock_send.call_args
        assert args[0] == 12345
        assert "Подписка успешно оформлена" in args[1]

@pytest.mark.asyncio
@patch("bot.routers.subscriptions.session")
async def test_subscribe_command_banned(mock_session):
    """Тест на команду /subscribe, если пользователь заблокирован, должно вернуться 'Вы заблокированы'."""
    fake_user = MagicMock()
    fake_user.user_id = 12345
    fake_user.status = UserStatus.banned
    mock_session.query.return_value.filter_by.return_value.first.return_value = fake_user

    with patch.object(bot, 'send_message', new=AsyncMock()) as mock_send:
        dp.include_router(subs_router)

        message = Message(
            message_id=1,
            date=None,
            chat=types.Chat(id=12345, type='private'),
            from_user=types.User(id=12345, is_bot=False, first_name="Tester"),
            text="/subscribe 777",
        )
        update = Update(update_id=2, message=message)

        await dp.feed_update(bot, update)

        mock_send.assert_awaited()
        args, kwargs = mock_send.call_args
        assert "Вы заблокированы." in args[1]