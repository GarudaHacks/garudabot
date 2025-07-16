import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio
from utils.db import get_firebase_db, categories
from utils.styles import Colors, Emojis, Titles, Messages, Footers

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

class TicketCreateModal(discord.ui.Modal, title="Create Ticket"):
    def __init__(self, selected_categories: list):
        super().__init__()
        self.selected_categories = selected_categories
        
        self.title_input = discord.ui.TextInput(
            label="Title",
            placeholder="Brief title for your issue",
            required=True,
            max_length=100
        )
        
        self.description_input = discord.ui.TextInput(
            label="Description",
            placeholder="Describe your issue in detail",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        
        self.location_input = discord.ui.TextInput(
            label="Location",
            placeholder="Where can a mentor find you (on venue or online)?",
            max_length=100,
            required=True
        )
        
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.location_input)

    async def on_submit(self, interaction: discord.Interaction):
        db = get_firebase_db()
        
        ticket = db.create_ticket(
            user_id=interaction.user.id,
            user_name=interaction.user.display_name,
            title=self.title_input.value,
            description=self.description_input.value,
            location=self.location_input.value,
            categories=self.selected_categories
        )
        
        embed = discord.Embed(
            title=Titles.TICKET_CREATED,
            description=f"Ticket #{ticket['id']} has been created successfully!",
            color=Colors.GREEN
        )
        embed.add_field(name="Title", value=ticket['title'], inline=False)
        embed.add_field(name="Description", value=ticket['description'][:200] + "..." if len(ticket['description']) > 200 else ticket['description'], inline=False)
        embed.add_field(name="Location", value=ticket['location'], inline=True)
        if ticket['categories']:
            embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=True)
        embed.add_field(name="Status", value="Open", inline=True)
        embed.add_field(name="Created", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await notify_mentors(interaction, ticket)

class CategorySelectionView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_categories = []
        
        self.add_item(CategorySelect(self.selected_categories))

class PublicCategorySelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  
        self.selected_categories = []
        
        self.add_item(PublicCategorySelect(self.selected_categories))

class CategorySelect(discord.ui.Select):
    def __init__(self, selected_categories: list):
        self.selected_categories = selected_categories
        
        options = []
        for category in categories:
            options.append(discord.SelectOption(
                label=category,
                value=category
            ))
        
        super().__init__(
            placeholder="Make a selection",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This selection is not for you!", ephemeral=True)
            return
        
        self.selected_categories.clear()
        self.selected_categories.extend(self.values)
        
        modal = TicketCreateModal(self.selected_categories)
        await interaction.response.send_modal(modal)

class PublicCategorySelect(discord.ui.Select):
    def __init__(self, selected_categories: list):
        self.selected_categories = selected_categories
        
        options = []
        for category in categories:
            options.append(discord.SelectOption(
                label=category,
                value=category
            ))
        
        super().__init__(
            placeholder="Make a selection",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = get_firebase_db()
        ticket_channel_id = db.get_dev_config('ticket_channel')
        if ticket_channel_id and str(interaction.channel_id) != ticket_channel_id:
            embed = discord.Embed(
                title=Titles.WRONG_CHANNEL,
                description=Messages.WRONG_CHANNEL_MSG,
                color=Colors.RED
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_tickets = db.get_user_tickets(interaction.user.id)
        open_tickets = [t for t in user_tickets if t['status'] == 'open']
        
        if len(open_tickets) > 5:
            embed = discord.Embed(
                title=Titles.TOO_MANY_TICKETS,
                description=Messages.TOO_MANY_TICKETS_MSG,
                color=Colors.RED
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.selected_categories.clear()
        self.selected_categories.extend(self.values)
        
        modal = TicketCreateModal(self.selected_categories)
        await interaction.response.send_modal(modal)

async def notify_mentors(interaction, ticket):
    """Send a new ticket in the mentor channel"""
    try:
        mentor_channel_id = get_firebase_db().get_dev_config('mentor_channel')
        if mentor_channel_id:
            mentor_channel = interaction.guild.get_channel(int(mentor_channel_id))
            if mentor_channel:
                embed = discord.Embed(
                    title=f"Ticket #{ticket['id']}",
                    color=Colors.DEFAULT
                )
                embed.add_field(name="Problem description", value=ticket['description'], inline=False)
                embed.add_field(name="Where to meet", value=ticket['location'], inline=False)
                embed.add_field(name="Helped by:", value="No mentor assigned yet", inline=False)
                
                if ticket['categories']:
                    embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=False)
                
                view = AcceptTicketView(ticket['id'])
                await mentor_channel.send(embed=embed, view=view)
    except Exception as e:
        print(f"Failed to notify mentors: {e}")

class AcceptTicketView(discord.ui.View):
    def __init__(self, ticket_id: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @discord.ui.button(label="Accept Ticket", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        mentor_role = discord.utils.get(interaction.guild.roles, name="Mentor")
        if not mentor_role or mentor_role not in interaction.user.roles:
            await interaction.response.send_message("You need the Mentor role to accept tickets!", ephemeral=True)
            return
        
        db = get_firebase_db()
        ticket = db.get_ticket_by_id(self.ticket_id)
        
        if not ticket:
            await interaction.response.send_message("Ticket not found!", ephemeral=True)
            return
        
        if ticket['status'] != 'open':
            await interaction.response.send_message("This ticket is not open!", ephemeral=True)
            return
        
        if ticket['mentor_id']:
            await interaction.response.send_message(f"This ticket is already assigned to {ticket['mentor_name']}!", ephemeral=True)
            return
        
        success = db.assign_ticket(self.ticket_id, interaction.user.id, interaction.user.display_name)
        if not success:
            await interaction.response.send_message("Failed to assign ticket. Please try again.", ephemeral=True)
            return
        
        original_embed = interaction.message.embeds[0]
        new_embed = discord.Embed(
            title=original_embed.title,
            color=Colors.GREEN
        )
        
        for field in original_embed.fields:
            if field.name != "Helped by:":
                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        new_embed.add_field(name="Helped by:", value=interaction.user.mention, inline=False)
        
        button.disabled = True
        button.label = "Accepted"
        button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(embed=new_embed, view=self)
        
        try:
            user = await interaction.client.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_ASSIGNED,
                description=Messages.TICKET_ASSIGNED_SUCCESS,
                color=Colors.GREEN
            )
            user_embed.add_field(name="Mentor", value=interaction.user.mention, inline=True)
            user_embed.add_field(name="Description", value=ticket['description'], inline=False)
            user_embed.add_field(name="Location", value=ticket['location'], inline=False)
            
            user_view = UserTicketView(self.ticket_id, ticket)
            await user.send(embed=user_embed, view=user_view)
        except:
            pass
        
        try:
            mentor_embed = discord.Embed(
                title=f"Ticket #{self.ticket_id} Assigned to You",
                description="You have accepted this ticket. Choose an action:",
                color=Colors.GREEN
            )
            mentor_embed.add_field(name="User", value=f"<@{ticket['user_id']}>", inline=True)
            mentor_embed.add_field(name="Description", value=ticket['description'], inline=False)
            mentor_embed.add_field(name="Location", value=ticket['location'], inline=False)
            if ticket['categories']:
                mentor_embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=False)
            
            mentor_view = MentorActionView(self.ticket_id, ticket)
            await interaction.user.send(embed=mentor_embed, view=mentor_view)
        except:
            pass

class MentorActionView(discord.ui.View):
    def __init__(self, ticket_id: str, ticket: dict):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.ticket = ticket

    @discord.ui.button(label="Resolve", style=discord.ButtonStyle.success)
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = get_firebase_db()
        current_ticket = db.get_ticket_by_id(self.ticket_id)
        
        if not current_ticket:
            await interaction.response.send_message("Ticket not found!", ephemeral=True)
            return
        
        if current_ticket['mentor_id'] != interaction.user.id:
            await interaction.response.send_message("This ticket is no longer assigned to you!", ephemeral=True)
            return
        
        if current_ticket['status'] == 'closed':
            await interaction.response.send_message("This ticket is already closed!", ephemeral=True)
            return
        
        success = db.close_ticket(self.ticket_id)
        if not success:
            await interaction.response.send_message("Failed to resolve ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Resolved",
            description="This ticket has been marked as resolved.",
            color=Colors.RED
        )
        embed.add_field(name="Resolved by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Resolved at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket['user_id'])
            user_embed = discord.Embed(
                title=f"Ticket #{self.ticket_id} Resolved",
                description="Your ticket has been resolved by your mentor.",
                color=Colors.RED
            )
            user_embed.add_field(name="Resolved by", value=interaction.user.mention, inline=True)
            await user.send(embed=user_embed)
        except:
            pass

    @discord.ui.button(label="Reassign", style=discord.ButtonStyle.danger)
    async def discard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Detach mentor from this ticket and push ticket back to the mentor queue"""
        db = get_firebase_db()
        current_ticket = db.get_ticket_by_id(self.ticket_id)
        
        if not current_ticket:
            await interaction.response.send_message("Ticket not found!", ephemeral=True)
            return
        
        if current_ticket['mentor_id'] != interaction.user.id:
            await interaction.response.send_message("This ticket is no longer assigned to you!", ephemeral=True)
            return
        
        if current_ticket['status'] == 'closed':
            await interaction.response.send_message("This ticket is already closed!", ephemeral=True)
            return
        

        success = db.release_ticket(self.ticket_id)
        if not success:
            await interaction.response.send_message("Failed to reassign ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Reassigned",
            description="This ticket has been released back to the queue.",
            color=Colors.DEFAULT
        )
        embed.add_field(name="Discarded by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Discarded at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        try:
            mentor_channel_id = db.get_dev_config('mentor_channel')
            if mentor_channel_id:
                mentor_channel = interaction.guild.get_channel(int(mentor_channel_id))
                if mentor_channel:
                    ticket_embed = discord.Embed(
                        title=f"Ticket #{self.ticket_id}",
                        color=Colors.DEFAULT
                    )
                    ticket_embed.add_field(name="Problem description", value=self.ticket['description'], inline=False)
                    ticket_embed.add_field(name="Where to meet", value=self.ticket['location'], inline=False)
                    ticket_embed.add_field(name="Helped by:", value="No mentor assigned yet", inline=False)
                    
                    if self.ticket['categories']:
                        ticket_embed.add_field(name="Categories", value=", ".join(self.ticket['categories']), inline=False)
                    
                    view = AcceptTicketView(self.ticket_id)
                    await mentor_channel.send(embed=ticket_embed, view=view)
        except Exception as e:
            print(f"Failed to repost ticket: {e}")

class UserTicketView(discord.ui.View):
    def __init__(self, ticket_id: str, ticket: dict):
        super().__init__(timeout=None)  # No timeout
        self.ticket_id = ticket_id
        self.ticket = ticket

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ticket['user_id']:
            await interaction.response.send_message("You can only close your own tickets!", ephemeral=True)
            return
        
        db = get_firebase_db()
        current_ticket = db.get_ticket_by_id(self.ticket_id)
        
        if not current_ticket:
            await interaction.response.send_message("Ticket not found!", ephemeral=True)
            return
        
        if current_ticket['status'] == 'closed':
            await interaction.response.send_message("This ticket is already closed!", ephemeral=True)
            return
        
        success = db.close_ticket(self.ticket_id)
        if not success:
            await interaction.response.send_message("Failed to close ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Closed",
            description="You have closed this ticket.",
            color=Colors.RED
        )
        embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Closed at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        button.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        if current_ticket['mentor_id']:
            try:
                mentor = await interaction.client.fetch_user(current_ticket['mentor_id'])
                mentor_embed = discord.Embed(
                    title=f"Ticket #{self.ticket_id} Closed by User",
                    description="The ticket creator has closed this ticket.",
                    color=Colors.RED
                )
                mentor_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
                await mentor.send(embed=mentor_embed)
            except:
                pass

class ChannelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300) 
        self.ticket_channel = None
        self.mentor_channel = None
        
        self.add_item(TicketChannelSelect())
        self.add_item(MentorChannelSelect())
        self.add_item(SaveChannelsButton())

class TicketChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select ticket creation channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to configure channels!", ephemeral=True)
            return
        
        self.view.ticket_channel = self.values[0]
        
        await interaction.response.defer(ephemeral=True)

class MentorChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select mentor notification channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to configure channels!", ephemeral=True)
        return

        self.view.mentor_channel = self.values[0]
        
        await interaction.response.defer(ephemeral=True)

class SaveChannelsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Save",
            style=discord.ButtonStyle.success,
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to configure channels!", ephemeral=True)
            return
        
        if not self.view.ticket_channel or not self.view.mentor_channel:
            await interaction.response.send_message("Please select both ticket and mentor channels first!", ephemeral=True)
            return

    db = get_firebase_db()
        db.set_dev_config('ticket_channel', str(self.view.ticket_channel.id))
        db.set_dev_config('mentor_channel', str(self.view.mentor_channel.id))
        
        try:
            ticket_channel = interaction.guild.get_channel(self.view.ticket_channel.id)
            if not ticket_channel:
                raise Exception("Could not find the selected ticket channel")
            
            ticket_embed = discord.Embed(
                title="Need 1:1 mentor help?",
                description="Select a technology you need help with and follow the instructions!",
                color=Colors.GREEN
            )
            
            ticket_view = PublicCategorySelectionView()
            await ticket_channel.send(embed=ticket_embed, view=ticket_view)
            
            embed = discord.Embed(
                title=Titles.CONFIG_SUCCESS,
                description="Channel configuration saved successfully!",
                color=Colors.GREEN
            )
            embed.add_field(name="Ticket Channel", value=self.view.ticket_channel.mention, inline=True)
            embed.add_field(name="Mentor Channel", value=self.view.mentor_channel.mention, inline=True)
            embed.add_field(name="Ticket Interface Posted", value=f"Ticket creation interface has been posted in {self.view.ticket_channel.mention}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title=Titles.CONFIG_SUCCESS,
                description="Channel configuration saved successfully!",
                color=Colors.GREEN
            )
            embed.add_field(name="Ticket Channel", value=self.view.ticket_channel.mention, inline=True)
            embed.add_field(name="Mentor Channel", value=self.view.mentor_channel.mention, inline=True)
            embed.add_field(name="Interface Post Failed", value=f"Could not post ticket interface: {str(e)}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
