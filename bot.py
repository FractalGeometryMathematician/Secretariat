import os
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
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
HF_SPACE_URL = os.getenv("HF_SPACE_URL")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
if not GMAIL_ADDRESS:
    raise RuntimeError("GMAIL_ADDRESS environment variable is not set.")
if not GMAIL_APP_PASSWORD:
    raise RuntimeError("GMAIL_APP_PASSWORD environment variable is not set.")
if not HF_SPACE_URL:
    HF_SPACE_URL = "https://vinthebest-secretariat.hf.space/generate"
    print(f"HF_SPACE_URL not set, using default: {HF_SPACE_URL}")

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
def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using Gmail SMTP from GMAIL_ADDRESS to to_email.
    """
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


# -----------------------------
# /sendemail – user writes the full email
# -----------------------------
@bot.tree.command(
    name="sendemail",
    description="Send a custom email to a specific address."
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
    # Public response (no ephemeral=True)
    await interaction.response.defer()

    success = send_email(to_email, subject, message)

    if success:
        await interaction.followup.send(
            f"✅ Email sent to **{to_email}** with subject **{subject}**."
        )
    else:
        await interaction.followup.send(
            "❌ There was an error sending your email. Check the server logs."
        )


# -----------------------------
# /draftemail – AI drafts the email, then sends it
# -----------------------------
@bot.tree.command(
    name="draftemail",
    description="Use AI to draft an email from an idea, then send it."
)
@app_commands.describe(
    to_email="The recipient's email address (e.g. someone@gmail.com).",
    subject="The subject line of the email.",
    idea="Describe what the email should say."
)
async def draftemail_command(
    interaction: discord.Interaction,
    to_email: str,
    subject: str,
    idea: str
):
    # Public response (no ephemeral=True)
    await interaction.response.defer()
    await interaction.followup.send("✏️ Generating your email with AI…")

    email_text = generate_email_from_space(idea)
    if not email_text:
        return await interaction.followup.send(
            "❌ AI failed to generate an email. Check the server logs."
        )

    success = send_email(to_email, subject, email_text)

    if success:
        preview = f"**To:** {to_email}\n**Subject:** {subject}\n\n**Body:**\n{email_text}"
        await interaction.followup.send(
            "✅ Email generated and sent!\n\n" + preview
        )
    else:
        await interaction.followup.send(
            "❌ Generated the email, but sending failed. Check the logs."
        )


# -----------------------------
# Run the bot
# -----------------------------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
