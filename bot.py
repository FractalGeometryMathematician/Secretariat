import os
import discord
from discord.ext import commands
import smtplib
from email.message import EmailMessage

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# List of recipients who will get the email
RECIPIENTS = [
    "testplspls@googlegroups.com"
]

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Function to send the email
def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(RECIPIENTS)
    msg["Subject"] = subject
    msg.set_content(body)

    # Connect to Gmail and send
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

# When bot starts
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

# The command in Discord
@bot.command()
async def sendmail(ctx, *, message):
    await ctx.send("Sending email...")

    try:
        send_email(
            subject=f"Message from {ctx.author.display_name}",
            body=message
        )
        await ctx.send("✅ Email sent successfully!")
    except Exception as e:
        print("Email error:", e)
        await ctx.send("❌ Failed to send email.")

# Run the bot
bot.run(DISCORD_TOKEN)
