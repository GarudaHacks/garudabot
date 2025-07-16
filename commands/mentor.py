import discord
from discord.ext import commands
from datetime import datetime
from utils.db import get_firebase_db
from utils.styles import Colors, Emojis, Titles, Messages, Footers

class Mentor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_firebase_db()

    def get_ticket_by_id(self, ticket_id):
        """Get ticket by ID"""
        return self.db.get_ticket_by_id(ticket_id)

    def get_open_tickets(self):
        """Get all open tickets"""
        return self.db.get_open_tickets()

    def is_mentor(self, ctx):
        """Check if user has mentor role"""
        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        return mentor_role and mentor_role in ctx.author.roles

    @commands.command(name='tickets')
    async def view_tickets(self, ctx):
        """View all open tickets (Mentor only)"""
        if not self.is_mentor(ctx):
            await ctx.send(f"{Emojis.ERROR} {Messages.MENTOR_ROLE_REQUIRED}.")
            return

        open_tickets = self.get_open_tickets()

        if not open_tickets:
            embed = discord.Embed(
                title=Titles.OPEN_TICKETS,
                description=Messages.NO_OPEN_TICKETS,
                color=Colors.GREEN
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=Titles.OPEN_TICKETS,
            description=f"There are {len(open_tickets)} open ticket(s):",
            color=Colors.DEFAULT
        )

        for ticket in open_tickets:
            mentor_status = f"Assigned to {ticket['mentor_name']}" if ticket['mentor_name'] else "**Unassigned**"
            
            categories_info = ""
            if ticket.get('categories'):
                categories_info = f"\n**Categories:** {', '.join(ticket['categories'])}"
            
            title_info = f"\n**Title:** {ticket.get('title', 'No title')}"
            location_info = f"\n**Location:** {ticket.get('location', 'No location')}"
            
            embed.add_field(
                name=f"{Emojis.TICKET} Ticket #{ticket['id']}",
                value=f"**User:** {ticket['user_name']}{title_info}{location_info}\n**Description:** {ticket['description'][:100]}...\n**Mentor:** {mentor_status}{categories_info}\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='accept')
    async def accept_ticket(self, ctx, ticket_id: str):
        """Accept a ticket (Mentor only)"""
        if not self.is_mentor(ctx):
            await ctx.send(f"{Emojis.ERROR} {Messages.MENTOR_ROLE_REQUIRED}.")
            return

        ticket = self.get_ticket_by_id(ticket_id)

        if not ticket:
            await ctx.send(f"{Emojis.ERROR} {Messages.TICKET_NOT_FOUND_MSG}.")
            return

        if ticket['status'] != 'open':
            await ctx.send(f"{Emojis.ERROR} This ticket is not open.")
            return

        if ticket['mentor_id']:
            await ctx.send(f"{Emojis.ERROR} This ticket is already assigned to {ticket['mentor_name']}.")
            return

        success = self.db.assign_ticket(ticket_id, ctx.author.id, ctx.author.display_name)
        
        if not success:
            await ctx.send(f"{Emojis.ERROR} Failed to assign ticket. Please try again.")
            return

        embed = discord.Embed(
            title=Titles.TICKET_ACCEPTED,
            description=f"{Messages.TICKET_ACCEPTED_SUCCESS} #{ticket_id}",
            color=Colors.GREEN
        )
        embed.add_field(name="User", value=ticket['user_name'], inline=True)
        embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
        embed.add_field(name="Description", value=ticket['description'], inline=False)
        embed.add_field(name="Location", value=ticket.get('location', 'No location'), inline=False)
        if ticket.get('categories'):
            embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=False)
        embed.add_field(name="Accepted At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)

        await ctx.send(embed=embed)

        # notify the user
        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_ASSIGNED,
                description=Messages.TICKET_ASSIGNED_SUCCESS,
                color=Colors.GREEN
            )
            user_embed.add_field(name="Mentor", value=ctx.author.display_name, inline=True)
            user_embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
            user_embed.add_field(name="Description", value=ticket['description'], inline=False)
            await user.send(embed=user_embed)
        except:
            pass

    @commands.command(name='resolve')
    async def close_ticket(self, ctx, ticket_id: str):
        """Close a ticket as mentor (Mentor only)"""
        if not self.is_mentor(ctx):
            await ctx.send(f"{Emojis.ERROR} {Messages.MENTOR_ROLE_REQUIRED}.")
            return

        ticket = self.get_ticket_by_id(ticket_id)

        if not ticket:
            await ctx.send(f"{Emojis.ERROR} {Messages.TICKET_NOT_FOUND_MSG}.")
            return

        if ticket['status'] == 'closed':
            await ctx.send(f"{Emojis.ERROR} This ticket is already closed.")
            return

        if ticket['mentor_id'] != ctx.author.id:
            await ctx.send(f"{Emojis.ERROR} You can only close tickets assigned to you.")
            return

        success = self.db.close_ticket(ticket_id)
        if not success:
            await ctx.send(f"{Emojis.ERROR} Failed to close ticket. Please try again.")
            return

        embed = discord.Embed(
            title=Titles.TICKET_CLOSED,
            description=f"Ticket #{ticket_id} has been closed by mentor.",
            color=Colors.GRAY
        )
        embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
        embed.add_field(name="User", value=ticket['user_name'], inline=True)
        embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
        embed.add_field(name="Closed At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)

        await ctx.send(embed=embed)

        # notify the user
        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_CLOSED,
                description=f"Your ticket #{ticket_id} has been closed by your mentor.",
                color=Colors.GRAY
            )
            user_embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
            await user.send(embed=user_embed)
        except:
            pass

    @commands.command(name='assign')
    async def assign_ticket(self, ctx, ticket_id: str, member: discord.Member):
        """Assign a ticket to another mentor (Mentor only)"""
        if not self.is_mentor(ctx):
            await ctx.send(f"{Emojis.ERROR} {Messages.MENTOR_ROLE_REQUIRED}.")
            return

        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        if not mentor_role or mentor_role not in member.roles:
            await ctx.send(f"{Emojis.ERROR} You can only assign tickets to other mentors.")
            return

        ticket = self.get_ticket_by_id(ticket_id)

        if not ticket:
            await ctx.send(f"{Emojis.ERROR} {Messages.TICKET_NOT_FOUND_MSG}.")
            return

        if ticket['status'] != 'open':
            await ctx.send(f"{Emojis.ERROR} This ticket is not open.")
            return

        if ticket['mentor_id'] != ctx.author.id:
            await ctx.send(f"{Emojis.ERROR} You can only reassign tickets assigned to you.")
            return

        success = self.db.reassign_ticket(ticket_id, member.id, member.display_name)
        if not success:
            await ctx.send(f"{Emojis.ERROR} Failed to reassign ticket. Please try again.")
            return

        embed = discord.Embed(
            title=Titles.TICKET_REASSIGNED,
            description=f"Ticket #{ticket_id} has been reassigned to {member.display_name}.",
            color=Colors.GREEN
        )
        embed.add_field(name="Reassigned By", value=ctx.author.display_name, inline=True)
        embed.add_field(name="New Mentor", value=member.display_name, inline=True)
        embed.add_field(name="User", value=ticket['user_name'], inline=True)

        await ctx.send(embed=embed)

        # notify the new mentor
        try:
            mentor_embed = discord.Embed(
                title=Titles.TICKET_ASSIGNED,
                description=f"You have been assigned ticket #{ticket_id}",
                color=Colors.GREEN
            )
            mentor_embed.add_field(name="User", value=ticket['user_name'], inline=True)
            mentor_embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
            mentor_embed.add_field(name="Description", value=ticket['description'], inline=False)
            await member.send(embed=mentor_embed)
        except:
            pass

        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_ASSIGNED,
                description=f"Your ticket #{ticket_id} has been reassigned to a new mentor.",
                color=Colors.GREEN
            )
            user_embed.add_field(name="New Mentor", value=member.display_name, inline=True)
            await user.send(embed=user_embed)
        except:
            pass

    @commands.command(name='my')
    async def my_tickets(self, ctx):
        """View your assigned tickets (Mentor only)"""
        if not self.is_mentor(ctx):
            await ctx.send(f"{Emojis.ERROR} {Messages.MENTOR_ROLE_REQUIRED}.")
            return

        mentor_tickets = self.db.get_mentor_tickets(ctx.author.id)

        if not mentor_tickets:
            embed = discord.Embed(
                title=Titles.MY_TICKETS,
                description="You have no assigned tickets.",
                color=Colors.GRAY
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=Titles.MY_TICKETS,
            description=f"You have {len(mentor_tickets)} assigned ticket(s):",
            color=Colors.GREEN
        )

        for ticket in mentor_tickets:
            status_emoji = Emojis.OPEN_TICKET if ticket['status'] == 'open' else Emojis.CLOSED_TICKET
            
            categories_info = ""
            if ticket.get('categories'):
                categories_info = f"\n**Categories:** {', '.join(ticket['categories'])}"
            
            title_info = f"\n**Title:** {ticket.get('title', 'No title')}"
            location_info = f"\n**Location:** {ticket.get('location', 'No location')}"
            
            embed.add_field(
                name=f"{status_emoji} Ticket #{ticket['id']}",
                value=f"**Status:** {ticket['status'].title()}{title_info}{location_info}\n**User:** {ticket['user_name']}\n**Description:** {ticket['description'][:100]}...{categories_info}\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Mentor(bot))


