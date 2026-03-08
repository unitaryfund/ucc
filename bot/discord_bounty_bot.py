"""Discord Bot for announcing new Merit Bounties.

This bot listens for GitHub webhook events and announces new merit bounties
to a Discord channel.

Usage:
    python discord_bounty_bot.py --webhook-url <github-webhook-url>
    # Or run as Discord bot:
    python discord_bounty_bot.py --token <discord-bot-token> --channel <channel-id>
"""

import os
import json
import asyncio
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import aiohttp
from github import Github
from discord import Embed


class GitHubWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for GitHub webhooks."""
    
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    
    def do_POST(self):
        """Handle incoming POST requests from GitHub."""
        if self.path != "/webhook":
            self.send_error(404)
            return
            
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        # Verify signature if secret is set
        if self.webhook_secret:
            import hmac
            signature = self.headers.get("X-Hub-Signature-256", "")
            expected = hmac.new(
                self.webhook_secret.encode(),
                body,
                "sha256"
            ).hexdigest()
            if not signature.endswith(expected):
                self.send_error(401)
                return
        
        try:
            event = json.loads(body)
            self.handle_event(event)
        except Exception as e:
            print(f"Error processing webhook: {e}")
        
        self.send_response(200)
        self.end_headers()
    
    def handle_event(self, event):
        """Process the GitHub event."""
        action = event.get("action")
        issue = event.get("issue", {})
        labels = issue.get("labels", [])
        
        # Check if it's a merit-bounty
        is_bounty = any(
            label.get("name") == "merit-bounty" 
            for label in labels
        )
        
        if is_bounty and action in ("opened", "reopened"):
            self.announce_bounty(issue)
    
    async def announce_bounty(self, issue):
        """Send bounty announcement to Discord."""
        if not self.discord_webhook_url:
            return
        
        embed = Embed(
            title=f"🎯 New Merit Bounty: #{issue.get('number')}",
            description=issue.get("title"),
            color=0x00FF00,
            url=issue.get("html_url")
        )
        
        body = issue.get("body", "")
        if body:
            # Truncate body
            body = body[:500] + "..." if len(body) > 500 else body
            embed.add_field(
                name="Description", 
                value=body[:1000], 
                inline=False
            )
        
        # Add bounty amount if mentioned
        for label in issue.get("labels", {}):
            if "bounty" in label.get("name", "").lower():
                embed.add_field(
                    name="Bounty", 
                    value=label.get("name"), 
                    inline=True
                )
        
        embed.set_footer(text=f"Repository: {issue.get('repository', {}).get('full_name', 'N/A')}")
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.discord_webhook_url,
                embed=embed.to_dict()
            )
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


async def run_webhook_server(port=8080):
    """Run the webhook server."""
    server = HTTPServer(("", port), GitHubWebhookHandler)
    print(f"🌐 Webhook server running on port {port}")
    print(f"   Set GitHub webhook URL to: http://your-server:{port}/webhook")
    await asyncio.Future()  # Run forever


async def run_discord_bot(token: str, channel_id: int):
    """Run as a Discord bot (alternative to webhooks)."""
    import discord
    
    intents = discord.Intents.default()
    intents.issues = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")
    
    await client.start(token)


def main():
    parser = argparse.ArgumentParser(description="Discord Bounty Announcer Bot")
    parser.add_argument("--port", type=int, default=8080, help="Webhook server port")
    parser.add_argument("--webhook-url", help="Discord webhook URL for announcements")
    parser.add_argument("--github-secret", help="GitHub webhook secret")
    parser.add_argument("--token", help="Discord bot token (alternative to webhook)")
    parser.add_argument("--channel", type=int, help="Discord channel ID")
    
    args = parser.parse_args()
    
    if args.webhook_url:
        os.environ["DISCORD_WEBHOOK_URL"] = args.webhook_url
    if args.github_secret:
        os.environ["GITHUB_WEBHOOK_SECRET"] = args.github_secret
    
    if args.token and args.channel:
        asyncio.run(run_discord_bot(args.token, args.channel))
    else:
        asyncio.run(run_webhook_server(args.port))


if __name__ == "__main__":
    main()
