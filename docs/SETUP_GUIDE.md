# 🚀 Quick Setup Guide - Club Exec Task Manager Bot

This guide will get you up and running in under 10 minutes!

## ⚡ Quick Start (5 minutes)

### 1. **Clone & Setup**
```bash
git clone <your-repo-url>
cd AutoExec
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. **Environment Setup**
```bash
cp env.example .env
# Edit .env with your Discord bot token
nano .env
```

**Minimum required in .env:**
```env
DISCORD_BOT_TOKEN=your_bot_token_here
CLUB_NAME=Your Club Name
```

### 3. **Google Setup**
- Download service account key for `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`
- Save it as `googledrive/servicekey.json`
- Share your Google Drive folders with the service account email

### 4. **Run Bot**
```bash
python scripts/start_bot.py
```

---

## 🔧 Detailed Setup

### **Discord Bot Creation**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application
3. Go to Bot section → Create Bot
4. Copy the bot token
5. Use OAuth2 → URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Read Message History`, `Use Slash Commands`
6. Invite bot to your server

### **Google Cloud Setup**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable APIs:
   - Google Drive API
   - Google Sheets API
   - Google Docs API
4. Download Service Account Key:
   - Go to IAM & Admin → Service Accounts
   - Find `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`
   - Click on it → Keys → Add Key → Create new key → JSON
   - Save as `googledrive/servicekey.json`

---

## 🎯 First-Time Bot Setup

### **In Discord:**
1. **DM the bot** (right-click bot → Message)
2. **Send `/setup`**
3. **Follow the wizard:**
   - Enter club name
   - @mention admin user
   - Bot creates Google Sheets automatically
   - Configure Discord channels

### **Bot will create:**
- `{Club Name} Task Manager Config` - Main settings
- `{Club Name} Tasks - {Month Year}` - Task tracking
- `{Club Name} Meetings - {Month Year}` - Meeting management

### **No OAuth Required!**
- Users only need to share specific Google Drive folders
- Bot uses service account authentication
- Much simpler and more secure setup

---

## 🧪 Test Your Setup

Run the test script to verify everything works:
```bash
python tests/test_bot.py
```

You should see:
```
✅ All tests passed! The bot should be ready to run.
```

---

## 🚨 Common Issues & Fixes

### **Bot not responding:**
- Check bot has proper permissions
- Verify slash commands are synced
- Ensure bot is online

### **Google Sheets errors:**
- Verify service account has access
- Check API quotas
- Ensure APIs are enabled

### **Import errors:**
- Activate virtual environment
- Run `pip install -r requirements.txt`
- Check Python version (3.8+)

---

## 📚 Next Steps

### **Learn the Commands:**
- `/help` - See all available commands
- `/meeting set` - Schedule your first meeting
- `/assign` - Create your first task

### **Set Up Your Workflow:**
1. Schedule regular meetings
2. Link minutes documents
3. Let bot automatically create tasks
4. Use natural language responses

### **Customize:**
- Adjust reminder times in .env
- Configure escalation channels
- Set up task priorities

---

## 🆘 Need Help?

- **Documentation**: Check README.md
- **Issues**: GitHub Issues
- **Test**: Run `python tests/test_bot.py`
- **Debug**: Check console output

---

**🎉 You're all set! Your club now has automated task management!**
