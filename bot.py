# Установка библиотеки для бота
!pip install -q aiogram

import json
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

TOKEN = "9231798465:AAHTtexH01jpRYyRJNYQLeqNFM41Or0Ds4k"
CONFIG_FILE = "bot_config.json"

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
        "⚙️ **Панель управления редиректом**\n\n"
        "Команды для настройки:\n"
        "• `/status` — показать текущие настройки\n"
        "• `/set_sources @chan1 @chan2 @chan3` — задать каналы-источники\n"
        "• `/set_target @navigatorRR4` — задать целевой канал\n\n"
        "💡 *Бот очищает рекламный подвал снизу и добавляет ваш тег наверх.*"
    )
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    config = load_config()
    sources = config.get("sources", [])
    target = config.get("target", "@navigatorRR4")
    
    sources_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sources)]) if sources else "Список пуст"
    text = (
        "📋 **Текущие настройки:**\n\n"
        f"**Каналы-источники (до 5 шт):**\n{sources_str}\n\n"
        f"**Целевой канал:**\n{target}"
    )
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("set_sources"))
async def cmd_set_sources(message: Message):
    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ Укажите каналы через пробел.\nПример: `/set_sources @chan1 @chan2 @chan3`", parse_mode="Markdown")
        return
    
    if len(args) > 5:
        await message.reply("❌ Можно указать не более 5 каналов-источников!")
        return

    config = load_config()
    config["sources"] = args
    save_config(config)
    
    sources_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(args)])
    await message.reply(f"✅ **Источники обновлены ({len(args)}/5):**\n{sources_str}", parse_mode="Markdown")

@dp.message(Command("set_target"))
async def cmd_set_target(message: Message):
    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ Укажите целевой канал.\nПример: `/set_target @navigatorRR4`", parse_mode="Markdown")
        return
    
    target = args[0]
    config = load_config()
    config["target"] = target
    save_config(config)
    
    await message.reply(f"✅ **Целевой канал обновлен на:** {target}", parse_mode="Markdown")

def clean_and_format_text(text: str = "", target: str = "@navigatorRR4") -> str:
    if not text:
        return target

    # Списки фраз и ссылок из подвала, которые нужно полностью стирать
    footers_to_remove = [
        r'Предложить пост.*',
        r'Поиск по водоёмам.*',
        r'Барахолка.*',
        r'Наши соцсети:.*',
        r'Твич:.*',
        r'Ютуб:.*',
        r'Телеграм:.*',
        r'Предложить пост, рекламу или розыгрыш:.*',
        r'Ищешь конкретную рыбу.*',
        r'Авторынок Астраханской области.*',
        r'Список Авторынков ЮГА.*',
        r'Разместить своё авто.*'
    ]

    for pattern in footers_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    # Заменяем случайные чужие упоминания на target
    text = re.sub(r'(?<!#)\B@[A-Za-z0-9_]+', target, text)

    text = text.strip()

    # Добавляем ваш тег сразу после первого хэштега вверху
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

print("🚀 Финальный бот запущен без ошибок!")
await dp.start_polling(bot)
