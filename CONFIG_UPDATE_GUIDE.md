# Server Configuration Update Guide

This guide explains how server admins can update their server configuration using the new `/config` command.

## Overview

The `/config` command allows server admins to view and update their server's configuration settings without going through the full setup process again. This is particularly useful for:

- Changing Google Drive folder links
- Updating Discord channel assignments
- Modifying server settings

## Prerequisites

- You must be the admin of the server (the user who originally set up the bot)
- The server must already be configured (setup completed)
- For Google Drive folder updates, the new folders must be shared with the service account

## Available Commands

### View Current Configuration

```
/config view
```

This command displays all current configuration settings for your server, including:
- Club name and admin information
- Google Drive folder IDs
- Discord channel assignments
- Google Sheets IDs

### Update Configuration Settings

```
/config update <setting> <value>
```

#### Available Settings

**Google Drive Folders:**
- `config_folder` - Main configuration folder link
- `monthly_folder` - Monthly sheets folder link  
- `meeting_minutes_folder` - Meeting minutes folder link

**Discord Channels:**
- `task_reminders_channel` - Channel ID for task reminders
- `meeting_reminders_channel` - Channel ID for meeting reminders
- `escalation_channel` - Channel ID for escalations

## Examples

### Update Google Drive Config Folder

```
/config update config_folder https://drive.google.com/drive/folders/1ABC123DEF456GHI789JKL
```

### Update Task Reminders Channel

```
/config update task_reminders_channel 123456789012345678
```

### Update Monthly Folder

```
/config update monthly_folder https://drive.google.com/drive/folders/1XYZ789ABC123DEF456GHI
```

## Important Notes

### Google Drive Folder Updates

When updating Google Drive folder links:

1. **Share the new folder** with the service account: `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com`
2. **Grant Editor permissions** to the service account
3. **Use the full Google Drive folder link** (not just the folder ID)
4. The bot will automatically verify access before updating

### Discord Channel Updates

When updating Discord channel IDs:

1. **Get the channel ID** by right-clicking the channel and selecting "Copy ID"
2. **Ensure the bot has access** to the channel
3. **Use only the numeric channel ID** (no # symbols or other formatting)

### Validation and Verification

The bot performs several validation checks:

- **Admin verification**: Only the server admin can update configuration
- **Folder access verification**: For Google Drive folders, the bot tests access before updating
- **Channel validation**: For Discord channels, the bot validates the channel ID format
- **Permission checks**: Ensures the bot has necessary permissions

## Error Handling

### Common Error Messages

**"Only the admin can update server configuration"**
- You must be the admin who originally set up the bot
- Contact the current admin or use `/reset` to reconfigure

**"Invalid Folder Link"**
- Ensure you're providing a complete Google Drive folder link
- The link should start with `https://drive.google.com/drive/folders/`

**"Permission denied"**
- The folder is not shared with the service account
- Share the folder with `autoexec-pubsub@active-alchemy-453323-f0.iam.gserviceaccount.com` with Editor permissions

**"Invalid Channel ID"**
- Channel ID must be numeric only (no # symbols)
- Right-click the channel and select "Copy ID" to get the correct format

### Troubleshooting

1. **Folder Access Issues**:
   - Verify the folder exists and is accessible
   - Check that the service account has Editor permissions
   - Ensure the folder link is complete and correct

2. **Channel Access Issues**:
   - Verify the channel ID is correct
   - Ensure the bot has access to the channel
   - Check that the channel exists in the server

3. **Permission Issues**:
   - Confirm you are the server admin
   - Check that the server is properly configured
   - Use `/config view` to verify current settings

## Best Practices

1. **Test Changes**: After updating configuration, test the affected features
2. **Backup Information**: Keep a record of your current settings before making changes
3. **Verify Access**: Ensure all folders and channels are accessible before updating
4. **Gradual Updates**: Update one setting at a time to isolate any issues
5. **Document Changes**: Keep track of what you've changed and when

## Support

If you encounter issues:

1. Use `/config view` to check current settings
2. Verify all permissions and access rights
3. Try updating one setting at a time
4. Contact support if problems persist

## Related Commands

- `/setup` - Initial server setup (DM only)
- `/reset` - Reset entire server configuration (admin only)
- `/help` - Show all available commands
- `/config view` - View current configuration
- `/config update` - Update configuration settings
