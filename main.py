import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

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

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="!help for commands"))

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        logger.error(f"Unhandled error: {error}")
        await ctx.send("❌ An unexpected error occurred. Please try again.")

@bot.command(name='help')
async def help_command(ctx):
    """Display help information"""
    embed = discord.Embed(
        title="🎫 Ticket Bot Help",
        description="Welcome to Garuda Hacks 6.0!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📝 User Commands",
        value="""
        `!ticket create <description>` - Create a new ticket
        `!ticket list` - List your tickets
        `!ticket close <ticket_id>` - Close your ticket
        `!ticket info <ticket_id>` - Get ticket information
        """,
        inline=False
    )
    
    embed.add_field(
        name="👨‍🏫 Mentor Commands",
        value="""
        `!mentor tickets` - View all open tickets
        `!mentor accept <ticket_id>` - Accept a ticket
        `!mentor close <ticket_id>` - Close a ticket as mentor
        `!mentor assign <ticket_id> <user>` - Assign ticket to another mentor
        """,
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value="""
        `!setup` - Set up the bot (Admin only)
        `!config` - View bot configuration
        """,
        inline=False
    )
    
    embed.set_footer(text="Use !help <command> for detailed information about a specific command")
    await ctx.send(embed=embed)

@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Set up the bot for the server (Admin only)"""
    embed = discord.Embed(
        title="🔧 Bot Setup",
        description="Setting up ticket management system...",
        color=0x00ff00
    )
    
    # create ticket category if it doesn't exist
    category_name = "🎫 Tickets"
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    
    if not category:
        try:
            category = await ctx.guild.create_category(category_name)
            embed.add_field(name="✅ Category Created", value=f"Created '{category_name}' category", inline=False)
        except discord.Forbidden:
            embed.add_field(name="❌ Permission Error", value="Bot needs 'Manage Channels' permission", inline=False)
            await ctx.send(embed=embed)
            return
    
    # create a mentor role if it doesn't yet exist
    mentor_role_name = "Mentor"
    mentor_role = discord.utils.get(ctx.guild.roles, name=mentor_role_name)
    
    if not mentor_role:
        try:
            mentor_role = await ctx.guild.create_role(
                name=mentor_role_name,
                color=0x00ff00,
                reason="Ticket bot setup - Mentor role"
            )
            embed.add_field(name="✅ Mentor Role Created", value=f"Created '{mentor_role_name}' role", inline=False)
        except discord.Forbidden:
            embed.add_field(name="❌ Permission Error", value="Bot needs 'Manage Roles' permission", inline=False)
    
    embed.add_field(name="🎉 Setup Complete", value="The bot is ready to handle tickets!", inline=False)
    await ctx.send(embed=embed)

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
