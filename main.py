import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import ssl
import certifi
import json
from utils.styles import Colors, Emojis, Titles, Messages, Footers

load_dotenv()

# Environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS")

# Validate required environment variables
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

if not FIREBASE_PROJECT_ID:
    raise ValueError("FIREBASE_PROJECT_ID environment variable is required")

# Validate Firebase credentials
if FIREBASE_CREDENTIALS_JSON:
    credentials_path = "/tmp/firebase-credentials.json"
    with open(credentials_path, 'w') as f:
        json.dump(json.loads(FIREBASE_CREDENTIALS_JSON), f)
    FIREBASE_CREDENTIALS_PATH = credentials_path
elif not FIREBASE_CREDENTIALS_PATH:
    raise ValueError("Either FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_PATH must be set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# initialize firebase
from utils.db import init_firebase_db
init_firebase_db(FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID)
logger.info("Firebase database initialized successfully")

# bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

# Configure SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    await bot.change_presence(activity=discord.Game(name="!help for commands"))
    await post_ticket_interface_in_channels()

async def post_ticket_interface_in_channels():
    """Post the ticket creation interface in configured channels"""
    from utils.db import get_firebase_db
    from views.create_ticket import PublicCategorySelectionView
    from utils.styles import Colors
    
    db = get_firebase_db()
    ticket_channel_id = db.get_dev_config('ticket_channel')
    
    if not ticket_channel_id:
        logger.info("No ticket channel configured. Use !setup to set up channels.")
        return
    
    try:
        for guild in bot.guilds:
            ticket_channel = guild.get_channel(int(ticket_channel_id))
            if ticket_channel:
                async for message in ticket_channel.history(limit=50):
                    if message.author == bot.user and message.embeds:
                        for embed in message.embeds:
                            if embed.title == "Need 1:1 mentor help?":
                                logger.info(f"Ticket interface already exists in {guild.name}")
                                return
                
                embed = discord.Embed(
                    title="Need 1:1 mentor help?",
                    description="Select a technology you need help with and follow the instructions!",
                    color=Colors.GREEN
                )
                
                view = PublicCategorySelectionView()
                await ticket_channel.send(embed=embed, view=view)
                logger.info(f"Posted ticket interface in {guild.name}")
                
    except Exception as e:
        logger.error(f"Failed to post ticket interface: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"{Emojis.ERROR} Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{Emojis.ERROR} You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"{Emojis.ERROR} Missing required argument: {error.param}")
    else:
        logger.error(f"Unhandled error: {error}")
        await ctx.send(f"{Emojis.ERROR} An unexpected error occurred. Please try again.")

@bot.command(name='help')
async def help_command(ctx):
    """Display help information"""
    embed = discord.Embed(
        title="🎫 Ticket Bot Help",
        description="Welcome to Garuda Hacks 6.0!",
        color=Colors.DEFAULT
    )
    
    embed.add_field(
        name=f"{Emojis.HACKER_COMMANDS} Hacker Commands",
        value="""
        `!create` - Create a new ticket (with category selection)
        `!list` - List your tickets
        `!close_ticket <ticket_id>` - Close your ticket
        `!info <ticket_id>` - Get ticket information
        """,
        inline=False
    )
    
    embed.add_field(
        name=f"{Emojis.MENTOR_COMMANDS} Mentor Commands",
        value="""
        `!mentor tickets` - View all open tickets
        `!mentor accept <ticket_id>` - Accept a ticket
        `!mentor resolve <ticket_id>` - Close a ticket as mentor
        `!mentor assign <ticket_id> <user>` - Assign ticket to another mentor
        `!mentor my` - View your assigned tickets
        """,
        inline=False
    )
    
    embed.add_field(
        name=f"{Emojis.ADMIN_COMMANDS} Admin Commands",
        value="""
        `!setup` - Configure channels interactively (Admin only)
        `!post` - Post the interactive ticket creation interface (Admin only)
        `!post_interface` - Manually post ticket interface in configured channels (Admin only)
        """,
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='post_interface')
@commands.has_permissions(administrator=True)
async def post_interface(ctx):
    """Manually post the ticket creation interface (Admin only)"""
    await post_ticket_interface_in_channels()
    await ctx.send(f"{Emojis.SUCCESS} Ticket interface posted in configured channels!")

# Load command cogs
async def load_extensions():
    """Load all command extensions"""
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'commands.{filename[:-3]}')
                logger.info(f'Loaded extension: {filename}')
            except Exception as e:
                logger.error(f'Failed to load extension {filename}: {e}')

# Run the bot
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
