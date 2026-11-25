import asyncio
import html
import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN va ADMIN_ID muhit o'zgaruvchilarini kiriting!")

router = Router()

ADMIN_MSG_TO_USER: dict[int, int] = {}
USER_LANG: dict[int, str] = {}
USER_TOPIC: dict[int, str] = {}
UID_PATTERN = re.compile(r"#uid_(\d+)")

# Tugma matnlari
BTN_TECH_UZ = "🛠 Texnik muammo"
BTN_REPORT_UZ = "🚨 E'lon / Shikoyat"
BTN_CARGO_UZ = "🤝 Hamkorlik / Cargo"
BTN_FAQ_UZ = "❓ Ko'p so'raladigan savollar"
BTN_LANG_UZ = "🌐 Tilni o'zgartirish"

BTN_TECH_RU = "🛠 Техническая проблема"
BTN_REPORT_RU = "🚨 Объявление / Жалоба"
BTN_CARGO_RU = "🤝 Сотрудничество / Карго"
BTN_FAQ_RU = "❓ Частые вопросы (FAQ)"
BTN_LANG_RU = "🌐 Сменить язык"

TOPIC_BUTTONS = {
    BTN_TECH_UZ: ("uz", "Texnik muammo"),
    BTN_REPORT_UZ: ("uz", "E'lon / Shikoyat"),
    BTN_CARGO_UZ: ("uz", "Hamkorlik / Cargo"),
    BTN_TECH_RU: ("ru", "Техническая проблема"),
    BTN_REPORT_RU: ("ru", "Объявление / Жалоба"),
    BTN_CARGO_RU: ("ru", "Сотрудничество / Карго"),
}

FAQ_DATA = {
    "uz": [
        (
            "faq_post",
            "📦 Qanday qilib e'lon joylash mumkin?",
            "<b>📦 E'lon joylash tartibi:</b>\n\n"
            "Ilovaning pastki markazidagi olovrang <b>«+»</b> tugmasini bosing, "
            "<i>Yuk</i>, <i>Mashina</i> yoki <i>Cargo</i> turini tanlang va yo'nalish hamda "
            "aloqa raqamingizni kiriting. E'lon darhol jonli bozorda chiqadi.",
        ),
        (
            "faq_tg",
            "✈️ Telegram yuklari bilan qanday bog'laniladi?",
            "<b>✈️ Telegram e'lonlari:</b>\n\n"
            "Ko'k <b>Telegram</b> belgili yuklar logistika guruhlaridan avtomatik yig'iladi. "
            "Ular bilan ilova chatida emas, <b>Raqamni ko'rish</b> (qo'ng'iroq) yoki "
            "<b>Telegram</b> tugmasi orqali to'g'ridan-to'g'ri bog'lanishingiz mumkin.",
        ),
        (
            "faq_price",
            "💳 Ilovadan foydalanish pullikmi?",
            "<b>💳 Narxlar:</b>\n\n"
            "Hozirda Humo Logistics ilovasida e'lon joylash, yuk qidirish va raqamlarni "
            "ko'rish <b>mutlaqo bepul</b>.",
        ),
        (
            "faq_cargo",
            "🚛 Cargo kompaniyamni katalogga qanday qo'shaman?",
            "<b>🚛 Cargo katalogiga qo'shilish:</b>\n\n"
            "Menyudan <b>«🤝 Hamkorlik / Cargo»</b> tugmasini bosib, kompaniya nomi, "
            "yo'nalishlari (Xitoy, Turkiya, Dubay va b.), tarifi hamda telefon raqamingizni "
            "yuboring — adminlarimiz tekshirib tasdiqlangan belgi bilan qo'shib berishadi.",
        ),
    ],
    "ru": [
        (
            "faq_post",
            "📦 Как разместить объявление?",
            "<b>📦 Размещение объявления:</b>\n\n"
            "Нажмите оранжевую кнопку <b>«+»</b> внизу по центру приложения, выберите тип "
            "(<i>Груз</i>, <i>Машина</i> или <i>Карго</i>), укажите маршрут и контактный номер. "
            "Объявление сразу появится в ленте.",
        ),
        (
            "faq_tg",
            "✈️ Как связаться по грузам из Telegram?",
            "<b>✈️ Объявления из Telegram:</b>\n\n"
            "Грузы с синей меткой <b>Telegram</b> собираются из логистических групп. "
            "Связывайтесь с автором через кнопку <b>Показать номер</b> (звонок) или "
            "напрямую в <b>Telegram</b>.",
        ),
        (
            "faq_price",
            "💳 Приложение платное?",
            "<b>💳 Стоимость:</b>\n\n"
            "Сейчас размещение объявлений, поиск грузов и просмотр контактов в "
            "Humo Logistics <b>полностью бесплатны</b>.",
        ),
        (
            "faq_cargo",
            "🚛 Как добавить Карго-компанию в каталог?",
            "<b>🚛 Добавление в каталог Карго:</b>\n\n"
            "Нажмите <b>«🤝 Сотрудничество / Карго»</b> и отправьте название компании, "
            "направления, тарифы и контакты — администратор проверит и добавит вас в каталог.",
        ),
    ],
}


def get_lang(user_id: int) -> str:
    return USER_LANG.get(user_id, "uz")


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            ]
        ]
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ru":
        rows = [
            [KeyboardButton(text=BTN_TECH_RU), KeyboardButton(text=BTN_REPORT_RU)],
            [KeyboardButton(text=BTN_CARGO_RU), KeyboardButton(text=BTN_FAQ_RU)],
            [KeyboardButton(text=BTN_LANG_RU)],
        ]
        placeholder = "Выберите раздел или напишите сообщение..."
    else:
        rows = [
            [KeyboardButton(text=BTN_TECH_UZ), KeyboardButton(text=BTN_REPORT_UZ)],
            [KeyboardButton(text=BTN_CARGO_UZ), KeyboardButton(text=BTN_FAQ_UZ)],
            [KeyboardButton(text=BTN_LANG_UZ)],
        ]
        placeholder = "Bo'limni tanlang yoki xabar yozing..."

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def faq_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=f"faq:{lang}:{key}")]
        for key, title, _ in FAQ_DATA[lang]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def welcome_text(lang: str) -> str:
    if lang == "ru":
        return (
            "🔥 <b>Humo Logistics — Служба поддержки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Здравствуйте! Чем мы можем помочь?\n\n"
            "Выберите нужную тему кнопками ниже или сразу напишите ваш вопрос "
            "(можно прикрепить скриншот). Оператор ответит в ближайшее время."
        )
    return (
        "🔥 <b>Humo Logistics — Qo'llab-quvvatlash xizmati</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Assalomu alaykum! Sizga qanday yordam bera olamiz?\n\n"
        "Pastdagi tugmalardan kerakli mavzuni tanlang yoki savolingizni to'g'ridan-to'g'ri "
        "yozib yuboring (skrinshot ham jo'natishingiz mumkin). Operatorlarimiz tez orada javob berishadi."
    )


def format_user_header(message: Message) -> str:
    user = message.from_user
    full_name = html.escape(user.full_name or "Foydalanuvchi")
    username = f"@{html.escape(user.username)}" if user.username else "username yo'q"
    topic = html.escape(USER_TOPIC.get(user.id, "Umumiy murojaat"))
    lang_badge = "🇷🇺 RU" if get_lang(user.id) == "ru" else "🇺🇿 UZ"
    return (
        f"🔥 <b>HUMO SUPPORT | Yangi murojaat</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 <b>Mavzu:</b> {topic}\n"
        f"👤 <b>Foydalanuvchi:</b> {full_name} ({username})\n"
        f"🌐 <b>Til:</b> {lang_badge}  |  🆔 #uid_{user.id}"
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🔥 <b>Humo Logistics Support — Admin paneli faol</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Foydalanuvchilardan kelgan har qanday murojaatga oddiy <b>Reply</b> qilib javob yozing — "
            "bot matn, rasm yoki ovozli xabaringizni foydalanuvchiga yetkazadi."
        )
        return

    if message.from_user.id not in USER_LANG:
        await message.answer(
            "🔥 <b>Humo Logistics Support</b>\n\n"
            "🇺🇿 Muloqot tilini tanlang:\n"
            "🇷🇺 Выберите язык общения:",
            reply_markup=lang_keyboard(),
        )
    else:
        lang = get_lang(message.from_user.id)
        await message.answer(welcome_text(lang), reply_markup=main_menu_keyboard(lang))


@router.message(Command("lang"))
@router.message(F.text.in_({BTN_LANG_UZ, BTN_LANG_RU}))
async def cmd_lang(message: Message):
    await message.answer(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=lang_keyboard(),
    )


@router.message(Command("faq"))
@router.message(F.text.in_({BTN_FAQ_UZ, BTN_FAQ_RU}))
async def cmd_faq(message: Message):
    lang = "ru" if message.text == BTN_FAQ_RU else get_lang(message.from_user.id)
    title = (
        "❓ <b>Часто задаваемые вопросы:</b>\nВыберите интересующий пункт:"
        if lang == "ru"
        else "❓ <b>Ko'p so'raladigan savollar:</b>\nKerakli savolni tanlang:"
    )
    await message.answer(title, reply_markup=faq_keyboard(lang))


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    USER_LANG[callback.from_user.id] = lang
    await callback.answer("Til tanlandi ✅" if lang == "uz" else "Язык выбран ✅")
    await callback.message.delete()
    await callback.message.answer(
        welcome_text(lang),
        reply_markup=main_menu_keyboard(lang),
    )


@router.callback_query(F.data.startswith("faq:"))
async def cb_faq_item(callback: CallbackQuery):
    _, lang, key = callback.data.split(":")
    answer_text = ""
    for item_key, _, body in FAQ_DATA.get(lang, FAQ_DATA["uz"]):
        if item_key == key:
            answer_text = body
            break
    if answer_text:
        await callback.message.answer(answer_text)
    await callback.answer()


# Admin javob berganda (Reply)
@router.message(F.from_user.id == ADMIN_ID)
async def handle_admin_reply(message: Message, bot: Bot):
    if not message.reply_to_message:
        await message.answer(
            "ℹ️ Foydalanuvchiga javob yuborish uchun uning murojaat xabariga <b>Reply</b> qiling."
        )
        return

    replied = message.reply_to_message
    target_user_id = ADMIN_MSG_TO_USER.get(replied.message_id)

    if not target_user_id:
        source_text = replied.text or replied.caption or ""
        match = UID_PATTERN.search(source_text)
        if match:
            target_user_id = int(match.group(1))

    if not target_user_id:
        await message.answer("❌ Foydalanuvchi ID'si topilmadi. Murojaat sarlavhasiga Reply qiling.")
        return

    try:
        if message.text:
            user_lang = get_lang(target_user_id)
            prefix = (
                "💬 <b>Ответ оператора Humo Logistics:</b>\n\n"
                if user_lang == "ru"
                else "💬 <b>Humo Logistics operatori javobi:</b>\n\n"
            )
            await bot.send_message(
                chat_id=target_user_id,
                text=f"{prefix}{html.escape(message.text)}",
            )
        else:
            await bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
        await message.answer("✅ Javob foydalanuvchiga yuborildi.")
    except Exception as e:
        logger.error("Javob yuborishda xato: %s", e)
        await message.answer(
            f"❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin):\n<code>{html.escape(str(e))}</code>"
        )


# Foydalanuvchi menyudan mavzu tanlaganda
@router.message(F.text.in_(set(TOPIC_BUTTONS.keys())))
async def handle_topic_selection(message: Message):
    lang, topic = TOPIC_BUTTONS[message.text]
    USER_LANG[message.from_user.id] = lang
    USER_TOPIC[message.from_user.id] = topic

    if lang == "ru":
        await message.answer(
            f"📂 Раздел: <b>{html.escape(topic)}</b>\n\n"
            "Опишите ваш вопрос подробно (можно отправить фото/скриншот) — "
            "сообщение сразу поступит оператору."
        )
    else:
        await message.answer(
            f"📂 Bo'lim: <b>{html.escape(topic)}</b>\n\n"
            "Muammo yoki taklifingizni batafsil yozib yuboring (rasm/skrinshot ham "
            "qo'shishingiz mumkin) — xabaringiz darhol operatorga yetkaziladi."
        )


# Foydalanuvchi murojaat yuborganda
@router.message()
async def handle_user_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    header = format_user_header(message)

    try:
        if message.text:
            sent = await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{header}\n\n💬 {html.escape(message.text)}",
            )
            ADMIN_MSG_TO_USER[sent.message_id] = user_id
        else:
            caption_text = header
            if message.caption:
                caption_text += f"\n\n💬 {html.escape(message.caption)}"

            if message.photo or message.video or message.document:
                sent = await bot.copy_message(
                    chat_id=ADMIN_ID,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=caption_text[:1024],
                    parse_mode=ParseMode.HTML,
                )
                ADMIN_MSG_TO_USER[sent.message_id] = user_id
            else:
                info_msg = await bot.send_message(chat_id=ADMIN_ID, text=header)
                media_msg = await bot.copy_message(
                    chat_id=ADMIN_ID,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )
                ADMIN_MSG_TO_USER[info_msg.message_id] = user_id
                ADMIN_MSG_TO_USER[media_msg.message_id] = user_id

        confirm = (
            "✅ <b>Ваше обращение принято!</b>\nОператор Humo Logistics ответит вам в ближайшее время."
            if lang == "ru"
            else "✅ <b>Murojaatingiz qabul qilindi!</b>\nHumo Logistics operatori tez orada shu yerda javob beradi."
        )
        await message.answer(confirm, reply_markup=main_menu_keyboard(lang))
    except Exception as e:
        logger.error("Adminga uzatishda xato: %s", e)
        err = (
            "⚠️ Временная ошибка при отправке. Попробуйте чуть позже."
            if lang == "ru"
            else "⚠️ Xabar yuborishda vaqtinchalik xatolik yuz berdi. Birozdan so'ng urinib ko'ring."
        )
        await message.answer(err)


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="Humo Support Bot OK"))
    app.router.add_get("/health", lambda _: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server %s portda ishga tushdi", port)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await start_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Humo Support Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
