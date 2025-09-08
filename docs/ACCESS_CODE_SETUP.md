# Access Code Configuration

The bot now requires a valid access code to complete the setup process. This helps control who can set up the bot on your servers.

## Configuration

Add the following to your `.env` file:

```bash
# Access Control Configuration
# Comma-separated list of valid access codes for bot setup
VALID_ACCESS_CODES=your_access_code_here,another_code_here,club123
```

## Examples

### Single Access Code
```bash
VALID_ACCESS_CODES=club2024
```

### Multiple Access Codes
```bash
VALID_ACCESS_CODES=club2024,exec2024,secretcode
```

### No Access Codes (Not Recommended)
```bash
VALID_ACCESS_CODES=
```

## Security Best Practices

1. **Use Strong Codes**: Choose access codes that are not easily guessable
2. **Rotate Codes**: Change access codes periodically
3. **Limit Distribution**: Only share access codes with trusted administrators
4. **Monitor Usage**: Keep track of who has access codes

## Setup Flow

1. User starts setup with `/setup` command
2. Bot asks for access code
3. User provides access code
4. Bot validates the code against `VALID_ACCESS_CODES`
5. If valid, setup continues; if invalid, setup is blocked

## Troubleshooting

### "Invalid Access Code" Error
- Check that the access code is correctly configured in your `.env` file
- Ensure there are no extra spaces or special characters
- Verify the code matches exactly (case-insensitive)

### No Access Codes Configured
- If `VALID_ACCESS_CODES` is empty or not set, no one can complete setup
- Add at least one access code to allow setup

### Case Sensitivity
- Access codes are case-insensitive
- "CLUB2024" and "club2024" are treated as the same code
