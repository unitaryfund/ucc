# Discord Bounty Bot

A bot that announces new Unitary Fund merit bounties to Discord.

## Usage

### Option 1: Webhook (Simpler)

1. Create a Discord webhook in your channel
2. Run the bot:
```bash
python discord_bounty_bot.py --webhook-url "https://discord.com/api/webhooks/..."
```

3. Add GitHub webhook:
   - Go to repo Settings > Webhooks
   - Add webhook URL: `http://your-server:8080/webhook`
   - Events: Issues

### Option 2: Discord Bot

1. Create a Discord bot at https://discord.com/developers/applications
2. Run:
```bash
python discord_bounty_bot.py --token <bot-token> --channel <channel-id>
```

## Environment Variables

- `DISCORD_WEBHOOK_URL`: Discord webhook URL
- `GITHUB_WEBHOOK_SECRET`: GitHub webhook secret (optional)
