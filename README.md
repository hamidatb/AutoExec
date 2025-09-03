# Club Exec Task Manager Bot

A powerful Discord bot that automates executive task management by integrating with Google Docs and Google Sheets. Perfect for clubs, organizations, and teams that need to track action items from meetings and manage deadlines effectively.

## 🚀 Features

### **Core Functionality**
- **Automated Meeting Management** - Schedule, track, and manage meetings with automatic reminders
- **Smart Task Tracking** - Parse action items from meeting minutes and create tracked tasks
- **Deadline Management** - Automated reminders and escalation for overdue tasks
- **Google Integration** - Seamless integration with Google Docs and Google Sheets
- **Discord Integration** - Full Discord bot with slash commands and natural language responses

### **Meeting Features**
- Schedule meetings with `/meeting set`
- View upcoming meetings with `/meeting upcoming`
- Create agenda templates with `/meeting agenda`
- Link minutes documents and automatically parse action items
- Automatic reminders at T-2h, T-0, and T+30m

### **Task Management**
- Assign tasks to team members with `/assign`
- View task summaries with `/summary`
- Check individual status with `/status @user`
- Mark tasks complete with `/done`
- Reschedule deadlines with `/reschedule`
- Natural language responses: "done", "not yet", "reschedule to [date]"

### **Automation & Reminders**
- **Task Reminders**: T-24h, T-2h, overdue, and escalation after 48h
- **Meeting Reminders**: T-2h, T-0, and automatic minutes processing
- **Smart Escalation**: Automatic admin notifications for overdue tasks
- **Background Processing**: Persistent reminders across bot restarts

## 🛠️ Setup Instructions

### **1. Prerequisites**
- Python 3.8 or higher
- Discord Bot Token
- Google Cloud Project with APIs enabled
- Google Service Account credentials

### **2. Installation**

```bash
# Clone the repository
git clone <repository-url>
cd AutoExec

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **3. Google Cloud Setup**

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Required APIs**
   - Google Drive API
   - Google Sheets API
   - Google Docs API
   - Google Calendar API (optional)

3. **Create Service Account**
   - Go to IAM & Admin > Service Accounts
   - Create new service account
   - Download JSON key file
   - Place in `googledrive/servicekey.json`

4. **Share Google Drive Folder**
   - Create a folder for your club's documents
   - Share with service account email (read/write access)

### **4. Discord Bot Setup**

1. **Create Discord Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create new application
   - Go to Bot section and create bot
   - Copy bot token

2. **Invite Bot to Server**
   - Use OAuth2 > URL Generator
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Read Message History`, `Use Slash Commands`
   - Use generated URL to invite bot

### **5. Environment Configuration**

```bash
# Copy environment template
cp env.example .env

# Edit .env with your values
nano .env
```

**Required Environment Variables:**
```env
DISCORD_BOT_TOKEN=your_bot_token_here
CLUB_NAME=Your Club Name
TIMEZONE=America/Edmonton
```

**Optional Environment Variables:**
```env
TASK_REMINDER_CHANNEL_ID=channel_id_for_task_reminders
MEETING_REMINDER_CHANNEL_ID=channel_id_for_meeting_reminders
ESCALATION_CHANNEL_ID=channel_id_for_escalations
```

### **6. Environment Management (IMPORTANT!)**

**⚠️ CRITICAL: Avoid API Key Conflicts**

This project uses a virtual environment to prevent conflicts with conda or system environment variables. Follow these steps carefully:

#### **Option A: Use Setup Scripts (Recommended)**
```bash
# First time setup
./setup_env.sh

# Run the bot
./run_bot.sh
```

#### **Option B: Manual Setup**
```bash
# Deactivate conda if active
conda deactivate

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Run the bot
python -m discordbot.discord_client
```

#### **Option C: Use direnv (Advanced)**
```bash
# Install direnv
brew install direnv  # macOS
# or
sudo apt install direnv  # Ubuntu

# Allow direnv for this project
direnv allow

# The environment will automatically load when you enter the directory
```

### **7. Run the Bot**

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot (use module format to avoid import issues)
python -m discordbot.discord_client
```

## 📋 Bot Setup Process

### **First-Time Setup**
1. **Invite bot to your Discord server**
2. **Start private DM with the bot**
3. **Run `/setup` command**
4. **Follow the setup wizard:**
   - Enter club name
   - @mention the admin user
   - Bot creates Google Sheets automatically
   - Configure Discord channels

### **Setup Steps**
1. **Club Name** - Sets the name for your organization
2. **Admin Selection** - Choose who has full bot control
3. **Google Sheets Creation** - Bot creates:
   - `{Club Name} Task Manager Config` - Main configuration
   - `{Club Name} Tasks - {Month Year}` - Task tracking
   - `{Club Name} Meetings - {Month Year}` - Meeting management
4. **Channel Configuration** - Set channels for reminders and escalations

## 🎯 Usage Examples

### **Meeting Management**

```bash
# Schedule a meeting
/meeting set title:"Weekly Exec Meeting" start:"2025-09-08 17:00" end:"2025-09-08 18:00"

# View upcoming meetings
/meeting upcoming

# Create agenda template
/meeting agenda title:"Project Review Meeting"
```

### **Task Management**

```bash
# Assign a task
/assign @username "Prepare presentation slides" due:"2025-09-10 12:00"

# View task summary
/summary
/summary September 2025

# Check user status
/status @username

# Mark task complete
/done task_id_here

# Reschedule task
/reschedule task_id_here "2025-09-12 15:00"
```

### **Natural Language Responses**
When the bot pings you about a task, simply reply:
- **"done"** → Marks task as complete
- **"not yet"** → Marks task as in progress
- **"reschedule to 2025-09-15"** → Changes deadline

## 🔧 Configuration

### **Bot Behavior Settings**
```env
# Reminder intervals
REMINDER_CHECK_INTERVAL=3600        # Task reminders every hour
MEETING_REMINDER_INTERVAL=300       # Meeting checks every 5 minutes
TASK_ESCALATION_DELAY=172800        # Escalate after 48 hours

# Meeting reminder times
MEETING_REMINDER_2H=2               # 2 hours before meeting
MEETING_REMINDER_1H=1               # 1 hour before meeting
MEETING_REMINDER_30M=0.5            # 30 minutes before meeting

# Task reminder times
TASK_REMINDER_24H=24                # 24 hours before deadline
TASK_REMINDER_2H=2                  # 2 hours before deadline
```

### **Google Sheets Schema**

#### **Tasks Sheet**
| Column | Description |
|--------|-------------|
| task_id | Unique UUID |
| title | Task description |
| owner_discord_id | Discord ID of responsible person |
| owner_name | Human-readable name |
| due_at | ISO 8601 timestamp |
| status | open, in_progress, done, blocked |
| priority | low, medium, high |
| source_doc | Link to minutes document |
| channel_id | Reminder channel |
| notes | Additional information |

#### **Meetings Sheet**
| Column | Description |
|--------|-------------|
| meeting_id | Unique UUID |
| title | Meeting title |
| start_at_utc | Start time UTC |
| end_at_utc | End time UTC |
| start_at_local | Local readable time |
| end_at_local | Local readable time |
| channel_id | Meeting channel |
| minutes_doc_url | Google Docs link |
| status | scheduled, started, ended, canceled |
| created_by | Discord ID of creator |

## 🔄 Automation Flow

### **Meeting Lifecycle**
1. **Admin schedules meeting** → Bot creates entry in Meetings sheet
2. **T-2h reminder** → Bot sends reminder to meeting channel
3. **T-0 reminder** → Bot announces meeting start
4. **T+30m processing** → Bot parses linked minutes document
5. **Task creation** → Bot extracts action items and creates tasks

### **Task Lifecycle**
1. **Task created** → From minutes parsing or manual assignment
2. **T-24h reminder** → Bot sends deadline reminder
3. **T-2h reminder** → Bot sends urgent reminder
4. **T+0 (overdue)** → Bot marks as overdue
5. **T+48h escalation** → Bot notifies admin in escalation channel

## 🚨 Troubleshooting

### **Common Issues**

**Bot not responding to commands:**
- Check bot has proper permissions
- Verify slash commands are synced
- Check bot is online and connected

**Google Sheets errors:**
- Verify service account has proper access
- Check API quotas and limits
- Ensure required APIs are enabled

**Reminders not working:**
- Check channel IDs in configuration
- Verify bot has permission to send messages
- Check timezone configuration

### **Debug Mode**
Enable debug logging by setting environment variables:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 🔮 Future Features

### **Planned Enhancements**
- **Attendance Tracking** - Button-based RSVP system
- **Google Calendar Integration** - Automatic event creation
- **Web Dashboard** - Task visualization and management
- **Advanced Analytics** - Task completion metrics
- **Multi-language Support** - Internationalization
- **Mobile App** - Companion mobile application

### **API Extensions**
- **Slack Integration** - Cross-platform support
- **Microsoft Teams** - Enterprise integration
- **Email Notifications** - Fallback communication
- **Webhook Support** - Custom integrations

## 📚 API Reference

### **Core Classes**

#### **ClubExecBot**
Main Discord bot class handling commands and interactions.

#### **ClubSheetsManager**
Manages Google Sheets operations for tasks, meetings, and configuration.

#### **MeetingManager**
Handles meeting scheduling, reminders, and minutes processing.

#### **TaskManager**
Manages task creation, updates, and deadline tracking.

#### **SetupManager**
Handles initial bot setup and configuration.

#### **MinutesParser**
Parses Google Docs to extract action items and deadlines.

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style and standards
- Testing requirements
- Pull request process
- Issue reporting

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### **Getting Help**
- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join our community discussions
- **Email**: Contact the development team

### **Community**
- **Discord Server**: Join our community server
- **GitHub Discussions**: Ask questions and share ideas
- **Contributing**: Help improve the bot

---

**Made with ❤️ for the club executive community**

*Automate your administrative tasks, focus on what matters most.*
