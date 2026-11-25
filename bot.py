import asyncio
import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip())

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN va ADMIN_ID muhit o'zgaruvchilarini kiriting!")

router = Router()

# Render qayta ishga tushmaguncha xabar ID -> user_id bog'lanishini saqlaydi
# (qayta ishga tushsa ham matn/caption ichidagi #uid_... orqali javob ishlayveradi)
ADMIN_MSG_TO_USER: dict[int, int] = {}
UID_PATTERN = re.compile(r"#uid_(\d+)")


def format_user_tag(message: Message) -> str:
    user = message.from_user
    full_name = user.full_name or "Foydalanuvchi"
    username = f"@{user.username}" if user.username else "username yo'q"
    return f"👤 <b>{full_name}</b> ({username})\n🆔 #uid_{user.id}"


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👋 <b>Humo Support Admin rejimi faol.</b>\n\n"
            "Foydalanuvchilardan kelgan istalgan xabarga <b>Reply</b> qilib javob yozing — "
            "bot javobingizni foydalanuvchiga yetkazadi."
        )
        return

    await message.answer(
        "👋 Assalomu alaykum! <b>Humo Logistics</b> qo'llab-quvvatlash xizmatiga xush kelibsiz.\n\n"
        "Savolingiz, texnik muammo yoki taklifingizni shu yerga yozib qoldiring "
        "(skrinshot ham yuborishingiz mumkin). Operatorlarimiz tez orada javob berishadi.\n\n"
        "🇷🇺 <i>Здравствуйте! Напишите ваш вопрос или отправьте скриншот — оператор скоро ответит.</i>"
    )


# 1. Admin foydalanuvchi xabariga Reply qilganda
@router.message(F.from_user.id == ADMIN_ID)
async def handle_admin_reply(message: Message, bot: Bot):
    if not message.reply_to_message:
        await message.answer("ℹ️ Foydalanuvchiga javob yuborish uchun uning xabariga <b>Reply</b> qiling.")
        return

    replied = message.reply_to_message
    target_user_id = ADMIN_MSG_TO_USER.get(replied.message_id)

    if not target_user_id:
        source_text = replied.text or replied.caption or ""
        match = UID_PATTERN.search(source_text)
        if match:
            target_user_id = int(match.group(1))

    if not target_user_id:
        await message.answer("❌ Foydalanuvchi ID'si topilmadi. Xabar sarlavhasiga Reply qiling.")
        return

    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer("✅ Javob foydalanuvchiga yuborildi.")
    except Exception as e:
        logger.error("Javob yuborishda xato: %s", e)
        await message.answer(f"❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin):\n<code>{e}</code>")


# 2. Oddiy foydalanuvchi xabar yuborganda
@router.message()
async def handle_user_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    header = format_user_tag(message)

    try:
        if message.text:
            sent = await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 <b>Yangi murojaat</b>\n{header}\n\n💬 {message.text}",
            )
            ADMIN_MSG_TO_USER[sent.message_id] = user_id
        else:
            # Rasm, video, hujjat, ovozli xabarlar uchun
            caption_text = f"📩 <b>Yangi murojaat</b>\n{header}"
            if message.caption:
                caption_text += f"\n\n💬 {message.caption}"

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
                info_msg = await bot.send_message(chat_id=ADMIN_ID, text=f"📩 <b>Yangi murojaat</b>\n{header}")
                media_msg = await bot.copy_message(
                    chat_id=ADMIN_ID,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )
                ADMIN_MSG_TO_USER[info_msg.message_id] = user_id
                ADMIN_MSG_TO_USER[media_msg.message_id] = user_id

        await message.answer("✅ Murojaatingiz qabul qilindi. Tez orada javob beramiz.")
    except Exception as e:
        logger.error("Adminga uzatishda xato: %s", e)
        await message.answer("⚠️ Xabar yuborishda vaqtinchalik xatolik yuz berdi. Birozdan so'ng urinib ko'ring.")


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
