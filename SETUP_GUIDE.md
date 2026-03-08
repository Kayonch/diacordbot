# 🤖 Ginox Intern Bot — Complete Setup Guide

## What You're Getting
A fully-featured Discord bot built as **Ginox Intern** — funny, sarcastic, hype, occasionally professional. Powered by Google Gemini AI with deep GINOX knowledge baked in.

---

## STEP 1 — Create Your Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **"New Application"** → Name it **"Ginox Intern"**
3. Go to the **Bot** tab on the left
4. Click **"Add Bot"** → Confirm
5. Under **"Privileged Gateway Intents"**, enable ALL THREE:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Click **"Reset Token"** → Copy the token → **SAVE IT SOMEWHERE SAFE**
   > ⚠️ You only see this once! If you lose it, reset again.

### Invite the bot to your server:
1. Go to **OAuth2 → URL Generator**
2. Under **Scopes**, check: `bot`, `applications.commands`
3. Under **Bot Permissions**, check:
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Manage Messages`
   - `Moderate Members` (for mute)
   - `Read Message History`
   - `Mention Everyone`
4. Copy the generated URL → Open in browser → Add to your server

---

## STEP 2 — Get Your Free Gemini API Key

1. Go to https://aistudio.google.com
2. Sign in with your Google account
3. Click **"Get API Key"** → **"Create API Key"**
4. Copy the key → **SAVE IT**

> ✅ Completely free. No credit card needed. Generous limits.

---

## STEP 3 — Deploy to Render (Free)

### 3a. Upload your code to GitHub
1. Create a free account at https://github.com
2. Create a **new repository** (call it `ginox-intern-bot`)
3. Upload these files to the repo:
   - `bot.py`
   - `knowledge.py`
   - `requirements.txt`
   - `render.yaml`
   > **DO NOT upload** the `.env` file — it contains secrets!

### 3b. Deploy on Render
1. Go to https://render.com → Sign up free
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub account → Select your `ginox-intern-bot` repo
4. Render will auto-detect the `render.yaml` settings
5. Go to **Environment** tab and add these variables:

| Key | Value |
|-----|-------|
| `DISCORD_TOKEN` | Your Discord bot token |
| `GEMINI_API_KEY` | Your Gemini API key |
| `OWNER_TAG` | @ui.kay (or whatever your Discord username is) |
| `VERIFIED_ROLE` | verified (your role name) |
| `GENERAL_CHANNEL_NAME` | general |
| `DEAD_CHAT_HOURS` | 6 |

6. Click **"Create Background Worker"**
7. Wait 2-3 minutes for the build to complete
8. Check the logs — you should see: `✅ Ginox Intern is LIVE`

---

## STEP 4 — Configure Your Discord Server

### Create the "Timeout" role (for mute to work):
The bot uses Discord's built-in **Timeout** feature — no extra role needed! Moderators just need **Manage Messages** permission.

### Make sure the bot has the right permissions:
- In your Discord server, right-click the **Ginox Intern** role
- Give it: Read Messages, Send Messages, Manage Messages, Moderate Members, Mention Roles

---

## Commands Reference

### Info Commands
| Command | What it does |
|---------|-------------|
| `!help` | Shows all commands |
| `!ginox` | About the GINOX ecosystem |
| `!gidex` | About Gidex DEX |
| `!mining` | How Ginox Core mining works |
| `!signalx` | About SignalX signals |
| `!ai` | About Ginox AI & Intelligent X |
| `!links` | All official GINOX links |
| `!roadmap` | GINOX roadmap |
| `!minerlevel <1-20>` | Stats for a specific miner level |
| `!energy` | Energy tank level table |
| `!cards` | Card system overview |
| `!faq` | Common questions |

### Fun Commands
| Command | What it does |
|---------|-------------|
| `!wagmi` | WAGMI energy 🚀 |
| `!ngmi` | Pick yourself up ser |
| `!predict <coin>` | Hilarious (not real) price prediction |
| `!8ball <question>` | Magic 8ball |
| `!roll` | Roll a dice |
| `!flip` | Flip a coin |
| `!gm` | Good morning response |
| `!trivia` | GINOX/crypto trivia with 30s timer |

### AI Chat
| How | What it does |
|-----|-------------|
| `@Ginox Intern <question>` | Full AI conversation using Gemini |
| DM the bot | Private AI chat |

### Moderation (Admin/Mod only)
| Command | What it does |
|---------|-------------|
| `!warn @user <reason>` | Issues a warning + DMs the user |
| `!mute @user <minutes> <reason>` | Times out the user |
| `!unmute @user` | Removes timeout |
| `!clear <amount>` | Deletes up to 100 messages |

---

## Customization

To change any config value, update the **Environment Variables** in your Render dashboard:

- `OWNER_TAG` — Change who gets tagged when bot doesn't know something
- `VERIFIED_ROLE` — Change the role pinged for dead chat revival
- `GENERAL_CHANNEL_NAME` — Change which channel is monitored
- `DEAD_CHAT_HOURS` — Change how many hours before bot revives chat

No code changes needed — just update the env vars and redeploy!

---

## Troubleshooting

**Bot is offline:**
- Check Render logs for errors
- Make sure `DISCORD_TOKEN` is correct
- Ensure all 3 Privileged Intents are enabled in Discord Developer Portal

**Bot not responding to mentions:**
- Make sure "Message Content Intent" is enabled
- Check bot has "Read Messages" and "Send Messages" permissions in the channel

**Mute command not working:**
- Bot needs "Moderate Members" permission
- The bot's role must be higher than the user being muted in the role hierarchy

**Dead chat not triggering:**
- Check `GENERAL_CHANNEL_NAME` matches exactly (case-insensitive)
- Check `VERIFIED_ROLE` matches your role name exactly
- Check the `DEAD_CHAT_HOURS` value

---

## Security Reminders
- Never share your `DISCORD_TOKEN` or `GEMINI_API_KEY` publicly
- Never commit your `.env` file to GitHub
- Regularly rotate your bot token if you suspect it's compromised

---

*Built for the GINOX community. WAGMI 🚀*
