import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
OWNER_ID = int(os.getenv('OWNER_ID'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
db_instance = None

class TelegramDB:
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.cache = {}

    async def save(self, key, data):
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            await self.bot.send_message(chat_id=self.channel_id, text=f"DB_{key}: {json_data}")
            self.cache[key] = data
            return True
        except Exception as e:
            logger.error(f"خطا: {e}")
            return False

    async def get(self, key):
        return self.cache.get(key)

    async def get_all_data(self):
        return {
            'teams': await self.get('teams') or [],
            'players': await self.get('players') or [],
            'matches': await self.get('matches') or [],
            'transfers': await self.get('transfers') or [],
            'news': await self.get('news') or [],
            'lineups': await self.get('lineups') or []
        }

def get_db():
    return db_instance

@app.route('/')
def home():
    return '🤖 ربات Zyron League فعال است!'

@app.route('/get_data', methods=['GET'])
async def get_data():
    db = get_db()
    if not db:
        return jsonify({'error': 'دیتابیس در دسترس نیست'}), 500
    data = await db.get_all_data()
    return jsonify(data)

@app.route('/save_data', methods=['POST'])
async def save_data():
    db = get_db()
    if not db:
        return jsonify({'error': 'دیتابیس در دسترس نیست'}), 500
    try:
        data = request.json
        for key, value in data.items():
            await db.save(key, value)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 سلام! به ربات Zyron League خوش اومدی. برای راهنما /help رو بزن.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 راهنما:\n/login [username] [password]\n/team_add [name] [level]\n/team_list\n/player_add [name] [team_id] [position] [overall]\n/player_list\n/standings")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("❌ فرمت: /login [username] [password]")
            return
        username, password = args[0], args[1]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            context.user_data['role'] = 'owner'
            await update.message.reply_text("✅ به عنوان مالک وارد شدی!")
            return
        await update.message.reply_text("❌ اشتباه است!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def team_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('role') != 'owner':
        await update.message.reply_text("❌ فقط مالک!")
        return
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("❌ فرمت: /team_add [name] [level]")
            return
        db = context.bot_data.get('db')
        teams = await db.get('teams') or []
        teams.append({'id': f't{len(teams)+1}', 'name': args[0], 'level': args[1] if len(args) > 1 else "Standard", 'budget': 200})
        await db.save('teams', teams)
        await update.message.reply_text(f"✅ تیم {args[0]} ساخته شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def team_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data.get('db')
    teams = await db.get('teams') or []
    if not teams:
        await update.message.reply_text("📭 تیمی نیست!")
        return
    text = "⚽ لیست تیم‌ها:\n"
    for i, t in enumerate(teams, 1):
        text += f"{i}. {t.get('name')} (💰{t.get('budget')}M)\n"
    await update.message.reply_text(text)

async def player_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('role') != 'owner':
        await update.message.reply_text("❌ فقط مالک!")
        return
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("❌ فرمت: /player_add [name] [team_id] [position] [overall]")
            return
        db = context.bot_data.get('db')
        players = await db.get('players') or []
        players.append({'id': f'p{len(players)+1}', 'name': args[0], 'team_id': args[1], 'position': args[2], 'overall': int(args[3])})
        await db.save('players', players)
        await update.message.reply_text(f"✅ بازیکن {args[0]} اضافه شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def player_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data.get('db')
    players = await db.get('players') or []
    if not players:
        await update.message.reply_text("📭 بازیکنی نیست!")
        return
    text = "👤 لیست بازیکنان:\n"
    for i, p in enumerate(players[:10], 1):
        text += f"{i}. {p.get('name')} (⭐{p.get('overall')})\n"
    await update.message.reply_text(text)

async def standings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 جدول لیگ:\nهنوز مسابقه‌ای ثبت نشده!")

async def post_init(application):
    global db_instance
    db_instance = TelegramDB(application.bot, CHANNEL_ID)
    application.bot_data['db'] = db_instance
    if not await db_instance.get('teams'):
        await db_instance.save('teams', [])
    if not await db_instance.get('players'):
        await db_instance.save('players', [])

def main():
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("team_add", team_add))
    application.add_handler(CommandHandler("team_list", team_list))
    application.add_handler(CommandHandler("player_add", player_add))
    application.add_handler(CommandHandler("player_list", player_list))
    application.add_handler(CommandHandler("standings", standings))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()