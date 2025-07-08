import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class Mentor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = "tickets.json"

    def load_tickets(self):
        """Load tickets from JSON file"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def save_tickets(self, tickets):
        """Save tickets to JSON file"""
        with open(self.tickets_file, 'w') as f:
            json.dump(tickets, f, indent=2)

    def get_ticket_by_id(self, tickets, ticket_id):
        """Get ticket by ID"""
        for ticket in tickets:
            if ticket['id'] == ticket_id:
                return ticket
        return None

    def is_mentor(self, ctx):
        """Check if user has mentor role"""
        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        return mentor_role and mentor_role in ctx.author.roles

    @commands.group(name='mentor', invoke_without_command=True)
    async def mentor(self, ctx):
        """Mentor management commands"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use these commands.")
            return
        await ctx.send("Use `!help mentor` to see available mentor commands.")

    @mentor.command(name='tickets')
    async def view_tickets(self, ctx):
        """View all open tickets"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use this command.")
            return

        tickets = self.load_tickets()
        open_tickets = [ticket for ticket in tickets if ticket['status'] == 'open']

        if not open_tickets:
            embed = discord.Embed(
                title="📝 Open Tickets",
                description="No open tickets at the moment!",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📝 Open Tickets",
            description=f"There are {len(open_tickets)} open ticket(s):",
            color=0xffff00
        )

        for ticket in open_tickets:
            mentor_status = f"Assigned to {ticket['mentor_name']}" if ticket['mentor_name'] else "**Unassigned**"
            
            embed.add_field(
                name=f"🎫 Ticket #{ticket['id']}",
                value=f"**User:** {ticket['user_name']}\n**Description:** {ticket['description'][:100]}...\n**Mentor:** {mentor_status}\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        embed.set_footer(text="Use !mentor accept <ticket_id> to accept a ticket")
        await ctx.send(embed=embed)

    @mentor.command(name='accept')
    async def accept_ticket(self, ctx, ticket_id: int):
        """Accept a ticket"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use this command.")
            return

        tickets = self.load_tickets()
        ticket = self.get_ticket_by_id(tickets, ticket_id)

        if not ticket:
            await ctx.send("❌ Ticket not found.")
            return

        if ticket['status'] != 'open':
            await ctx.send("❌ This ticket is not open.")
            return

        if ticket['mentor_id']:
            await ctx.send(f"❌ This ticket is already assigned to {ticket['mentor_name']}.")
            return

        ticket['mentor_id'] = ctx.author.id
        ticket['mentor_name'] = ctx.author.display_name
        self.save_tickets(tickets)

        embed = discord.Embed(
            title="✅ Ticket Accepted",
            description=f"You have accepted Ticket #{ticket_id}",
            color=0x00ff00
        )
        embed.add_field(name="User", value=ticket['user_name'], inline=True)
        embed.add_field(name="Description", value=ticket['description'], inline=False)
        embed.add_field(name="Accepted At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)

        await ctx.send(embed=embed)

        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title="🎫 Ticket Assigned",
                description=f"Your ticket #{ticket_id} has been assigned to a mentor!",
                color=0x00ff00
            )
            user_embed.add_field(name="Mentor", value=ctx.author.display_name, inline=True)
            user_embed.add_field(name="Description", value=ticket['description'], inline=False)
            await user.send(embed=user_embed)
        except:
            pass

    @mentor.command(name='close')
    async def close_ticket(self, ctx, ticket_id: int):
        """Close a ticket as mentor"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use this command.")
            return

        tickets = self.load_tickets()
        ticket = self.get_ticket_by_id(tickets, ticket_id)

        if not ticket:
            await ctx.send("❌ Ticket not found.")
            return

        if ticket['status'] == 'closed':
            await ctx.send("❌ This ticket is already closed.")
            return

        if ticket['mentor_id'] != ctx.author.id:
            await ctx.send("❌ You can only close tickets assigned to you.")
            return

        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.now().isoformat()
        self.save_tickets(tickets)

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"Ticket #{ticket_id} has been closed by mentor.",
            color=0xff0000
        )
        embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
        embed.add_field(name="User", value=ticket['user_name'], inline=True)
        embed.add_field(name="Closed At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)

        await ctx.send(embed=embed)

        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"Your ticket #{ticket_id} has been closed by your mentor.",
                color=0xff0000
            )
            user_embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
            await user.send(embed=user_embed)
        except:
            pass

    @mentor.command(name='assign')
    async def assign_ticket(self, ctx, ticket_id: int, member: discord.Member):
        """Assign a ticket to another mentor"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use this command.")
            return

        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        if not mentor_role or mentor_role not in member.roles:
            await ctx.send("❌ You can only assign tickets to other mentors.")
            return

        tickets = self.load_tickets()
        ticket = self.get_ticket_by_id(tickets, ticket_id)

        if not ticket:
            await ctx.send("❌ Ticket not found.")
            return

        if ticket['status'] != 'open':
            await ctx.send("❌ This ticket is not open.")
            return

        if ticket['mentor_id'] != ctx.author.id:
            await ctx.send("❌ You can only reassign tickets assigned to you.")
            return

        old_mentor = ticket['mentor_name']
        ticket['mentor_id'] = member.id
        ticket['mentor_name'] = member.display_name
        self.save_tickets(tickets)

        embed = discord.Embed(
            title="🔄 Ticket Reassigned",
            description=f"Ticket #{ticket_id} has been reassigned.",
            color=0x00ff00
        )
        embed.add_field(name="From", value=old_mentor, inline=True)
        embed.add_field(name="To", value=member.display_name, inline=True)
        embed.add_field(name="User", value=ticket['user_name'], inline=True)

        await ctx.send(embed=embed)

        try:
            new_mentor_embed = discord.Embed(
                title="🎫 Ticket Assigned to You",
                description=f"You have been assigned Ticket #{ticket_id}",
                color=0x00ff00
            )
            new_mentor_embed.add_field(name="User", value=ticket['user_name'], inline=True)
            new_mentor_embed.add_field(name="Description", value=ticket['description'], inline=False)
            await member.send(embed=new_mentor_embed)
        except:
            pass

        try:
            user = await self.bot.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title="🔄 Mentor Changed",
                description=f"Your ticket #{ticket_id} has been reassigned to a new mentor.",
                color=0x00ff00
            )
            user_embed.add_field(name="New Mentor", value=member.display_name, inline=True)
            await user.send(embed=user_embed)
        except:
            pass

    @mentor.command(name='my')
    async def my_tickets(self, ctx):
        """View tickets assigned to you"""
        if not self.is_mentor(ctx):
            await ctx.send("❌ You need the Mentor role to use this command.")
            return

        tickets = self.load_tickets()
        my_tickets = [ticket for ticket in tickets if ticket['mentor_id'] == ctx.author.id]

        if not my_tickets:
            embed = discord.Embed(
                title="📝 Your Assigned Tickets",
                description="You don't have any assigned tickets.",
                color=0x808080
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📝 Your Assigned Tickets",
            description=f"You have {len(my_tickets)} assigned ticket(s):",
            color=0x00ff00
        )

        for ticket in my_tickets:
            status_emoji = "🟢" if ticket['status'] == 'open' else "🔴"
            
            embed.add_field(
                name=f"{status_emoji} Ticket #{ticket['id']}",
                value=f"**User:** {ticket['user_name']}\n**Status:** {ticket['status'].title()}\n**Description:** {ticket['description'][:100]}...\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Mentor(bot))


