import os
import json
import smtplib
from email.mime.text import MIMEText

import requests
import discord
from discord.ext import commands
from discord import app_commands

# -----------------------------
# Environment variables
# -----------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_SPACE_URL = os.getenv("HF_SPACE_URL")

# Optional global default Gmail (used if server not configured)
DEFAULT_GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
DEFAULT_GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
if not HF_SPACE_URL:
    raise RuntimeError("HF_SPACE_URL environment variable is not set.")

CONFIG_FILE = "server_email_config.json"

# -----------------------------
# Load / save per-server Gmail config
# -----------------------------
def load_server_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading server config:", e)
        return {}


def save_server_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print("Error saving server config:", e)


SERVER_CONFIG = load_server_config()


def get_gmail_credentials_for_guild(guild_id: int | None):
    """Return (gmail_address, app_password) for this server, or default env, or (None, None)."""
    if guild_id is not None:
        guild_key = str(guild_id)
        if guild_key in SERVER_CONFIG:
            cfg = SERVER_CONFIG[guild_key]
            return cfg.get("gmail_address"), cfg.get("gmail_app_password")

    # Fallback to global default
    if DEFAULT_GMAIL_ADDRESS and DEFAULT_GMAIL_APP_PASSWORD:
        return DEFAULT_GMAIL_ADDRESS, DEFAULT_GMAIL_APP_PASSWORD

    return None, None


# -----------------------------
# Discord bot setup
# -----------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print("Slash commands synced:", [cmd.name for cmd in synced])
    except Exception as e:
        print("Error syncing commands:", e)


# -----------------------------
# Helper: call Hugging Face Space
# -----------------------------
def generate_email_from_space(prompt: str) -> str | None:
    """
    Sends a POST request to your HF Space:
      POST HF_SPACE_URL with JSON: {"prompt": "..."}
    Expects response JSON: {"email": "..."}
    """
    try:
        resp = requests.post(
            HF_SPACE_URL,
            json={"prompt": prompt},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        email_text = data.get("email")
        if not email_text:
            print("HF response missing 'email' key:", data)
            return None
        return email_text
    except Exception as e:
        print("Error calling HF Space:", e)
        return None


# -----------------------------
# Helper: send email via Gmail
# -----------------------------
def send_email(
    from_gmail: str,
    app_password: str,
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """
    Sends an email using Gmail SMTP from from_gmail to to_email.
    """
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_gmail
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_gmail, app_password)
            smtp.send_message(msg)

        print(f"Email sent successfully from {from_gmail} to {to_email}")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


# -----------------------------
# /setserveremail – bind this server to a Gmail account
# -----------------------------
@bot.tree.command(
    name="setserveremail",
    description="(Admin only) Configure which Gmail account this server uses to send emails."
)
@app_commands.describe(
    gmail_address="The Gmail address to send from (use a bot-only Gmail!).",
    app_password="The 16-character Gmail app password for that account."
)
@app_commands.checks.has_permissions(administrator=True)
async def setserveremail_command(
    interaction: discord.Interaction,
    gmail_address: str,
    app_password: str
):
    if interaction.guild_id is None:
        return await interaction.response.send_message(
            "❌ This command can only be used in a server, not in DMs.",
            ephemeral=True,
        )

    guild_key = str(interaction.guild_id)

    # Update in-memory config
    SERVER_CONFIG[guild_key] = {
        "gmail_address": gmail_address,
        "gmail_app_password": app_password,
    }
    save_server_config(SERVER_CONFIG)

    # Do NOT echo the password back.
    await interaction.response.send_message(
        f"✅ This server is now configured to send email from **{gmail_address}**.\n"
        "Make sure this is a bot-only Gmail account, not a personal one.",
        ephemeral=True,  # keep setup private
    )


@setserveremail_command.error
async def setserveremail_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        # If they don't have admin perms
        try:
            await interaction.response.send_message(
                "❌ You must be a server administrator to use /setserveremail.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "❌ You must be a server administrator to use /setserveremail.",
                ephemeral=True,
            )
    else:
        print("Error in /setserveremail:", error)


# -----------------------------
# /sendemail – user writes the full email and it gets sent
# -----------------------------
@bot.tree.command(
    name="sendemail",
    description="Send a custom email to a specific address from this server's configured Gmail."
)
@app_commands.describe(
    to_email="The recipient's email address (e.g. someone@gmail.com).",
    subject="The subject line of the email.",
    message="The full text of the email body."
)
async def sendemail_command(
    interaction: discord.Interaction,
    to_email: str,
    subject: str,
    message: str
):
    await interaction.response.defer()

    from_gmail, app_password = get_gmail_credentials_for_guild(interaction.guild_id)
    if not from_gmail or not app_password:
        return await interaction.followup.send(
            "❌ This server's Gmail is not configured yet.\n"
            "An admin should run `/setserveremail` first, "
            "or set GMAIL_ADDRESS and GMAIL_APP_PASSWORD as defaults on the bot.",
        )

    success = send_email(from_gmail, app_password, to_email, subject, message)

    if success:
        await interaction.followup.send(
            f"✅ Email sent from **{from_gmail}** to **{to_email}** with subject **{subject}**."
        )
    else:
        await interaction.followup.send(
            "❌ There was an error sending your email. Check the server logs."
        )


# -----------------------------
# /draftemail – ONLY drafts, does NOT send
# -----------------------------
@bot.tree.command(
    name="draftemail",
    description="Use AI to draft an email from an idea (does NOT send it)."
)
@app_commands.describe(
    idea="Describe what the email should say."
)
async def draftemail_command(
    interaction: discord.Interaction,
    idea: str
):
    await interaction.response.defer()
    await interaction.followup.send("✏️ Generating your email with AI…")

    email_text = generate_email_from_space(idea)
    if not email_text:
        return await interaction.followup.send(
            "❌ AI failed to generate an email. Check the server logs."
        )

    preview = f"📝 **Drafted email (not sent):**\n```text\n{email_text}\n```"
    await interaction.followup.send(preview)


# -----------------------------
# Run the bot
# -----------------------------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
