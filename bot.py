import os
import discord
from discord.ext import commands
from discord import app_commands
import smtplib
from email.message import EmailMessage

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# For now: one shared mailing list (the Google Group you made)
RECIPIENTS = [
    "testplspls@googlegroups.com",
]

intents = discord.Intents.default()
intents.message_content = True  # still needed if you also keep prefix commands

class EmailBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # sync slash commands on startup
        await self.tree.sync()
        print("Slash commands synced.")

bot = EmailBot()

def send_email(subject: str, body: str, recipients: list[str]):
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

# OLD prefix command (you can keep or delete)
@bot.command()
async def sendmail(ctx, *, message: str):
    await ctx.send("Sending email...")
    try:
        send_email(
            subject=f"Message from {ctx.author.display_name}",
            body=message,
            recipients=RECIPIENTS
        )
        await ctx.send("✅ Email sent successfully!")
    except Exception as e:
        print("Email error:", e)
        await ctx.send("❌ Failed to send email.")

# NEW SLASH COMMAND
@bot.tree.command(name="sendmail", description="Send an email to your mailing list")
@app_commands.describe(message="The text that will be sent in the email")
async def sendmail_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)  # show “thinking…” privately
    try:
        send_email(
            subject=f"Message from {interaction.user.display_name}",
            body=message,
            recipients=RECIPIENTS
        )
        await interaction.followup.send("✅ Email sent successfully!", ephemeral=True)
    except Exception as e:
        print("Email error:", e)
        await interaction.followup.send("❌ Failed to send email.", ephemeral=True)

bot.run(DISCORD_TOKEN)


