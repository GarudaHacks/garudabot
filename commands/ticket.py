import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = "tickets.json"
        self.tickets = self.load_tickets()
        self.ticket_counter = max([ticket['id'] for ticket in self.tickets]) if self.tickets else 0

    def load_tickets(self):
        """Load tickets from JSON file"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def save_tickets(self):
        """Save tickets to JSON file"""
        with open(self.tickets_file, 'w') as f:
            json.dump(self.tickets, f, indent=2)

    def get_ticket_by_id(self, ticket_id):
        """Get ticket by ID"""
        for ticket in self.tickets:
            if ticket['id'] == ticket_id:
                return ticket
        return None

    def get_user_tickets(self, user_id):
        """Get all tickets for a specific user"""
        return [ticket for ticket in self.tickets if ticket['user_id'] == user_id]

    def get_open_tickets(self):
        """Get all open tickets"""
        return [ticket for ticket in self.tickets if ticket['status'] == 'open']

    @commands.group(name='ticket', invoke_without_command=True)
    async def ticket(self, ctx):
        """Ticket management commands"""
        await ctx.send("Use `!help ticket` to see available ticket commands.")

    # /create -- create a new ticktet
    @ticket.command(name='create')
    async def create_ticket(self, ctx, *, description):
        """Create a new ticket"""
        user_tickets = self.get_user_tickets(ctx.author.id)
        open_tickets = [t for t in user_tickets if t['status'] == 'open']
        
        # TODO: should allow any number of tickets
        if open_tickets:
            embed = discord.Embed(
                title="❌ Ticket Already Open",
                description="You already have an open ticket. Please close it before creating a new one.",
                color=0xff0000
            )
            embed.add_field(name="Your Open Ticket", value=f"Ticket #{open_tickets[0]['id']}", inline=False)
            await ctx.send(embed=embed)
            return

        self.ticket_counter += 1
        new_ticket = {
            'id': self.ticket_counter,
            'user_id': ctx.author.id,
            'user_name': ctx.author.display_name,
            'description': description,
            'status': 'open',
            'created_at': datetime.now().isoformat(),
            'mentor_id': None,
            'mentor_name': None,
            'closed_at': None
        }
        
        self.tickets.append(new_ticket)
        self.save_tickets()

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=f"Your ticket has been created successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Ticket ID", value=f"#{new_ticket['id']}", inline=True)
        embed.add_field(name="Status", value="Open", inline=True)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Created", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await ctx.send(embed=embed)

        await self.notify_mentors(ctx, new_ticket)

    # /list -- list all tickets in order of open and closed tickets
    @ticket.command(name='list')
    async def list_tickets(self, ctx):
        """List your tickets"""
        user_tickets = self.get_user_tickets(ctx.author.id)
        
        if not user_tickets:
            embed = discord.Embed(
                title="📝 Your Tickets",
                description="You don't have any tickets yet.",
                color=0x808080
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📝 Your Tickets",
            description=f"You have {len(user_tickets)} ticket(s):",
            color=0x00ff00
        )

        for ticket in user_tickets:
            status_emoji = "🟢" if ticket['status'] == 'open' else "🔴"
            mentor_info = f"Assigned to {ticket['mentor_name']}" if ticket['mentor_name'] else "Unassigned"
            
            embed.add_field(
                name=f"{status_emoji} Ticket #{ticket['id']}",
                value=f"**Status:** {ticket['status'].title()}\n**Description:** {ticket['description'][:100]}...\n**Mentor:** {mentor_info}\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        await ctx.send(embed=embed)

    # /info -- display information on one ticket 
    # TODO: connect with interface for ticket viewing
    @ticket.command(name='info')
    async def ticket_info(self, ctx, ticket_id: int):
        """Get detailed information about a ticket"""
        ticket = self.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await ctx.send("❌ Ticket not found.")
            return

        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        is_mentor = mentor_role and mentor_role in ctx.author.roles
        
        if ticket['user_id'] != ctx.author.id and not is_mentor:
            await ctx.send("❌ You can only view your own tickets.")
            return

        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket['id']}",
            color=0x00ff00 if ticket['status'] == 'open' else 0xff0000
        )
        
        embed.add_field(name="Status", value=ticket['status'].title(), inline=True)
        embed.add_field(name="Created By", value=ticket['user_name'], inline=True)
        embed.add_field(name="Description", value=ticket['description'], inline=False)
        embed.add_field(name="Created", value=ticket['created_at'], inline=True)
        
        if ticket['mentor_name']:
            embed.add_field(name="Assigned Mentor", value=ticket['mentor_name'], inline=True)
        
        if ticket['closed_at']:
            embed.add_field(name="Closed", value=ticket['closed_at'], inline=True)

        await ctx.send(embed=embed)

    @ticket.command(name='close')
    async def close_ticket(self, ctx, ticket_id: int):
        """Close your ticket"""
        ticket = self.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await ctx.send("❌ Ticket not found.")
            return

        if ticket['user_id'] != ctx.author.id:
            await ctx.send("❌ You can only close your own tickets.")
            return

        if ticket['status'] == 'closed':
            await ctx.send("❌ This ticket is already closed.")
            return

        # Close the ticket
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.now().isoformat()
        self.save_tickets()

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"Ticket #{ticket_id} has been closed.",
            color=0xff0000
        )
        embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
        embed.add_field(name="Closed At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await ctx.send(embed=embed)

    # send a message on mentor channel for the ticket
    async def notify_mentors(self, ctx, ticket):
        """Notify mentors about a new ticket"""
        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        if not mentor_role:
            return

        embed = discord.Embed(
            title="🎫 New Ticket Available",
            description=f"A new ticket has been created and needs attention!",
            color=0xffff00
        )
        embed.add_field(name="Ticket ID", value=f"#{ticket['id']}", inline=True)
        embed.add_field(name="User", value=ticket['user_name'], inline=True)
        embed.add_field(name="Description", value=ticket['description'][:200] + "..." if len(ticket['description']) > 200 else ticket['description'], inline=False)
        embed.add_field(name="Action", value="Use `!mentor accept {ticket['id']}` to accept this ticket", inline=False)

        ticket_category = discord.utils.get(ctx.guild.categories, name="🎫 Tickets")
        if ticket_category:
            for channel in ticket_category.channels:
                # TODO: fix matching
                if channel.name == "general" or channel.name == "tickets":
                    await channel.send(content=f"{mentor_role.mention}", embed=embed)
                    return

        await ctx.send(content=f"{mentor_role.mention}", embed=embed)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
