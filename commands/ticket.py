import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio
from utils.db import get_firebase_db, categories
from utils.styles import Colors, Emojis, Titles, Messages, Footers
from views.create_ticket import (
    TicketCreateModal, CategorySelectionView, PublicCategorySelectionView
)
from views.manage_ticket import AcceptTicketView, notify_mentors
from views.mentor_action import MentorActionView
from views.hacker_action import UserTicketView
from views.select_channel import ChannelSetupView

class Ticket(commands.Cog):
    """
    All commands associated with opening, closing, and editing tickets.
    """
    def __init__(self, bot):
        self.bot = bot
        self.db = get_firebase_db()

    def get_ticket_by_id(self, ticket_id):
        """Get ticket by ID"""
        return self.db.get_ticket_by_id(ticket_id)

    def get_user_tickets(self, user_id):
        """Get all tickets for a specific user"""
        return self.db.get_user_tickets(user_id)

    def get_open_tickets(self):
        """Get all open tickets"""
        return self.db.get_open_tickets()

    @commands.command(name='create')
    async def create_ticket(self, ctx):
        """Create a new ticket with category selection"""
        ticket_channel_id = self.db.get_dev_config('ticket_channel')
        if ticket_channel_id and str(ctx.channel.id) != ticket_channel_id:
            embed = discord.Embed(
                title=Titles.WRONG_CHANNEL,
                description=Messages.WRONG_CHANNEL_MSG,
                color=Colors.RED
            )
            await ctx.send(embed=embed)
            return

        user_tickets = self.get_user_tickets(ctx.author.id)
        open_tickets = [t for t in user_tickets if t['status'] == 'open']
        
        if len(open_tickets) > 5:
            embed = discord.Embed(
                title=Titles.TOO_MANY_TICKETS,
                description=Messages.TOO_MANY_TICKETS_MSG,
                color=Colors.RED
            )
            await ctx.send(embed=embed)
            return

        view = CategorySelectionView(ctx.author.id)
        embed = discord.Embed(
            title="Need 1:1 mentor help?",
            description="Select a technology you need help with and follow the instructions!",
            color=Colors.GREEN
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name='list')
    async def list_tickets(self, ctx):
        """List your tickets"""
        user_tickets = self.get_user_tickets(ctx.author.id)
        
        if not user_tickets:
            embed = discord.Embed(
                title=Titles.YOUR_TICKETS,
                description=Messages.NO_TICKETS,
                color=Colors.GRAY
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=Titles.YOUR_TICKETS,
            description=f"You have {len(user_tickets)} ticket(s):",
            color=Colors.GREEN
        )

        for ticket in user_tickets:
            status_emoji = Emojis.OPEN_TICKET if ticket['status'] == 'open' else Emojis.CLOSED_TICKET
            mentor_info = f"Assigned to {ticket['mentor_name']}" if ticket['mentor_name'] else "Unassigned"
            
            categories_info = ""
            if ticket.get('categories'):
                categories_info = f"\n**Categories:** {', '.join(ticket['categories'])}"
            
            title_info = f"\n**Title:** {ticket.get('title', 'No title')}"
            location_info = f"\n**Location:** {ticket.get('location', 'No location')}"
            
            embed.add_field(
                name=f"{status_emoji} Ticket #{ticket['id']}",
                value=f"**Status:** {ticket['status'].title()}{title_info}{location_info}\n**Description:** {ticket['description'][:100]}...\n**Mentor:** {mentor_info}{categories_info}\n**Created:** {ticket['created_at'][:10]}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='info')
    async def ticket_info(self, ctx, ticket_id: str):
        """Get detailed information about a ticket"""
        ticket = self.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await ctx.send(f"{Emojis.ERROR} {Messages.TICKET_NOT_FOUND_MSG}.")
            return

        mentor_role = discord.utils.get(ctx.guild.roles, name="Mentor")
        is_mentor = mentor_role and mentor_role in ctx.author.roles
        
        if ticket['user_id'] != ctx.author.id and not is_mentor:
            await ctx.send(f"{Emojis.ERROR} You can only view your own tickets.")
            return

        embed = discord.Embed(
            title=f"{Emojis.TICKET} Ticket #{ticket['id']}",
            color=Colors.GREEN if ticket['status'] == 'open' else Colors.RED_STATUS
        )
        
        embed.add_field(name="Status", value=ticket['status'].title(), inline=True)
        embed.add_field(name="Created By", value=ticket['user_name'], inline=True)
        embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
        embed.add_field(name="Location", value=ticket.get('location', 'No location'), inline=True)
        embed.add_field(name="Description", value=ticket['description'], inline=False)
        
        if ticket.get('categories'):
            embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=False)
        
        embed.add_field(name="Created", value=ticket['created_at'], inline=True)
        
        if ticket['mentor_name']:
            embed.add_field(name="Assigned Mentor", value=ticket['mentor_name'], inline=True)
        
        if ticket['closed_at']:
            embed.add_field(name="Closed", value=ticket['closed_at'], inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='close_ticket')
    async def close_ticket(self, ctx, ticket_id: str):
        """Close a ticket"""
        ticket = self.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await ctx.send(f"{Emojis.ERROR} {Messages.TICKET_NOT_FOUND_MSG}.")
            return

        if ticket['user_id'] != ctx.author.id:
            await ctx.send(f"{Emojis.ERROR} You can only close your own tickets.")
            return

        if ticket['status'] == 'closed':
            await ctx.send(f"{Emojis.ERROR} This ticket is already closed.")
            return

        success = self.db.close_ticket(ticket_id)
        if not success:
            await ctx.send(f"{Emojis.ERROR} Failed to close ticket. Please try again.")
            return

        embed = discord.Embed(
            title=Titles.TICKET_CLOSED,
            description=f"Ticket #{ticket_id} has been closed.",
            color=Colors.GRAY
        )
        embed.add_field(name="Closed By", value=ctx.author.display_name, inline=True)
        embed.add_field(name="Closed At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='config')
    @commands.has_permissions(administrator=True)
    async def config_channels(self, ctx, ticket_channel: discord.TextChannel, mentor_channel: discord.TextChannel):
        """Configure bot channels (Admin only)"""
        try:
            self.db.set_dev_config('ticket_channel', str(ticket_channel.id))
            self.db.set_dev_config('mentor_channel', str(mentor_channel.id))
            
            embed = discord.Embed(
                title=Titles.CONFIG_SUCCESS,
                description="Bot channels configured successfully!",
                color=Colors.GREEN
            )
            embed.add_field(name="Ticket Channel", value=ticket_channel.mention, inline=True)
            embed.add_field(name="Mentor Channel", value=mentor_channel.mention, inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"{Emojis.ERROR} Failed to configure channels: {e}")

    @commands.command(name='post')
    @commands.has_permissions(administrator=True)
    async def post_ticket_interface(self, ctx):
        """Post the interactive ticket creation interface (Admin only)"""
        embed = discord.Embed(
            title="Need 1:1 mentor help?",
            description="Select a technology you need help with and follow the instructions!",
            color=Colors.GREEN
        )
        
        view = PublicCategorySelectionView()
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='setup')
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Interactive channel setup using dropdowns (Admin only)"""
        try:
            self.db.set_dev_config('counter', '0')
        except:
            pass 
        
        embed = discord.Embed(
            title="🔧 Configure Mentorship Channels",
            description="Ticket creation channel: This will be where hackers can post tickets.\nMentor notification channel: This will be where mentors can accept and resolve open tickets.",
            color=Colors.GREEN
        )
        
        view = ChannelSetupView()
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
