import json
import re
import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = "9231798465:AAHTtexH01jpRYyRJNYQLeqNFM41Or0Ds4k"
CONFIG_FILE = "bot_config.json"

# Настройки вебхука для Render
PORT = int(os.environ.get("PORT", 8080))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"sources": [], "target": "@navigatorRR4"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

bot = Bot(token=TOKEN)
dp = Dispatcher()
media_groups = {}

@dp.message(Command("start"))
@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "⚙️ **Панель управления редиректом (Webhook)**\n\n"
        "Команды для настройки:\n"
        "• `/status` — текущие настройки\n"
        "• `/set_sources @chan1 @chan2` — каналы-источники\n"
        "• `/set_target @navigatorRR4` — целевой канал\n\n"
        "💡 *Работает через вебхуки 24/7!*"
    )
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    config = load_config()
    sources = config.get("sources", [])
    target = config.get("target", "@navigatorRR4")
    sources_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sources)]) if sources else "Список пуст"
    text = f"📋 **Текущие настройки:**\n\n**Источники:**\n{sources_str}\n\n**Цель:**\n{target}"
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("set_sources"))
async def cmd_set_sources(message: Message):
    args = message.text.split()[1:]
    if not args or len(args) > 5:
        await message.reply("❌ Укажите от 1 до 5 каналов через пробел.")
        return
    config = load_config()
    config["sources"] = args
    save_config(config)
    await message.reply(f"✅ Источники обновлены: {args}")

@dp.message(Command("set_target"))
async def cmd_set_target(message: Message):
    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ Укажите целевой канал.")
        return
    config = load_config()
    config["target"] = args[0]
    save_config(config)
    await message.reply(f"✅ Цель обновлена: {args[0]}")

def clean_and_format_text(text: str = "", target: str = "@navigatorRR4") -> str:
    if not text:
        return target
    footers_to_remove = [
        r'Предложить пост.*', r'Поиск по водоёмам.*', r'Барахолка.*',
        r'Наши соцсети:.*', r'Твич:.*', r'Ютуб:.*', r'Телеграм:.*',
        r'Предложить пост, рекламу или розыгрыш:.*', r'Ищешь конкретную рыбу.*',
        r'Авторынок Астраханской области.*', r'Список Авторынков ЮГА.*', r'Разместить своё авто.*'
    ]
    for pattern in footers_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    text = re.sub(r'(?<!#)\B@[A-Za-z0-9_]+', target, text)
    text = text.strip()

    match = re.search(r'(#[А-Яа-яA-Za-z0-9_]+)', text)
    if match:
        first_tag = match.group(1)
        if target not in text:
            text = text.replace(first_tag, f"{first_tag} {target}", 1)
    else:
        if target not in text:
            text = f"{target}\n{text}"
    return text

@dp.channel_post()
async def handle_channel_post(post: Message):
    config = load_config()
    sources = [s.lower().replace("@", "") for s in config.get("sources", [])]
    target = config.get("target", "@navigatorRR4")
    
    if not post.chat.username or post.chat.username.lower() not in sources:
        return

    if post.media_group_id:
        mg_id = post.media_group_id
        if mg_id not in media_groups:
            media_groups[mg_id] = []
            asyncio.create_task(process_media_group(mg_id, target))
        media_groups[mg_id].append(post)
    else:
        raw_text = post.caption or post.text or ""
        new_caption = clean_and_format_text(raw_text, target)
        if post.caption:
            await post.copy_to(chat_id=target, caption=new_caption)
        elif post.text:
            await bot.send_message(chat_id=target, text=new_caption)
        else:
            await post.copy_to(chat_id=target, caption=target)

async def process_media_group(mg_id: str, target: str):
    await asyncio.sleep(2)
    posts = media_groups.pop(mg_id, [])
    if not posts:
        return
    caption = ""
    for p in posts:
        if p.caption:
            caption = clean_and_format_text(p.caption, target)
            break
    if not caption:
        caption = target

    await bot.copy_messages(
        chat_id=target,
        from_chat_id=posts[0].chat.id,
        message_ids=[p.message_id for p in posts],
        caption=caption
    )

async def on_startup(bot: Bot) -> None:
    if RENDER_EXTERNAL_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Вебхук установлен: {WEBHOOK_URL}")
    else:
        logging.warning("RENDER_EXTERNAL_URL не задан в переменных окружения!")

def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    dp.startup.register(on_startup)
    
    setup_application(app, dp, bot=bot)
    
    web.run_app(app, port=PORT)

if __name__ == "__main__":
    main()
