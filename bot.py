import discord
from discord.ext import commands, tasks
import google.generativeai as genai
import os
import asyncio
import datetime
import random
from dotenv import load_dotenv
from knowledge import (
    GINOX_KNOWLEDGE, DEAD_CHAT_MESSAGES,
    WAGMI_RESPONSES, NGMI_RESPONSES,
    PREDICT_RESPONSES, EIGHTBALL_RESPONSES
)

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIG — set these in your .env file
# ─────────────────────────────────────────────
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")
OWNER_TAG           = os.getenv("OWNER_TAG", "@ui.kay")
VERIFIED_ROLE       = os.getenv("VERIFIED_ROLE", "verified")
GENERAL_CHANNEL     = os.getenv("GENERAL_CHANNEL_NAME", "general")
DEAD_CHAT_HOURS     = int(os.getenv("DEAD_CHAT_HOURS", "6"))

# ─────────────────────────────────────────────
#  GEMINI SETUP
# ─────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=f"""
{GINOX_KNOWLEDGE}

IMPORTANT INSTRUCTIONS:
- You are Ginox Intern. Stay in character ALWAYS.
- If someone asks something NOT in your knowledge base, respond with something like:
  "Hmm ser, that one's above my intern pay grade 😅 Let me grab the boss — {OWNER_TAG} can you help out here?"
- Never fabricate information about GINOX. If you don't know, tag the owner.
- Keep casual replies SHORT and punchy (1-3 sentences). Use longer replies only for real technical questions.
- Use crypto slang naturally but don't overdo it.
- When sharing links, ONLY use official ones from the knowledge base.
- NEVER give financial advice under any circumstances.
- Be helpful, hype, and fun. This is a crypto community!
"""
)

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

last_message_time: dict[int, datetime.datetime] = {}
conversation_history: dict[int, list] = {}

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def get_verified_role(guild):
    return discord.utils.find(lambda r: r.name.lower() == VERIFIED_ROLE.lower(), guild.roles)

def get_general_channel(guild):
    return discord.utils.find(lambda c: c.name.lower() == GENERAL_CHANNEL.lower(), guild.text_channels)

async def ask_gemini(user_id: int, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "parts": [user_message]})
    history = conversation_history[user_id][-20:]
    try:
        chat = gemini_model.start_chat(history=history[:-1])
        response = chat.send_message(user_message)
        reply = response.text
        conversation_history[user_id].append({"role": "model", "parts": [reply]})
        if len(conversation_history[user_id]) > 40:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        return reply
    except Exception as e:
        print(f"Gemini error: {e}")
        return "My brain just glitched 😅 Try again in a sec ser, the intern needs a moment."

def split_message(text: str, limit: int = 1990) -> list:
    if len(text) <= limit:
        return [text]
    chunks = []
    while len(text) > limit:
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks

# ─────────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Ginox Intern is LIVE as {bot.user}")
    print(f"   Owner tag : {OWNER_TAG}")
    print(f"   Monitoring: #{GENERAL_CHANNEL}")
    print(f"   Dead chat : {DEAD_CHAT_HOURS}h silence threshold")
    dead_chat_checker.start()

@bot.event
async def on_member_join(member: discord.Member):
    general = get_general_channel(member.guild)
    if general:
        msgs = [
            f"🎉 YO! Welcome to the GINOX fam, {member.mention}! Your intern (that's me 👋) is here to help. Type `!help` to see what I can do. WAGMI! 🚀",
            f"👀 New face just dropped! Welcome {member.mention}! I'm Ginox Intern — your slightly sarcastic but very helpful guide. Hit me with your questions! LFG 🔥",
            f"🚀 LFG! {member.mention} just joined the GINOX ecosystem! Check `!links` for official resources and `!help` for commands. The intern is at your service 😄",
        ]
        await general.send(random.choice(msgs))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    last_message_time[message.channel.id] = datetime.datetime.utcnow()
    await bot.process_commands(message)

    # Respond if bot is mentioned or DM
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not content:
            content = "Hello!"
        async with message.channel.typing():
            reply = await ask_gemini(message.author.id, content)
            for chunk in split_message(reply):
                await message.reply(chunk)

# ─────────────────────────────────────────────
#  DEAD CHAT REVIVAL
# ─────────────────────────────────────────────
@tasks.loop(minutes=30)
async def dead_chat_checker():
    await bot.wait_until_ready()
    now = datetime.datetime.utcnow()
    for guild in bot.guilds:
        general = get_general_channel(guild)
        if not general:
            continue
        channel_id = general.id
        last_time = last_message_time.get(channel_id)
        if last_time is None:
            last_message_time[channel_id] = now
            continue
        hours_silent = (now - last_time).total_seconds() / 3600
        if hours_silent >= DEAD_CHAT_HOURS:
            role = get_verified_role(guild)
            role_mention = role.mention if role else f"@{VERIFIED_ROLE}"
            msg = random.choice(DEAD_CHAT_MESSAGES).replace("{role}", role_mention)
            try:
                await general.send(msg)
                last_message_time[channel_id] = now
                print(f"💬 Revived dead chat in {guild.name}")
            except Exception as e:
                print(f"Dead chat error in {guild.name}: {e}")

# ─────────────────────────────────────────────
#  COMMANDS — INFO
# ─────────────────────────────────────────────
@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="👋 Ginox Intern — Command Center",
        description="Your slightly sarcastic but always helpful GINOX guide. Here's everything I can do:",
        color=0x5865F2
    )
    embed.add_field(name="💬 Chat With Me", value="Mention me `@Ginox Intern` and ask anything about GINOX!", inline=False)
    embed.add_field(name="ℹ️ Info Commands", value=(
        "`!ginox` — About GINOX ecosystem\n"
        "`!gidex` — Gidex DEX info\n"
        "`!mining` — How mining works\n"
        "`!signalx` — SignalX trading signals\n"
        "`!ai` — Ginox AI & Intelligent X\n"
        "`!links` — All official links\n"
        "`!roadmap` — GINOX roadmap\n"
        "`!minerlevel <1-20>` — Miner level stats\n"
        "`!energy` — Energy tank levels\n"
        "`!cards` — Card system overview\n"
        "`!faq` — Common questions answered"
    ), inline=False)
    embed.add_field(name="🎮 Fun Commands", value=(
        "`!wagmi` — Good vibes only\n"
        "`!ngmi` — Pick yourself up ser\n"
        "`!predict <coin>` — Useless price prediction 😂\n"
        "`!8ball <question>` — The oracle has spoken\n"
        "`!roll` — Roll a dice\n"
        "`!flip` — Flip a coin\n"
        "`!gm` — Good morning!\n"
        "`!trivia` — Test your GINOX knowledge"
    ), inline=False)
    embed.add_field(name="🛡️ Moderation (Admins Only)", value=(
        "`!warn @user <reason>` — Warn a user\n"
        "`!mute @user <minutes> <reason>` — Timeout a user\n"
        "`!unmute @user` — Remove timeout\n"
        "`!clear <amount>` — Delete messages (max 100)"
    ), inline=False)
    embed.set_footer(text="Ginox Intern | Not financial advice. Ever. 😅")
    await ctx.send(embed=embed)


@bot.command(name="ginox")
async def ginox_info(ctx):
    embed = discord.Embed(
        title="⚡ What is GINOX?",
        description=(
            "**GINOX** is an **Intelligent Web3 Suite** — one unified ecosystem combining "
            "**Artificial Intelligence** and **Blockchain** into a single digital command center.\n\n"
            "No more switching between 10 different apps. Trade, earn, research, and automate — all in one place 🚀"
        ),
        color=0xFFD700
    )
    embed.add_field(name="🔗 Blockchain Products", value="• Gidex (DEX Trading)\n• Ginox Core (Mine-to-Earn)\n• SignalX (Trading Signals)", inline=True)
    embed.add_field(name="🤖 AI Products", value="• Ginox AI (Multi-model hub)\n• Intelligent X (Signal analyzer)", inline=True)
    embed.add_field(name="🌐 Website", value="https://ginox.io/", inline=False)
    embed.set_footer(text="An Intelligent Web3 Suite")
    await ctx.send(embed=embed)


@bot.command(name="gidex")
async def gidex_info(ctx):
    embed = discord.Embed(
        title="📊 Gidex — GINOX Decentralized Exchange",
        description="Your wallet. Your funds. Your trades. No middleman. 💪",
        color=0x00CED1
    )
    embed.add_field(name="What is Gidex?", value="A fully decentralized Web3 trading platform with spot trading, perpetual futures, cross-chain bridging, and token swaps.", inline=False)
    embed.add_field(name="Key Features", value=(
        "✅ Non-custodial — you keep your keys\n"
        "✅ No account creation — wallet = account\n"
        "✅ Omni-chain settlement layer\n"
        "✅ Deep liquidity pools\n"
        "✅ Limit orders (~0.045% fee)\n"
        "✅ High leverage perpetual futures"
    ), inline=False)
    embed.add_field(name="🗓️ Launch", value="**Q1 2026 — Gidex Mega Launch (Phase 3)**", inline=False)
    embed.set_footer(text="Not a CEX. No account freezes. No restrictions. 👀")
    await ctx.send(embed=embed)


@bot.command(name="mining")
async def mining_info(ctx):
    embed = discord.Embed(
        title="⛏️ Ginox Core — Mine-to-Earn",
        description="Mine real BNB for FREE directly on Telegram. Zero investment needed. Literally. 👀",
        color=0xFFA500
    )
    embed.add_field(name="How It Works", value=(
        "1️⃣ Open the app & activate your miner\n"
        "2️⃣ Session runs automatically ⚙️\n"
        "3️⃣ Collect rewards when session ends\n"
        "4️⃣ Restart & repeat 🔁"
    ), inline=False)
    embed.add_field(name="⚡ Energy", value="• Free recharge every 12hrs\n• Open app 3x/day for bonus\n• 13 tank levels (100→700 energy)", inline=True)
    embed.add_field(name="⛏️ Miner", value="• 20 levels total\n• Max: 12hr sessions, 3,195 coins/hr\n• More levels = more card slots", inline=True)
    embed.add_field(name="💡 Pro Tips", value=(
        "• Always fill tank before sessions\n"
        "• Upgrade miner level first\n"
        "• Combine Coin Boost + Energy cards\n"
        "• Never miss your daily streak!"
    ), inline=False)
    embed.add_field(name="🚀 Start Mining Free", value="https://t.me/GinoxApp_Bot", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="signalx")
async def signalx_info(ctx):
    embed = discord.Embed(
        title="📡 SignalX — Crypto Trading Signals",
        description="Expert signals. 90%+ accuracy. Entry. Exit. Take-profit. Clean and simple. 📈",
        color=0xFF4500
    )
    embed.add_field(name="What You Get", value=(
        "• Real-time market signals\n"
        "• Clear entry/exit/TP levels\n"
        "• Market structure analysis\n"
        "• Liquidity & volatility insights\n"
        "• Works for beginners AND pros"
    ), inline=False)
    embed.add_field(name="📢 Join SignalX", value="https://t.me/Ginox_OfficialTP", inline=False)
    embed.set_footer(text="Not financial advice. Always DYOR. 🙏")
    await ctx.send(embed=embed)


@bot.command(name="ai")
async def ai_info(ctx):
    embed = discord.Embed(
        title="🤖 Ginox AI — All-in-One AI Hub",
        description="Multiple AI models. One platform. No more tab switching like a degen 🧠",
        color=0x9B59B6
    )
    embed.add_field(name="Ginox AI", value=(
        "• Access multiple LLMs in one interface\n"
        "• AI recommends best model per task\n"
        "• Content generation, research, analytics\n"
        "• Trading research & automation\n"
        "• Business productivity tools"
    ), inline=True)
    embed.add_field(name="Intelligent X", value=(
        "• AI that validates SignalX signals\n"
        "• Rates signals: invalid / high-risk /\n  short-term / long-term\n"
        "• Trained on market data & sentiment\n"
        "• Trade smarter, not harder 🧠"
    ), inline=True)
    embed.add_field(name="🌐 Access", value="https://app.ginox.io/Ginox-AI", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="links")
async def links_cmd(ctx):
    embed = discord.Embed(
        title="🔗 GINOX Official Links",
        description="**ONLY use these official links.** Scammers are everywhere — stay safe ser 👀",
        color=0x2ECC71
    )
    embed.add_field(name="🌐 Platforms", value=(
        "• [Website](https://ginox.io/) — ginox.io\n"
        "• [App](https://app.ginox.io) — app.ginox.io\n"
        "• [Mining App](https://t.me/GinoxApp_Bot) — Telegram"
    ), inline=False)
    embed.add_field(name="📱 Social Media", value=(
        "• [Twitter/X](https://x.com/Ginox_Official)\n"
        "• [Telegram Channel](https://t.me/Ginox_Official)\n"
        "• [Telegram Topic/Signals](https://t.me/Ginox_OfficialTP)\n"
        "• [Instagram](https://www.instagram.com/ginox_official/)\n"
        "• [YouTube](https://www.youtube.com/@ginox_official)\n"
        "• [Discord](https://discord.gg/Cw4upzre)"
    ), inline=False)
    embed.set_footer(text="⚠️ The GINOX team will NEVER DM you first. Never share your seed phrase.")
    await ctx.send(embed=embed)


@bot.command(name="roadmap")
async def roadmap_cmd(ctx):
    embed = discord.Embed(
        title="🗺️ GINOX Roadmap",
        description="Building the world's most intelligent Web3 suite — phase by phase.",
        color=0x3498DB
    )
    embed.add_field(name="✅ Phase 1 — Q2 2025", value="Ginox Core App + SignalX\n**LAUNCHED 🟢**", inline=False)
    embed.add_field(name="✅ Phase 2 — Q3 2025", value="Ginox AI + Ginox Intelligent X\n**LAUNCHED 🟢**", inline=False)
    embed.add_field(name="🔜 Phase 3 — Q1 2026", value="**Gidex Mega Launch** 🔥\nSpot & Futures trading, bridging, swaps\n**COMING SOON 🟡**", inline=False)
    embed.set_footer(text="WAGMI ser. The roadmap doesn't lie. 🚀")
    await ctx.send(embed=embed)


@bot.command(name="minerlevel")
async def miner_level(ctx, level: int = None):
    if level is None or not (1 <= level <= 20):
        await ctx.send("❌ Provide a level between 1–20. Example: `!minerlevel 10`")
        return
    data = {
        1:(1.0,10,100,1,500), 2:(1.5,12,120,1,1500), 3:(2.0,15,144,1,3000),
        4:(2.5,18,173,1,6000), 5:(3.0,20,207,2,10000), 6:(3.5,22,249,2,15000),
        7:(4.0,25,299,2,21000), 8:(5.0,28,358,2,28000), 9:(6.0,30,430,3,36000),
        10:(7.0,32,516,3,45000), 11:(8.0,35,619,3,55000), 12:(9.0,38,743,3,66000),
        13:(10.0,40,892,4,78000), 14:(10.5,42,1070,4,91000), 15:(11.0,45,1284,4,105000),
        16:(11.5,48,1541,4,120000), 17:(12.0,50,1849,5,136000), 18:(12.0,52,2219,5,153000),
        19:(12.0,55,2662,5,171000), 20:(12.0,58,3195,5,190000),
    }
    d = data[level]
    embed = discord.Embed(title=f"⛏️ Miner Level {level}", color=0xFFA500)
    embed.add_field(name="⏱️ Session Duration", value=f"{d[0]} hours", inline=True)
    embed.add_field(name="⚡ Energy/Hour", value=str(d[1]), inline=True)
    embed.add_field(name="💰 Coins/Hour", value=str(d[2]), inline=True)
    embed.add_field(name="🃏 Card Slots", value=str(d[3]), inline=True)
    if level < 20:
        embed.add_field(name="💸 Upgrade Cost", value=f"{d[4]:,} coins", inline=True)
    else:
        embed.add_field(name="🏆 Status", value="MAX LEVEL!", inline=True)
    embed.add_field(name="🪙 Coins Per Session", value=f"{d[2]*d[0]:,.0f} coins", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="energy")
async def energy_info(ctx):
    tank = [
        (1,100,"Free"),(2,120,"500"),(3,150,"1,500"),(4,180,"4,000"),
        (5,220,"8,000"),(6,260,"14,000"),(7,300,"22,000"),(8,350,"32,000"),
        (9,400,"45,000"),(10,460,"60,000"),(11,520,"80,000"),(12,600,"100,000"),(13,700,"130,000")
    ]
    table = "```\nLvl | Max Energy | Upgrade Cost (tokens)\n" + "-"*40 + "\n"
    for lvl, energy, cost in tank:
        table += f" {lvl:<3} | {energy:<10} | {cost}\n"
    table += "```"
    embed = discord.Embed(title="⚡ Energy Tank Levels", description=table, color=0xFFFF00)
    embed.set_footer(text="Free recharge every 12hrs | Open app 3x/day for bonus energy | Buy from shop")
    await ctx.send(embed=embed)


@bot.command(name="cards")
async def cards_info(ctx):
    embed = discord.Embed(
        title="🃏 Card System Overview",
        description="Cards are your secret weapon for maximizing mining efficiency!",
        color=0x8E44AD
    )
    embed.add_field(name="Card Types", value=(
        "⏱️ **Duration Boost** — Longer mining sessions\n"
        "💰 **Coin Boost** — More coins per hour\n"
        "⚡ **Energy Efficiency** — Less energy consumed\n"
        "💎 **Rare Drop Chance** — Better loot drops\n"
        "🔄 **Recharge Boost** — Faster energy recharge\n"
        "👥 **Referral Boost** — More referral rewards"
    ), inline=False)
    embed.add_field(name="Tiers", value="Very Low → Low → Normal → High → Very High → **Extreme** 🔥", inline=False)
    embed.add_field(name="How to Get", value="🛒 Shop\n⛏️ Mining drops\n👥 Referrals\n🔗 Card chains", inline=True)
    embed.add_field(name="Rules", value="• Max Level 5\n• Can't swap during mining\n• Slots depend on miner level\n• Some need active referrals", inline=True)
    embed.set_footer(text="Pro tip: Combine Coin Boost + Energy Efficiency for max gains 💡")
    await ctx.send(embed=embed)


@bot.command(name="faq")
async def faq_cmd(ctx):
    embed = discord.Embed(title="❓ Ginox FAQ", description="Top questions answered by your favorite intern 😎", color=0x1ABC9C)
    embed.add_field(name="Is mining free?", value="YES! No investment. Open app → activate miner → mine BNB. Simple.", inline=False)
    embed.add_field(name="Is Gidex a CEX or DEX?", value="100% DEX. Non-custodial. Your wallet = your account. No freezes ever. 💪", inline=False)
    embed.add_field(name="When is Gidex launching?", value="Q1 2026 — Phase 3 Mega Launch. WAGMI 🚀", inline=False)
    embed.add_field(name="Why did mining stop?", value="Energy ran out! Recharge free every 12hrs, or open app 3x/day for bonus.", inline=False)
    embed.add_field(name="What's an active referral?", value="Someone who joined via your link AND activated their miner 21+ times. You earn 5% of their mining! 💰", inline=False)
    embed.add_field(name="Multiple accounts allowed?", value="NO. One Telegram account per player. Multiple = restrictions. Don't 🚫", inline=False)
    embed.add_field(name="Is GINOX safe?", value="Smart contracts are audited. Non-custodial = GINOX never holds your funds. Always DYOR 🔐", inline=False)
    await ctx.send(embed=embed)

# ─────────────────────────────────────────────
#  FUN COMMANDS
# ─────────────────────────────────────────────
@bot.command(name="wagmi")
async def wagmi(ctx):
    await ctx.send(random.choice(WAGMI_RESPONSES))

@bot.command(name="ngmi")
async def ngmi(ctx):
    await ctx.send(random.choice(NGMI_RESPONSES))

@bot.command(name="gm")
async def gm(ctx):
    responses = [
        f"GM GM {ctx.author.mention}! ☀️ Rise and grind ser — checked your mining session today? LFG! 🚀",
        f"GMMM {ctx.author.mention}! 🌅 Another day, another mining session. Stay blessed and stay WAGMI! 💪",
        f"Good morning fren {ctx.author.mention}! ☀️ Did you claim your daily reward? Don't let that streak reset! 🔥",
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="predict")
async def predict(ctx, *, coin: str = "the market"):
    await ctx.send(f"🔮 **{coin.upper()} prediction:** {random.choice(PREDICT_RESPONSES)}")

@bot.command(name="8ball")
async def eightball(ctx, *, question: str = None):
    if not question:
        await ctx.send("❓ Ask me something! Example: `!8ball will I be rich?`")
        return
    await ctx.send(f"**{ctx.author.mention} asked:** *{question}*\n{random.choice(EIGHTBALL_RESPONSES)}")

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    if sides < 2: sides = 6
    await ctx.send(f"🎲 {ctx.author.mention} rolled a **{random.randint(1, sides)}** (1–{sides})!")

@bot.command(name="flip")
async def flip(ctx):
    await ctx.send(f"🪙 {ctx.author.mention} flipped: **{random.choice(['Heads 🪙', 'Tails 🪙'])}**!")

@bot.command(name="trivia")
async def trivia(ctx):
    questions = [
        ("What does 'DEX' stand for?", "decentralized exchange", "It's literally the core of Gidex! 😂"),
        ("What is the max miner level in Ginox Core?", "20", "Level 20: 12hr sessions, 3,195 coins/hr. BEAST! 🔥"),
        ("What does 'HODL' mean in crypto?", "hold on for dear life", "A legendary typo that became crypto gospel 😅"),
        ("What is the max energy tank level?", "13", "Level 13 = 700 energy. Stack it up! ⚡"),
        ("How many days is the Ginox Core daily reward cycle?", "10", "Miss one day and the cycle resets. Don't sleep! 😤"),
        ("What does 'non-custodial' mean?", "you control your own funds", "YOUR keys, YOUR coins. The GINOX way 🔐"),
        ("How many times must a referral activate their miner to count as active?", "21", "21 activations = active referral = you earn 5%! 💰"),
        ("What phase is the Gidex Mega Launch?", "phase 3", "Q1 2026. Stay ready ser! 🚀"),
        ("What does 'WAGMI' stand for?", "we are all gonna make it", "And yes. We. Are. 🚀"),
        ("What's the max level a card can be upgraded to?", "5", "Level 5 is max and the effects get juicy 💎"),
    ]
    q, answer, fact = random.choice(questions)
    embed = discord.Embed(title="🧠 Ginox Trivia!", description=f"**{q}**\n\n⏱️ You have 30 seconds!", color=0xE74C3C)
    await ctx.send(embed=embed)

    def check(m):
        return m.channel == ctx.channel and not m.author.bot

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        if answer.lower() in msg.content.lower():
            await ctx.send(f"✅ **Correct!** {msg.author.mention} is built different! 🎉\n💡 {fact}")
        else:
            await ctx.send(f"❌ Not quite! Answer: **{answer.title()}**\n💡 {fact}")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Time's up! Answer was: **{answer.title()}**\n💡 {fact}")

# ─────────────────────────────────────────────
#  MODERATION
# ─────────────────────────────────────────────
def is_mod():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command(name="warn")
@is_mod()
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    embed = discord.Embed(title="⚠️ Warning Issued", color=0xFFCC00)
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)
    try:
        await member.send(
            f"⚠️ You received a warning in **{ctx.guild.name}**.\n"
            f"**Reason:** {reason}\n"
            "Please follow the server rules. Further violations may result in a mute or ban."
        )
    except discord.Forbidden:
        pass

@bot.command(name="mute")
@is_mod()
async def mute(ctx, member: discord.Member, duration: int = 10, *, reason: str = "No reason provided"):
    try:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        embed = discord.Embed(title="🔇 User Muted", color=0xFF6347)
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute that user.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command(name="unmute")
@is_mod()
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f"✅ {member.mention} has been unmuted.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute that user.")

@bot.command(name="clear")
@is_mod()
async def clear(ctx, amount: int = 10):
    if amount > 100: amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Cleared {len(deleted) - 1} messages.")
    await asyncio.sleep(3)
    await msg.delete()

@warn.error
@mute.error
@unmute.error
@clear.error
async def mod_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use that command ser 🚫")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing argument. Check `!help` for usage.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ User not found. Make sure you @mentioned them correctly.")

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
