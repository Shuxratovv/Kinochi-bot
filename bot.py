import asyncio
import html
import logging
import os

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ErrorEvent
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError

import database as db

# Render portni ko'rib tinchlanishi uchun soxta server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Serverni alohida oqimda ishga tushiramiz
threading.Thread(target=run_server, daemon=True).start()


# ==================================================
# ENVIRONMENT
# ==================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")


if not TOKEN:

    raise RuntimeError(
        "BOT_TOKEN .env faylida topilmadi."
    )


if not ADMIN_ID_RAW:

    raise RuntimeError(
        "ADMIN_ID .env faylida topilmadi."
    )


try:

    ADMIN_ID = int(ADMIN_ID_RAW)

except ValueError:

    raise RuntimeError(
        "ADMIN_ID raqam bo'lishi kerak."
    )


# ==================================================
# LOGGING
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


# ==================================================
# BOT
# ==================================================

bot = Bot(
    token=TOKEN
)

dp = Dispatcher()


# ==================================================
# FSM
# ==================================================

class AddMovieState(StatesGroup):

    waiting_for_title = State()
    waiting_for_code = State()


class EditMovieState(StatesGroup):

    waiting_for_title = State()


class EditCodeState(StatesGroup):

    waiting_for_code = State()


class AddEpisodeState(StatesGroup):

    waiting_for_episode_number = State()
    waiting_for_video = State()


class BulkEpisodeState(StatesGroup):

    waiting_for_video = State()


class UserSearchState(StatesGroup):

    waiting_for_query = State()


# ==================================================
# HELPERS
# ==================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


def safe_text(text):

    return html.escape(str(text))


# ==================================================
# USER MAIN KEYBOARD
# ==================================================

def user_main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔎 Kino izlash",
                    callback_data="user_search"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📚 Katalog",
                    callback_data="user_catalog"
                )
            ],

            [
                InlineKeyboardButton(
                    text="❤️ Sevimlilarim",
                    callback_data="user_favorites"
                )
            ]

        ]
    )


# ==================================================
# ADMIN KEYBOARD
# ==================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🎬 Kino qo'shish",
                    callback_data="admin_add_movie"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🎥 Qism qo'shish",
                    callback_data="admin_add_episode"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📥 Ommaviy yuklash",
                    callback_data="admin_bulk_upload"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📚 Kontent boshqaruvi",
                    callback_data="admin_content"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    text="❌ Yopish",
                    callback_data="admin_close"
                )
            ]

        ]
    )


# ==================================================
# CANCEL KEYBOARD
# ==================================================

def cancel_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="admin_cancel"
                )
            ]
        ]
    )


# ==================================================
# START
# ==================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext
):

    await state.clear()

    db.add_user(
        message.from_user.id
    )

    await message.answer(
        f"Assalomu alaykum, "
        f"<b>{safe_text(message.from_user.first_name)}</b>! 👋\n\n"

        "🎬 <b>KINOCHI BOT</b>\n\n"

        "Kino yoki serial topish uchun "
        "quyidagi menyudan foydalaning:",
        
        reply_markup=user_main_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# /COMMANDS
# ==================================================

@dp.message(Command("commands"))
async def commands_handler(
    message: Message
):

    await message.answer(
        "📋 <b>KINOCHI BOT BUYRUQLARI</b>\n\n"

        "/start — 🏠 Bosh menyu\n"
        "/search — 🔎 Kino izlash\n"
        "/commands — 📋 Buyruqlar\n"
        "/help — 🛠 Yordam\n"
        "/myid — 🆔 Telegram ID\n\n"

        "👨‍💻 /admin — Admin panel "
        "(faqat admin uchun)",

        parse_mode="HTML"
    )


# ==================================================
# /HELP
# ==================================================

@dp.message(Command("help"))
async def help_handler(
    message: Message
):

    await message.answer(
        "🛠 <b>YORDAM</b>\n\n"

        "🔎 <b>Kino izlash</b> — kino kodini yoki "
        "kino nomini qidirish.\n\n"

        "📚 <b>Katalog</b> — mavjud kinolarni ko'rish.\n\n"

        "❤️ <b>Sevimlilarim</b> — saqlangan kinolar.\n\n"

        "/commands — barcha buyruqlarni ko'rish.",

        parse_mode="HTML"
    )


# ==================================================
# /MYID
# ==================================================

@dp.message(Command("myid"))
async def my_id_handler(
    message: Message
):

    await message.answer(
        "🆔 <b>Sizning Telegram ID'ingiz:</b>\n\n"
        f"<code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


# ==================================================
# ADMIN COMMAND
# ==================================================

@dp.message(Command("admin"))
async def admin_command(
    message: Message,
    state: FSMContext
):

    await state.clear()

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Sizda admin huquqi yo'q."
        )

        return

    await message.answer(
        "👨‍💻 <b>ADMIN PANEL</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# USER SEARCH BUTTON
# ==================================================

@dp.callback_query(
    F.data == "user_search"
)
async def user_search_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        UserSearchState.waiting_for_query
    )

    await callback.message.edit_text(
        "🔎 <b>KINO IZLASH</b>\n\n"

        "Kino <b>kodi</b> yoki "
        "<b>nomini</b> yuboring.\n\n"

        "Masalan:\n"
        "<code>101</code>\n"
        "<code>Panjara ortida</code>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="user_search_cancel"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# USER SEARCH
# ==================================================

@dp.message(
    UserSearchState.waiting_for_query
)
async def user_search_handler(
    message: Message,
    state: FSMContext
):

    if not message.text:

        await message.answer(
            "⚠️ Kino kodi yoki nomini "
            "matn ko'rinishida yuboring."
        )

        return

    query = message.text.strip()

    if len(query) < 1:

        await message.answer(
            "⚠️ Qidiruv so'rovi bo'sh."
        )

        return

    # Avval CODE bo'yicha qidiramiz

    movie = db.get_movie_by_code(
        query
    )

    if movie:

        await state.clear()

        await show_movie_details(
            message,
            movie[0],
            message.from_user.id
        )

        return

    # Keyin NOM bo'yicha qidiramiz

    results = db.search_movies(
        query
    )

    await state.clear()

    if not results:

        await message.answer(
            "😔 <b>Kino topilmadi.</b>\n\n"

            f"🔎 Qidirilgan: "
            f"<code>{safe_text(query)}</code>\n\n"

            "Kino kodini yoki nomini "
            "boshqacha yozib ko'ring.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔎 Qayta qidirish",
                            callback_data="user_search"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 Bosh menyu",
                            callback_data="user_home"
                        )
                    ]
                ]
            ),

            parse_mode="HTML"
        )

        return

    buttons = []

    for movie_id, title, code in results:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"movie:{movie_id}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔎 Yangi qidiruv",
                callback_data="user_search"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🏠 Bosh menyu",
                callback_data="user_home"
            )
        ]
    )

    await message.answer(
        "🔎 <b>QIDIRUV NATIJALARI</b>\n\n"

        f"📌 So'rov: "
        f"<i>{safe_text(query)}</i>\n\n"

        "Kerakli kinoni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )


# ==================================================
# DIRECT SEARCH
# ==================================================

@dp.message(
    F.text &
    ~F.text.startswith("/")
)
async def direct_search(
    message: Message
):

    query = message.text.strip()

    if not query:
        return

    movie = db.get_movie_by_code(
        query
    )

    if movie:

        await show_movie_details(
            message,
            movie[0],
            message.from_user.id
        )

        return

    results = db.search_movies(
        query
    )

    if not results:
        return

    buttons = []

    for movie_id, title, code in results:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"movie:{movie_id}"
                )
            ]
        )

    await message.answer(
        "🔎 <b>QIDIRUV NATIJALARI</b>\n\n"
        f"📌 So'rov: <i>{safe_text(query)}</i>\n\n"
        "Kerakli kinoni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )


# ==================================================
# SEARCH COMMAND
# ==================================================

@dp.message(Command("search"))
async def search_command(
    message: Message,
    state: FSMContext
):

    await state.set_state(
        UserSearchState.waiting_for_query
    )

    await message.answer(
        "🔎 <b>KINO IZLASH</b>\n\n"

        "Kino kodi yoki nomini yuboring.\n\n"

        "Masalan:\n"
        "<code>101</code>\n"
        "<code>Panjara ortida</code>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="user_search_cancel"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )


# ==================================================
# SEARCH CANCEL
# ==================================================

@dp.callback_query(
    F.data == "user_search_cancel"
)
async def user_search_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "🏠 <b>BOSH MENYU</b>\n\n"
        "Qidiruv bekor qilindi.",

        reply_markup=user_main_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# USER HOME
# ==================================================

@dp.callback_query(
    F.data == "user_home"
)
async def user_home(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "🏠 <b>BOSH MENYU</b>\n\n"
        "Kerakli bo'limni tanlang:",

        reply_markup=user_main_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# SHOW MOVIE DETAILS
# ==================================================

async def show_movie_details(
    target,
    movie_id,
    user_id
):

    movie = db.get_movie(
        movie_id
    )

    if not movie:
        return

    title = movie[1]
    code = movie[2]

    seasons = db.get_seasons(
        movie_id
    )

    favorite = db.is_favorite(
        user_id,
        movie_id
    )

    favorite_button = InlineKeyboardButton(
        text=(
            "💔 Sevimlilardan olib tashlash"
            if favorite
            else
            "❤️ Sevimlilarga qo'shish"
        ),

        callback_data=(
            f"favorite_remove:{movie_id}"
            if favorite
            else
            f"favorite_add:{movie_id}"
        )
    )

    if not seasons:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[

                [favorite_button],

                [
                    InlineKeyboardButton(
                        text="🏠 Bosh menyu",
                        callback_data="user_home"
                    )
                ]

            ]
        )

        text = (
            f"🎬 <b>{safe_text(title)}</b>\n"
            f"🔑 Kod: <code>{safe_text(code)}</code>\n\n"
            "⚠️ Hali qismlar yuklanmagan."
        )

    else:

        season_buttons = []

        for season in seasons:

            season_buttons.append(
                InlineKeyboardButton(
                    text=f"📺 {season}-fasl",
                    callback_data=(
                        f"season:{movie_id}:{season}"
                    )
                )
            )

        rows = []

        for i in range(
            0,
            len(season_buttons),
            2
        ):

            rows.append(
                season_buttons[i:i + 2]
            )

        rows.append(
            [favorite_button]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text="🏠 Bosh menyu",
                    callback_data="user_home"
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=rows
        )

        text = (
            f"🎬 <b>{safe_text(title)}</b>\n"
            f"🔑 Kod: <code>{safe_text(code)}</code>\n\n"
            "📺 <b>Faslni tanlang:</b>"
        )

    if isinstance(target, Message):

        await target.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    else:

        await target.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


# ==================================================
# MOVIE CALLBACK
# ==================================================

@dp.callback_query(
    F.data.startswith("movie:")
)
async def movie_callback(
    callback: CallbackQuery
):

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await show_movie_details(
        callback,
        movie_id,
        callback.from_user.id
    )

    await callback.answer()


# ==================================================
# SEASON
# ==================================================

@dp.callback_query(
    F.data.startswith("season:")
)
async def season_callback(
    callback: CallbackQuery
):

    try:

        parts = callback.data.split(":")

        if len(parts) != 3:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Fasl ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    episodes = db.get_episodes(
        movie_id,
        season
    )

    if not episodes:

        await callback.answer(
            "❌ Bu faslda qismlar yo'q.",
            show_alert=True
        )

        return

    buttons = []

    for episode in episodes:

        buttons.append(
            InlineKeyboardButton(
                text=f"▶️ {episode}",
                callback_data=(
                    f"episode:"
                    f"{movie_id}:"
                    f"{season}:"
                    f"{episode}"
                )
            )
        )

    rows = []

    for i in range(
        0,
        len(buttons),
        4
    ):

        rows.append(
            buttons[i:i + 4]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 Fasllar",
                callback_data=f"movie:{movie_id}"
            )
        ]
    )

    await callback.message.edit_text(
        f"🎬 <b>{safe_text(movie[1])}</b>\n"
        f"📺 <b>{season}-fasl</b>\n\n"
        "🔢 <b>Qismni tanlang:</b>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# EPISODE
# ==================================================

@dp.callback_query(
    F.data.startswith("episode:")
)
async def episode_callback(
    callback: CallbackQuery
):

    try:

        parts = callback.data.split(":")

        if len(parts) != 4:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])
        episode = int(parts[3])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Qism ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    file_id = db.get_episode(
        movie_id,
        season,
        episode
    )

    if not file_id:

        await callback.answer(
            "❌ Video topilmadi.",
            show_alert=True
        )

        return

    episodes = db.get_episodes(
        movie_id,
        season
    )

    if episode not in episodes:

        await callback.answer(
            "❌ Qism mavjud emas.",
            show_alert=True
        )

        return

    current_index = episodes.index(
        episode
    )

    previous_episode = (
        episodes[current_index - 1]
        if current_index > 0
        else None
    )

    next_episode = (
        episodes[current_index + 1]
        if current_index < len(episodes) - 1
        else None
    )

    await callback.answer(
        "🎥 Video tayyorlanmoqda..."
    )

    try:

        await callback.message.answer_video(
            video=file_id,

            caption=(
                f"🎬 <b>{safe_text(movie[1])}</b>\n"
                f"📺 {season}-fasl\n"
                f"🔢 {episode}-qism"
            ),

            parse_mode="HTML"
        )

    except TelegramAPIError:

        logger.exception(
            "Video yuborishda xatolik."
        )

        await callback.message.answer(
            "❌ Videoni yuborishda xatolik yuz berdi."
        )

        return

    navigation = []

    if previous_episode is not None:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=(
                    f"episode:"
                    f"{movie_id}:"
                    f"{season}:"
                    f"{previous_episode}"
                )
            )
        )

    if next_episode is not None:

        navigation.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=(
                    f"episode:"
                    f"{movie_id}:"
                    f"{season}:"
                    f"{next_episode}"
                )
            )
        )

    rows = []

    if navigation:

        rows.append(
            navigation
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 Qismlar",
                callback_data=(
                    f"season:"
                    f"{movie_id}:"
                    f"{season}"
                )
            ),

            InlineKeyboardButton(
                text="🏠 Bosh menyu",
                callback_data="user_home"
            )
        ]
    )

    await callback.message.answer(
        "⬇️ <b>Keyingi amal:</b>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),

        parse_mode="HTML"
    )


# ==================================================
# FAVORITE ADD
# ==================================================

@dp.callback_query(
    F.data.startswith("favorite_add:")
)
async def favorite_add_callback(
    callback: CallbackQuery
):

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ID noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    if not db.add_favorite(
        callback.from_user.id,
        movie_id
    ):

        await callback.answer(
            "❌ Sevimliga qo'shishda xatolik.",
            show_alert=True
        )

        return

    await callback.answer(
        "❤️ Sevimlilarga qo'shildi!"
    )

    await show_movie_details(
        callback,
        movie_id,
        callback.from_user.id
    )


# ==================================================
# FAVORITE REMOVE
# ==================================================

@dp.callback_query(
    F.data.startswith("favorite_remove:")
)
async def favorite_remove_callback(
    callback: CallbackQuery
):

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ID noto'g'ri.",
            show_alert=True
        )

        return

    db.remove_favorite(
        callback.from_user.id,
        movie_id
    )

    await callback.answer(
        "💔 Sevimlilardan olib tashlandi."
    )

    await show_movie_details(
        callback,
        movie_id,
        callback.from_user.id
    )


# ==================================================
# FAVORITES
# ==================================================

def favorites_keyboard(
    movies
):

    buttons = []

    for movie_id, title, code in movies:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"movie:{movie_id}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🏠 Bosh menyu",
                callback_data="user_home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


@dp.callback_query(
    F.data == "user_favorites"
)
async def user_favorites_callback(
    callback: CallbackQuery
):

    movies = db.get_favorites(
        callback.from_user.id
    )

    if not movies:

        await callback.message.edit_text(
            "❤️ <b>SEVIMLILARIM</b>\n\n"
            "Hozircha sevimlilarga kino qo'shilmagan.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔎 Kino izlash",
                            callback_data="user_search"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="📚 Katalog",
                            callback_data="user_catalog"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 Bosh menyu",
                            callback_data="user_home"
                        )
                    ]
                ]
            ),

            parse_mode="HTML"
        )

        await callback.answer()

        return

    await callback.message.edit_text(
        "❤️ <b>SEVIMLILARIM</b>\n\n"
        f"🎬 Kinolar: <b>{len(movies)}</b>\n\n"
        "Kerakli kinoni tanlang:",

        reply_markup=favorites_keyboard(
            movies
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# CATALOG
# ==================================================

CATALOG_PAGE_SIZE = 10


def catalog_keyboard(
    movies,
    page
):

    total_pages = (
        (
            len(movies)
            + CATALOG_PAGE_SIZE
            - 1
        )
        // CATALOG_PAGE_SIZE
    )

    start = page * CATALOG_PAGE_SIZE
    end = start + CATALOG_PAGE_SIZE

    page_movies = movies[
        start:end
    ]

    buttons = []

    for movie_id, title, code in page_movies:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"movie:{movie_id}"
                )
            ]
        )

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=(
                    f"catalog_page:{page - 1}"
                )
            )
        )

    navigation.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="catalog_current_page"
        )
    )

    if page < total_pages - 1:

        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=(
                    f"catalog_page:{page + 1}"
                )
            )
        )

    buttons.append(
        navigation
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🏠 Bosh menyu",
                callback_data="user_home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def catalog_text(
    movies,
    page
):

    total_pages = (
        (
            len(movies)
            + CATALOG_PAGE_SIZE
            - 1
        )
        // CATALOG_PAGE_SIZE
    )

    return (
        "📚 <b>KATALOG</b>\n\n"
        f"🎬 Jami kinolar: <b>{len(movies)}</b>\n\n"
        "Kerakli kinoni tanlang:\n\n"
        f"📄 Sahifa: "
        f"<b>{page + 1}/{total_pages}</b>"
    )


@dp.callback_query(
    F.data == "user_catalog"
)
async def user_catalog_callback(
    callback: CallbackQuery
):

    movies = db.get_all_movies()

    if not movies:

        await callback.message.edit_text(
            "📚 <b>KATALOG</b>\n\n"
            "Hozircha katalogda kino yo'q.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🏠 Bosh menyu",
                            callback_data="user_home"
                        )
                    ]
                ]
            ),

            parse_mode="HTML"
        )

        await callback.answer()

        return

    await callback.message.edit_text(
        catalog_text(
            movies,
            0
        ),

        reply_markup=catalog_keyboard(
            movies,
            0
        ),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("catalog_page:")
)
async def catalog_page_callback(
    callback: CallbackQuery
):

    try:

        page = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Sahifa noto'g'ri.",
            show_alert=True
        )

        return

    movies = db.get_all_movies()

    if not movies:

        await callback.answer(
            "📚 Katalog bo'sh.",
            show_alert=True
        )

        return

    total_pages = (
        (
            len(movies)
            + CATALOG_PAGE_SIZE
            - 1
        )
        // CATALOG_PAGE_SIZE
    )

    page = max(
        0,
        min(
            page,
            total_pages - 1
        )
    )

    await callback.message.edit_text(
        catalog_text(
            movies,
            page
        ),

        reply_markup=catalog_keyboard(
            movies,
            page
        ),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "catalog_current_page"
)
async def catalog_current_page(
    callback: CallbackQuery
):

    await callback.answer(
        "📄 Siz hozir shu sahifadasiz."
    )


# ==================================================
# ADMIN ADD MOVIE
# ==================================================

@dp.callback_query(
    F.data == "admin_add_movie"
)
async def admin_add_movie(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    await state.set_state(
        AddMovieState.waiting_for_title
    )

    await callback.message.edit_text(
        "🎬 <b>KINO QO'SHISH</b>\n\n"
        "Kino nomini yuboring.",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN MOVIE TITLE
# ==================================================

@dp.message(
    AddMovieState.waiting_for_title
)
async def receive_movie_title(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    if not message.text:

        await message.answer(
            "⚠️ Kino nomini matn ko'rinishida yuboring."
        )

        return

    title = message.text.strip()

    if len(title) < 2:

        await message.answer(
            "⚠️ Kino nomi juda qisqa."
        )

        return

    await state.update_data(
        title=title
    )

    await state.set_state(
        AddMovieState.waiting_for_code
    )

    await message.answer(
        "🔑 <b>KINO KODI</b>\n\n"
        "Kino uchun unikal kod yuboring.\n\n"
        "Masalan:\n"
        "<code>101</code>",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# ADMIN MOVIE CODE
# ==================================================

@dp.message(
    AddMovieState.waiting_for_code
)
async def receive_movie_code(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    if not message.text:

        await message.answer(
            "⚠️ Kodni matn ko'rinishida yuboring."
        )

        return

    code = message.text.strip()

    if len(code) < 1:

        await message.answer(
            "⚠️ Kod bo'sh bo'lishi mumkin emas."
        )

        return

    data = await state.get_data()

    movie_id = db.add_movie(
        data["title"],
        code
    )

    if movie_id is None:

        await message.answer(
            "❌ Bu kod allaqachon band.\n\n"
            "Boshqa kod yuboring."
        )

        return

    await state.clear()

    await message.answer(
        "✅ <b>KINO SAQLANDI!</b>\n\n"

        f"🎬 {safe_text(data['title'])}\n"
        f"🔑 Kod: <code>{safe_text(code)}</code>\n"
        f"🆔 ID: <code>{movie_id}</code>",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# ADMIN ADD EPISODE
# ==================================================

@dp.callback_query(
    F.data == "admin_add_episode"
)
async def admin_add_episode(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movies = db.get_all_movies()

    if not movies:

        await callback.message.edit_text(
            "❌ Bazada hali kino yo'q.\n\n"
            "Avval kino qo'shing.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Admin panel",
                            callback_data="admin_back"
                        )
                    ]
                ]
            )
        )

        await callback.answer()

        return

    buttons = []

    for movie_id, title, code in movies:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"admin_movie:{movie_id}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Admin panel",
                callback_data="admin_back"
            )
        ]
    )

    await callback.message.edit_text(
        "🎥 <b>QISM QO'SHISH</b>\n\n"
        "🎬 Kinoni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN MOVIE SELECTED
# ==================================================

@dp.callback_query(
    F.data.startswith("admin_movie:")
)
async def admin_movie_selected(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ID noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    seasons = db.get_seasons(
        movie_id
    )

    buttons = []

    for season in seasons:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📺 {season}-fasl",
                    callback_data=(
                        f"admin_season:"
                        f"{movie_id}:"
                        f"{season}"
                    )
                )
            ]
        )

    next_season = (
        max(seasons) + 1
        if seasons
        else 1
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text=f"➕ {next_season}-fasl",
                callback_data=(
                    f"admin_newseason:"
                    f"{movie_id}:"
                    f"{next_season}"
                )
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data="admin_add_episode"
            )
        ]
    )

    await callback.message.edit_text(
        f"🎬 <b>{safe_text(movie[1])}</b>\n\n"
        "📺 <b>Faslni tanlang:</b>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN NEW SEASON
# ==================================================

@dp.callback_query(
    F.data.startswith("admin_newseason:")
)
async def admin_new_season(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        parts = callback.data.split(":")

        if len(parts) != 3:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])

        if movie_id < 1 or season < 1:
            raise ValueError

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Fasl ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await state.update_data(
        movie_id=movie_id,
        season=season
    )

    await state.set_state(
        AddEpisodeState.waiting_for_episode_number
    )

    await callback.message.edit_text(
        f"🎬 <b>{safe_text(movie[1])}</b>\n"
        f"📺 <b>{season}-fasl</b>\n\n"

        "🔢 Qism raqamini yuboring.\n\n"
        "Masalan:\n"
        "<code>1</code>",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN EXISTING SEASON
# ==================================================

@dp.callback_query(
    F.data.startswith("admin_season:")
)
async def admin_season_selected(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        parts = callback.data.split(":")

        if len(parts) != 3:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Fasl ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    episodes = db.get_episodes(
        movie_id,
        season
    )

    next_episode = (
        max(episodes) + 1
        if episodes
        else 1
    )

    text = (
        f"🎬 <b>{safe_text(movie[1])}</b>\n"
        f"📺 <b>{season}-fasl</b>\n\n"
    )

    if episodes:

        text += "🔢 <b>Mavjud qismlar:</b>\n\n"

        text += "\n".join(
            f"▶️ {ep}-qism"
            for ep in episodes
        )

        text += "\n\n"

    else:

        text += (
            "ℹ️ Bu faslda hali qism yo'q.\n\n"
        )

    buttons = [

        [
            InlineKeyboardButton(
                text=f"➕ {next_episode}-qism qo'shish",
                callback_data=(
                    f"admin_addpart:"
                    f"{movie_id}:"
                    f"{season}:"
                    f"{next_episode}"
                )
            )
        ]

    ]

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data=f"admin_movie:{movie_id}"
            )
        ]
    )

    await callback.message.edit_text(
        text + "Yangi qism qo'shish:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN EPISODE NUMBER
# ==================================================

@dp.message(
    AddEpisodeState.waiting_for_episode_number
)
async def receive_episode_number(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    if not message.text:

        await message.answer(
            "⚠️ Qism raqamini yuboring."
        )

        return

    if not message.text.strip().isdigit():

        await message.answer(
            "❌ Faqat raqam kiriting.\n\n"
            "Masalan: <code>5</code>",
            parse_mode="HTML"
        )

        return

    episode = int(
        message.text.strip()
    )

    if episode < 1:

        await message.answer(
            "❌ Qism raqami 1 yoki undan katta bo'lishi kerak."
        )

        return

    data = await state.get_data()

    movie_id = data.get(
        "movie_id"
    )

    season = data.get(
        "season"
    )

    if not movie_id or not season:

        await state.clear()

        await message.answer(
            "❌ Sessiya ma'lumoti yo'qoldi.\n\n"
            "Qaytadan boshlang."
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await state.clear()

        await message.answer(
            "❌ Kino topilmadi."
        )

        return

    await state.update_data(
        episode=episode
    )

    await state.set_state(
        AddEpisodeState.waiting_for_video
    )

    await message.answer(
        "🎥 <b>VIDEONI YUBORING</b>\n\n"

        f"🎬 Kino: <b>{safe_text(movie[1])}</b>\n"
        f"📺 Fasl: <b>{season}</b>\n"
        f"🔢 Qism: <b>{episode}</b>",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# ADMIN EPISODE VIDEO
# ==================================================

@dp.message(
    AddEpisodeState.waiting_for_video,
    F.video
)
async def receive_video(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    data = await state.get_data()

    movie_id = data.get(
        "movie_id"
    )

    season = data.get(
        "season"
    )

    episode = data.get(
        "episode"
    )

    if not movie_id or not season or not episode:

        await state.clear()

        await message.answer(
            "❌ Video qo'shish sessiyasi buzilgan."
        )

        return

    success = db.add_episode(
        movie_id,
        season,
        episode,
        message.video.file_id
    )

    if not success:

        await message.answer(
            "❌ Video saqlashda xatolik."
        )

        return

    movie = db.get_movie(
        movie_id
    )

    await state.clear()

    await message.answer(
        "✅ <b>VIDEO SAQLANDI!</b>\n\n"

        f"🎬 {safe_text(movie[1])}\n"
        f"📺 {season}-fasl\n"
        f"🔢 {episode}-qism",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# ADMIN ADD PART DIRECTLY
# ==================================================

@dp.callback_query(
    F.data.startswith("admin_addpart:")
)
async def admin_add_part(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        parts = callback.data.split(":")

        if len(parts) != 4:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])
        episode = int(parts[3])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Qism ma'lumoti noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await state.update_data(
        movie_id=movie_id,
        season=season,
        episode=episode
    )

    await state.set_state(
        AddEpisodeState.waiting_for_video
    )

    await callback.message.edit_text(
        "🎥 <b>VIDEONI YUBORING</b>\n\n"

        f"🎬 Kino: <b>{safe_text(movie[1])}</b>\n"
        f"📺 Fasl: <b>{season}</b>\n"
        f"🔢 Qism: <b>{episode}</b>",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN BULK UPLOAD
# ==================================================

@dp.callback_query(
    F.data == "admin_bulk_upload"
)
async def admin_bulk_upload(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movies = db.get_all_movies()

    if not movies:

        await callback.message.edit_text(
            "❌ Bazada kino yo'q.\n\n"
            "Avval kino qo'shing.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Admin panel",
                            callback_data="admin_back"
                        )
                    ]
                ]
            )
        )

        await callback.answer()

        return

    buttons = []

    for movie_id, title, code in movies:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=f"bulk_movie:{movie_id}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Admin panel",
                callback_data="admin_back"
            )
        ]
    )

    await callback.message.edit_text(
        "📥 <b>OMMAVIY YUKLASH</b>\n\n"
        "🎬 Kinoni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# BULK MOVIE
# ==================================================

@dp.callback_query(
    F.data.startswith("bulk_movie:")
)
async def bulk_movie_selected(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ID noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    seasons = db.get_seasons(
        movie_id
    )

    next_season = (
        max(seasons) + 1
        if seasons
        else 1
    )

    buttons = []

    for season in seasons:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📺 {season}-faslga yuklash",
                    callback_data=(
                        f"bulk_go:"
                        f"{movie_id}:"
                        f"{season}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text=f"➕ Yangi {next_season}-fasl",
                callback_data=(
                    f"bulk_go:"
                    f"{movie_id}:"
                    f"{next_season}"
                )
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data="admin_bulk_upload"
            )
        ]
    )

    await callback.message.edit_text(
        f"🎬 <b>{safe_text(movie[1])}</b>\n\n"
        "📺 Qaysi faslga yuklamoqchisiz?",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# BULK GO
# ==================================================

@dp.callback_query(
    F.data.startswith("bulk_go:")
)
async def bulk_go(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        parts = callback.data.split(":")

        if len(parts) != 3:
            raise ValueError

        movie_id = int(parts[1])
        season = int(parts[2])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Ma'lumot noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    episodes = db.get_episodes(
        movie_id,
        season
    )

    next_episode = (
        max(episodes) + 1
        if episodes
        else 1
    )

    await state.update_data(
        movie_id=movie_id,
        season=season,
        episode=next_episode
    )

    await state.set_state(
        BulkEpisodeState.waiting_for_video
    )

    await callback.message.edit_text(
        "📥 <b>OMMAVIY YUKLASH REJIMI</b>\n\n"

        f"🎬 Kino: <b>{safe_text(movie[1])}</b>\n"
        f"📺 Fasl: <b>{season}</b>\n"
        f"🔢 Navbatdagi qism: <b>{next_episode}</b>\n\n"

        "🎥 Endi videolarni ketma-ket yuboravering.\n\n"

        "Har bir video avtomatik ravishda "
        "keyingi qismga saqlanadi.\n\n"

        "Masalan:\n"
        "1-video → 1-qism\n"
        "2-video → 2-qism\n"
        "3-video → 3-qism",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛑 To'xtatish",
                        callback_data="bulk_stop"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# BULK VIDEO
# ==================================================

@dp.message(
    BulkEpisodeState.waiting_for_video
)
async def bulk_video(
    message: Message,
    state: FSMContext
):
    """Ommaviy yuklash: har bir video avtomatik keyingi qismga yoziladi."""

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()

    movie_id = data.get("movie_id")
    season = data.get("season")
    episode = data.get("episode")

    if not movie_id or not season or not episode:
        await state.clear()
        await message.answer(
            "❌ Ommaviy yuklash sessiyasi buzilgan.\n\n"
            "Qaytadan boshlang.",
            reply_markup=admin_keyboard()
        )
        return

    # Oddiy Telegram video.
    file_id = None
    if message.video:
        file_id = message.video.file_id

    # Telegram videoni File/Document sifatida yuborsa ham qabul qilamiz.
    elif message.document:
        mime_type = (message.document.mime_type or "").lower()
        if mime_type.startswith("video/"):
            file_id = message.document.file_id

    if not file_id:
        await message.answer(
            "⚠️ Bu xabar video sifatida qabul qilinmadi.\n\n"
            "🎥 Videoni oddiy video qilib yuboring yoki 'File' sifatida yuborsangiz,\n"
            "video fayl ekaniga ishonch hosil qiling.\n\n"
            f"Hozir kutilayotgan qism: <b>{episode}-qism</b>",
            parse_mode="HTML"
        )
        return

    success = db.add_episode(
        movie_id,
        season,
        episode,
        file_id
    )

    if not success:
        # Xatoda qism raqami oshirilmaydi — shu qismga qayta uriniladi.
        await message.answer(
            "❌ <b>VIDEO SAQLANMADI</b>\n\n"
            f"🎬 Kino ID: <code>{movie_id}</code>\n"
            f"📺 {season}-fasl\n"
            f"🔢 {episode}-qism\n\n"
            "⚠️ Qism raqami o'zgartirilmadi.\n"
            "Videoni qayta yuboring yoki yuklashni to'xtating.",
            parse_mode="HTML"
        )
        return

    next_episode = episode + 1

    await state.update_data(
        episode=next_episode
    )

    await message.answer(
        "✅ <b>SAQLANDI!</b>\n\n"
        f"📺 {season}-fasl\n"
        f"🔢 {episode}-qism\n\n"
        f"➡️ Keyingi video: <b>{next_episode}-qism</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛑 To'xtatish",
                        callback_data="bulk_stop"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )



# ==================================================
# BULK STOP
# ==================================================

@dp.callback_query(
    F.data == "bulk_stop"
)
async def bulk_stop(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    await state.clear()

    await callback.message.edit_text(
        "🛑 <b>OMMAVIY YUKLASH TO'XTATILDI.</b>\n\n"
        "Admin panelga qaytishingiz mumkin.",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN CONTENT
# ==================================================

@dp.callback_query(
    F.data == "admin_content"
)
async def admin_content(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movies = db.get_all_movies()

    if not movies:

        await callback.message.edit_text(
            "📚 <b>KONTENT BOSHQARUVI</b>\n\n"
            "Hozircha kino yo'q.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Admin panel",
                            callback_data="admin_back"
                        )
                    ]
                ]
            ),

            parse_mode="HTML"
        )

        await callback.answer()

        return

    buttons = []

    for movie_id, title, code in movies:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title} [{code}]",
                    callback_data=(
                        f"content_movie:{movie_id}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Admin panel",
                callback_data="admin_back"
            )
        ]
    )

    await callback.message.edit_text(
        "📚 <b>KONTENT BOSHQARUVI</b>\n\n"
        "Tahrirlash yoki o'chirish uchun "
        "kinoni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# CONTENT MOVIE
# ==================================================

@dp.callback_query(
    F.data.startswith("content_movie:")
)
async def content_movie(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        movie_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Kino ID noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    seasons = db.get_seasons(
        movie_id
    )

    episode_count = sum(
        len(
            db.get_episodes(
                movie_id,
                season
            )
        )
        for season in seasons
    )

    await callback.message.edit_text(
        "📚 <b>KONTENT</b>\n\n"

        f"🎬 <b>{safe_text(movie[1])}</b>\n"
        f"🔑 Kod: <code>{safe_text(movie[2])}</code>\n"
        f"🆔 ID: <code>{movie[0]}</code>\n"
        f"📺 Fasllar: <b>{len(seasons)}</b>\n"
        f"🎥 Qismlar: <b>{episode_count}</b>\n\n"

        "Kerakli amalni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="✏️ Nomini tahrirlash",
                        callback_data=(
                            f"edit_movie:{movie_id}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔑 Kodni tahrirlash",
                        callback_data=(
                            f"edit_code:{movie_id}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🗑 Kino o'chirish",
                        callback_data=(
                            f"delete_movie:{movie_id}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="📺 Fasllarni boshqarish",
                        callback_data=(
                            f"manage_seasons:{movie_id}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔙 Orqaga",
                        callback_data="admin_content"
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# EDIT MOVIE
# ==================================================

@dp.callback_query(
    F.data.startswith("edit_movie:")
)
async def edit_movie(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movie_id = int(
        callback.data.split(":")[1]
    )

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await state.update_data(
        movie_id=movie_id
    )

    await state.set_state(
        EditMovieState.waiting_for_title
    )

    await callback.message.edit_text(
        "✏️ <b>KINO NOMINI TAHRIRLASH</b>\n\n"

        f"Eski nom:\n"
        f"<b>{safe_text(movie[1])}</b>\n\n"

        "Yangi nomni yuboring:",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(
    EditMovieState.waiting_for_title
)
async def receive_new_movie_title(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    if not message.text:

        await message.answer(
            "⚠️ Yangi nomni yuboring."
        )

        return

    new_title = message.text.strip()

    data = await state.get_data()

    movie_id = data.get(
        "movie_id"
    )

    if not movie_id:

        await state.clear()

        return

    success = db.update_movie_title(
        movie_id,
        new_title
    )

    await state.clear()

    if success:

        await message.answer(
            "✅ <b>KINO NOMI YANGILANDI!</b>\n\n"
            f"🎬 Yangi nom: "
            f"<b>{safe_text(new_title)}</b>",

            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )

    else:

        await message.answer(
            "❌ Kino nomini yangilashda xatolik.",
            reply_markup=admin_keyboard()
        )


# ==================================================
# EDIT CODE
# ==================================================

@dp.callback_query(
    F.data.startswith("edit_code:")
)
async def edit_code(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movie_id = int(
        callback.data.split(":")[1]
    )

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await state.update_data(
        movie_id=movie_id
    )

    await state.set_state(
        EditCodeState.waiting_for_code
    )

    await callback.message.edit_text(
        "🔑 <b>KODNI TAHRIRLASH</b>\n\n"

        f"Eski kod:\n"
        f"<code>{safe_text(movie[2])}</code>\n\n"

        "Yangi kodni yuboring:",

        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(
    EditCodeState.waiting_for_code
)
async def receive_new_code(
    message: Message,
    state: FSMContext
):

    if not is_admin(
        message.from_user.id
    ):

        await state.clear()

        return

    if not message.text:

        await message.answer(
            "⚠️ Yangi kodni yuboring."
        )

        return

    new_code = message.text.strip()

    data = await state.get_data()

    movie_id = data.get(
        "movie_id"
    )

    if not movie_id:

        await state.clear()

        return

    success = db.update_movie_code(
        movie_id,
        new_code
    )

    if not success:

        await message.answer(
            "❌ Bu kod allaqachon band.\n\n"
            "Boshqa kod yuboring."
        )

        return

    await state.clear()

    await message.answer(
        "✅ <b>KINO KODI YANGILANDI!</b>\n\n"
        f"🔑 Yangi kod: <code>{safe_text(new_code)}</code>",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# ==================================================
# DELETE MOVIE CONFIRMATION
# ==================================================

@dp.callback_query(
    F.data.startswith("delete_movie:")
)
async def delete_movie_confirmation(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movie_id = int(
        callback.data.split(":")[1]
    )

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "⚠️ <b>KINONI O'CHIRISH</b>\n\n"

        f"🎬 <b>{safe_text(movie[1])}</b>\n"
        f"🔑 Kod: <code>{safe_text(movie[2])}</code>\n\n"

        "❗ Bu amal kino bilan birga "
        "uning barcha fasl va qismlarini ham "
        "o'chiradi.\n\n"

        "Haqiqatan ham o'chirmoqchimisiz?",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🗑 HA, O'CHIRISH",
                        callback_data=(
                            f"confirm_delete_movie:"
                            f"{movie_id}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data=(
                            f"content_movie:{movie_id}"
                        )
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# DELETE MOVIE
# ==================================================

@dp.callback_query(
    F.data.startswith("confirm_delete_movie:")
)
async def confirm_delete_movie(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movie_id = int(
        callback.data.split(":")[1]
    )

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    success = db.delete_movie(
        movie_id
    )

    if not success:

        await callback.answer(
            "❌ Kino o'chirilmadi.",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        "🗑 <b>KINO O'CHIRILDI</b>\n\n"
        f"🎬 {safe_text(movie[1])}\n"
        f"🔑 Kod: <code>{safe_text(movie[2])}</code>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Kontent boshqaruvi",
                        callback_data="admin_content"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👨‍💻 Admin panel",
                        callback_data="admin_back"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer(
        "🗑 Kino o'chirildi."
    )


# ==================================================
# MANAGE SEASONS
# ==================================================

@dp.callback_query(
    F.data.startswith("manage_seasons:")
)
async def manage_seasons(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    movie_id = int(
        callback.data.split(":")[1]
    )

    movie = db.get_movie(
        movie_id
    )

    if not movie:

        await callback.answer(
            "❌ Kino topilmadi.",
            show_alert=True
        )

        return

    seasons = db.get_seasons(
        movie_id
    )

    buttons = []

    for season in seasons:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📺 {season}-fasl",
                    callback_data=(
                        f"manage_season:"
                        f"{movie_id}:"
                        f"{season}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data=(
                    f"content_movie:{movie_id}"
                )
            )
        ]
    )

    await callback.message.edit_text(
        f"📺 <b>FASLLARNI BOSHQARISH</b>\n\n"
        f"🎬 {safe_text(movie[1])}\n\n"
        "Faslni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# MANAGE SINGLE SEASON
# ==================================================

@dp.callback_query(
    F.data.startswith("manage_season:")
)
async def manage_single_season(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    try:

        parts = callback.data.split(":")

        movie_id = int(parts[1])
        season = int(parts[2])

    except (
        ValueError,
        IndexError,
        AttributeError
    ):

        await callback.answer(
            "❌ Ma'lumot noto'g'ri.",
            show_alert=True
        )

        return

    movie = db.get_movie(
        movie_id
    )

    if not movie:
        return

    episodes = db.get_episodes(
        movie_id,
        season
    )

    buttons = []

    for episode in episodes:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎥 {episode}-qism",
                    callback_data=(
                        f"delete_episode:"
                        f"{movie_id}:"
                        f"{season}:"
                        f"{episode}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🗑 Butun faslni o'chirish",
                callback_data=(
                    f"delete_season:"
                    f"{movie_id}:"
                    f"{season}"
                )
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Fasllar",
                callback_data=(
                    f"manage_seasons:{movie_id}"
                )
            )
        ]
    )

    await callback.message.edit_text(
        f"📺 <b>{season}-FASL</b>\n\n"
        f"🎬 {safe_text(movie[1])}\n\n"
        f"🎥 Qismlar: <b>{len(episodes)}</b>\n\n"
        "O'chirish uchun qismni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# DELETE EPISODE CONFIRM
# ==================================================

@dp.callback_query(
    F.data.startswith("delete_episode:")
)
async def delete_episode_confirmation(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    parts = callback.data.split(":")

    movie_id = int(parts[1])
    season = int(parts[2])
    episode = int(parts[3])

    await callback.message.edit_text(
        "⚠️ <b>QISMNI O'CHIRISH</b>\n\n"
        f"📺 {season}-fasl\n"
        f"🎥 {episode}-qism\n\n"
        "Haqiqatan ham o'chirmoqchimisiz?",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🗑 O'chirish",
                        callback_data=(
                            f"confirm_delete_episode:"
                            f"{movie_id}:"
                            f"{season}:"
                            f"{episode}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data=(
                            f"manage_season:"
                            f"{movie_id}:"
                            f"{season}"
                        )
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# DELETE EPISODE
# ==================================================

@dp.callback_query(
    F.data.startswith("confirm_delete_episode:")
)
async def confirm_delete_episode(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    parts = callback.data.split(":")

    movie_id = int(parts[1])
    season = int(parts[2])
    episode = int(parts[3])

    success = db.delete_episode(
        movie_id,
        season,
        episode
    )

    if success:

        await callback.answer(
            "🗑 Qism o'chirildi."
        )

    else:

        await callback.answer(
            "❌ Qism topilmadi.",
            show_alert=True
        )

        return

    await manage_single_season(
        callback
    )


# ==================================================
# DELETE SEASON CONFIRM
# ==================================================

@dp.callback_query(
    F.data.startswith("delete_season:")
)
async def delete_season_confirmation(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    parts = callback.data.split(":")

    movie_id = int(parts[1])
    season = int(parts[2])

    await callback.message.edit_text(
        "⚠️ <b>FASLNI O'CHIRISH</b>\n\n"

        f"📺 {season}-fasl\n\n"

        "❗ Bu fasldagi barcha qismlar "
        "o'chiriladi.\n\n"

        "Haqiqatan ham o'chirmoqchimisiz?",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🗑 HA, O'CHIRISH",
                        callback_data=(
                            f"confirm_delete_season:"
                            f"{movie_id}:"
                            f"{season}"
                        )
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data=(
                            f"manage_season:"
                            f"{movie_id}:"
                            f"{season}"
                        )
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# DELETE SEASON
# ==================================================

@dp.callback_query(
    F.data.startswith("confirm_delete_season:")
)
async def confirm_delete_season(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    parts = callback.data.split(":")

    movie_id = int(parts[1])
    season = int(parts[2])

    success = db.delete_season(
        movie_id,
        season
    )

    if not success:

        await callback.answer(
            "❌ Fasl topilmadi.",
            show_alert=True
        )

        return

    await callback.answer(
        "🗑 Fasl o'chirildi."
    )

    await manage_seasons(
        callback
    )


# ==================================================
# ADMIN STATS
# ==================================================

@dp.callback_query(
    F.data == "admin_stats"
)
async def admin_stats(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    users, movies, episodes = db.get_statistics()

    favorites = db.get_favorite_count()

    await callback.message.edit_text(
        "📊 <b>KINOCHI BOT — STATISTIKA</b>\n\n"

        "👥 <b>FOYDALANUVCHILAR</b>\n"
        f"└ 👤 A'zolar: <b>{users}</b>\n\n"

        "🎬 <b>KONTENT</b>\n"
        f"├ 🎬 Kinolar: <b>{movies}</b>\n"
        f"└ 🎥 Qismlar: <b>{episodes}</b>\n\n"

        "❤️ <b>FAOLLİK</b>\n"
        f"└ ❤️ Sevimlilar: <b>{favorites}</b>\n\n"

        "🤖 <b>TIZIM</b>\n"
        "└ 🟢 Bot faol",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🔄 Yangilash",
                        callback_data="admin_stats"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔙 Admin panel",
                        callback_data="admin_back"
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN BACK
# ==================================================

@dp.callback_query(
    F.data == "admin_back"
)
async def admin_back(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    await state.clear()

    await callback.message.edit_text(
        "👨‍💻 <b>ADMIN PANEL</b>\n\n"
        "Kerakli amalni tanlang:",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN CANCEL
# ==================================================

@dp.callback_query(
    F.data == "admin_cancel"
)
async def admin_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    await state.clear()

    await callback.message.edit_text(
        "❌ Amal bekor qilindi.\n\n"
        "👨‍💻 <b>ADMIN PANEL</b>",

        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ==================================================
# ADMIN CLOSE
# ==================================================

@dp.callback_query(
    F.data == "admin_close"
)
async def admin_close(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo'q.",
            show_alert=True
        )

        return

    await state.clear()

    try:

        await callback.message.delete()

    except TelegramAPIError:

        await callback.message.edit_text(
            "👨‍💻 Admin panel yopildi."
        )

    await callback.answer()


# ==================================================
# BOT COMMANDS
# ==================================================

async def set_main_menu():

    commands = [

        BotCommand(
            command="start",
            description="Bosh menyu"
        ),

        BotCommand(
            command="search",
            description="Kino izlash"
        ),

        BotCommand(
            command="commands",
            description="Buyruqlar"
        ),

        BotCommand(
            command="help",
            description="Yordam"
        ),

        BotCommand(
            command="myid",
            description="Telegram ID"
        ),

        BotCommand(
            command="admin",
            description="Admin panel"
        )

    ]

    await bot.set_my_commands(
        commands
    )

@dp.callback_query()
async def debug_callback(callback: CallbackQuery):

    logger.warning(
        "UNHANDLED CALLBACK DATA: %r",
        callback.data
    )

    await callback.answer(
        "⚠️ Test: callback handler topilmadi.",
        show_alert=True
    )



# ==================================================
# GLOBAL ERROR HANDLER
# ==================================================

@dp.error()
async def global_error_handler(
    event: ErrorEvent
):

    logger.error(
        "BOTDA KUTILMAGAN XATOLIK: %s",
        event.exception,
        exc_info=True
    )

    try:

        if event.update.message:

            await event.update.message.answer(
                "⚠️ <b>Kutilmagan xatolik yuz berdi.</b>\n\n"
                "Bot ishlashda davom etmoqda. "
                "Iltimos, birozdan keyin qayta urinib ko'ring.",

                parse_mode="HTML"
            )

        elif event.update.callback_query:

            try:

                await event.update.callback_query.answer(
                    "⚠️ Xatolik yuz berdi. "
                    "Qayta urinib ko'ring.",
                    show_alert=True
                )

            except TelegramAPIError:
                pass

    except Exception:

        logger.exception(
            "Global error handlerning o'zida xatolik."
        )


# ==================================================
# MAIN
# ==================================================

async def main():

    try:

        # DATABASE

        db.create_database()

        # TELEGRAM COMMANDS

        await set_main_menu()

        logger.info(
            "================================"
        )

        logger.info(
            "🎬 KINOCHI BOT ISHGA TUSHDI"
        )

        logger.info(
            "🗄 Database tayyor"
        )

        logger.info(
            "🔎 Qidiruv tizimi tayyor"
        )

        logger.info(
            "📚 Katalog tayyor"
        )

        logger.info(
            "❤️ Sevimlilar tayyor"
        )

        logger.info(
            "🎥 Yakka video yuklash tayyor"
        )

        logger.info(
            "📥 Ommaviy yuklash tayyor"
        )

        logger.info(
            "📚 Kontent boshqaruvi tayyor"
        )

        logger.info(
            "📊 Statistika tayyor"
        )

        logger.info(
            "📋 Telegram commands tayyor"
        )

        logger.info(
            "🛡️ Xatoliklarni boshqarish tayyor"
        )

        logger.info(
            "🤖 Bot ishlayapti"
        )

        logger.info(
            "================================"
        )

        await dp.start_polling(
            bot
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot foydalanuvchi tomonidan to'xtatildi."
        )

    except Exception:

        logger.critical(
            "BOT ISHGA TUSHISHIDA KRITIK XATOLIK.",
            exc_info=True
        )

        raise

    finally:

        await bot.session.close()


# ==================================================
# START
# ==================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )