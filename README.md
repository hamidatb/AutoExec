# Club Exec Task Manager Bot

A comprehensive Discord bot that automates executive task management for clubs and organizations. The bot integrates with Google Docs and Google Sheets to manage executive tasks, meetings, and deadlines automatically.

## 🎯 Features

### **Meeting Management**
- **Schedule meetings** with `/meeting set` command
- **Automatic reminders** at T-2h and T0
- **Minutes parsing** from Google Docs with automatic task extraction
- **Agenda templates** for structured meetings
- **Meeting cancellation** and rescheduling

### **Task Management**
- **Automatic task creation** from meeting minutes
- **Manual task assignment** with `/assign` command
- **Deadline tracking** with automated reminders
- **Status updates** via natural language responses
- **Task rescheduling** and completion tracking

### **Smart Automation**
- **Minutes parsing** from structured Google Docs tables
- **Action item extraction** with automatic task creation
- **Deadline reminders** at T-24h, T-2h, T+0h (overdue)
- **Escalation system** for missed deadlines
- **Background monitoring** for continuous operation

### **User Interaction**
- **Natural language responses** ("done", "not yet", "reschedule to...")
- **Private DM setup** for admins
- **Public channel commands** for general use
- **Role-based permissions** (admin vs. regular users)

## 🚀 Quick Start

### 1. **Environment Setup**
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

### 2. **Google API Configuration**
1. Create a Google Cloud Project
2. Enable Google Drive and Google Sheets APIs
3. Create service account credentials
4. Download `servicekey.json` to the `googledrive/` folder
5. Share your Google Drive folders with the service account email

### 3. **Environment Variables**
Create a `.env` file in the root directory:
```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_default_channel_id

# Google Drive Configuration
DRIVE_FOLDER_ID=your_google_drive_folder_id

# Club Configuration (optional - can be set during setup)
CLUB_NAME=Your Club Name
TIMEZONE=America/Edmonton
TASK_REMINDER_CHANNEL_ID=your_task_channel_id
MEETING_REMINDER_CHANNEL_ID=your_meeting_channel_id
ESCALATION_CHANNEL_ID=your_escalation_channel_id
```

### 4. **Run the Bot**
```bash
python discordbot/discord_client.py
```

## 📋 Setup Process

### **First-Time Club Setup**
1. **Invite the bot** to your Discord server
2. **Start setup** by sending `/setup` in a private DM with the bot
3. **Follow the guided setup**:
   - Club name
   - Admin selection (@mention)
   - Google Sheets creation
   - Channel configuration

### **Setup Steps**
1. **Club Name**: Provide your club or organization name
2. **Admin Selection**: @mention the person who should have admin privileges
3. **Google Sheets Creation**: Bot automatically creates:
   - `{Club Name} Task Manager Config` - Main configuration
   - `{Club Name} Tasks - {Month Year}` - Task tracking
   - `{Club Name} Meetings - {Month Year}` - Meeting management
4. **Channel Configuration**: Set channels for reminders and escalations

## 🎮 Commands

### **Admin Commands (DM Only)**
- `/setup` - Start club configuration
- `/meeting set title:"Title" start:"YYYY-MM-DD HH:MM" [end:"YYYY-MM-DD HH:MM"]` - Schedule meeting
- `/meeting cancel <meeting_id>` - Cancel meeting
- `/meeting linkminutes <meeting_id> <url>` - Link minutes document
- `/assign @user "Task title" [due:YYYY-MM-DD HH:MM]` - Assign task

### **General Commands**
- `/meeting upcoming` - Show upcoming meetings
- `/meeting agenda [title]` - Create agenda template
- `/summary [month]` - Show all open tasks
- `/status @user` - Show user's open tasks
- `/done <task_id>` - Mark task complete
- `/reschedule <task_id> <new_date>` - Reschedule task
- `/subscribe` - Subscribe to private DMs

### **Natural Language Responses**
- Reply **"done"** to mark a task complete
- Reply **"not yet"** to mark a task in progress
- Reply **"reschedule to <date>"** to change deadline

## 📊 Google Sheets Schema

### **Tasks Sheet**
| Column | Description |
|--------|-------------|
| task_id | Unique UUID |
| title | Action item description |
| owner_discord_id | Discord ID of responsible exec |
| owner_name | Name from minutes |
| due_at | ISO 8601 timestamp |
| status | open, in_progress, done, blocked |
| priority | low, medium, high |
| source_doc | Link to minutes doc |
| channel_id | Reminder channel |
| notes | Optional notes |

### **Meetings Sheet**
| Column | Description |
|--------|-------------|
| meeting_id | Unique UUID |
| title | Meeting title |
| start_at_utc | Start time UTC |
| end_at_utc | End time UTC |
| start_at_local | Local readable string |
| end_at_local | Local readable string |
| channel_id | Meeting channel |
| minutes_doc_url | Link to Google Doc |
| status | scheduled, started, ended, canceled |

### **Config Sheet**
- Club name and admin Discord ID
- Channel configurations
- Timezone settings
- Allowed role IDs

## 🔄 Automation Flow

### **Meeting Workflow**
1. **Admin schedules meeting** with `/meeting set`
2. **Bot creates meeting entry** in Google Sheets
3. **Automatic reminders** sent at T-2h and T0
4. **30 minutes after meeting** → Bot parses linked minutes
5. **Action items extracted** and tasks created automatically
6. **Task reminders** sent based on deadlines

### **Task Workflow**
1. **Tasks created** from meeting minutes or manual assignment
2. **Reminders sent** at T-24h, T-2h, T+0h (overdue)
3. **Users respond** with natural language
4. **Bot updates** task status automatically
5. **Escalation** to admin if tasks overdue for 48+ hours

## 📝 Meeting Minutes Format

The bot expects meeting minutes in Google Docs with an **Action Items** table containing:

| Role | Team Member | Action Items To Be Done By Next Meeting | Deadline |
|------|-------------|-------------------------------------------|----------|
| President | John Doe | Prepare budget proposal | 2025-09-15 |
| Secretary | Jane Smith | Send meeting invites | Next meeting |

## 🛠️ Technical Architecture

### **Core Components**
- **Discord Client** (`discordbot/discord_client.py`) - Main bot interface
- **Setup Manager** (`googledrive/setup_manager.py`) - Club configuration
- **Meeting Manager** (`googledrive/meeting_manager.py`) - Meeting operations
- **Task Manager** (`googledrive/task_manager.py`) - Task operations
- **Sheets Manager** (`googledrive/sheets_manager.py`) - Google Sheets integration
- **Minutes Parser** (`googledrive/minutes_parser.py`) - Document parsing

### **Data Flow**
```
Discord Bot → Managers → Google Sheets → Google Docs
     ↓              ↓           ↓           ↓
User Commands → Business Logic → Data Storage → Content Parsing
```

## 🔧 Configuration

### **Bot Permissions**
The bot requires the following Discord permissions:
- Send Messages
- Read Message History
- Use Slash Commands
- Manage Messages (for cleanup)

### **Google API Scopes**
- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/drive`
- `https://www.googleapis.com/auth/documents.readonly`

## 🚨 Troubleshooting

### **Common Issues**
1. **Bot not responding**: Check Discord token and permissions
2. **Google Sheets errors**: Verify service account permissions
3. **Setup not working**: Ensure bot has admin permissions in server
4. **Minutes not parsing**: Check document format and table structure

### **Debug Mode**
Enable debug logging by setting environment variable:
```env
DEBUG=true
```

## 🔮 Future Enhancements

### **Planned Features**
- [ ] Attendance tracking with buttons
- [ ] Automatic Google Doc creation for minutes
- [ ] Web dashboard for task visualization
- [ ] Google Calendar integration
- [ ] Advanced reporting and analytics
- [ ] Multi-language support

### **Integration Possibilities**
- Slack integration
- Microsoft Teams integration
- Email notifications
- Mobile app companion

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the command documentation

---

**Built with ❤️ for club executives everywhere**
