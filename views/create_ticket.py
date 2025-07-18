import discord
from datetime import datetime
from utils.db import get_firebase_db, categories
from utils.styles import Colors, Emojis, Titles, Messages

"""
Modal and views for creating tickets
"""
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
        
        # Reset the selected categories
        self.selected_categories.clear()
        
        from views.manage_ticket import notify_mentors
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