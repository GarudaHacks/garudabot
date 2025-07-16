import discord
from utils.db import get_firebase_db
from utils.styles import Colors, Titles, Messages

class ChannelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ticket_channel = None
        self.mentor_channel = None
        
        self.add_item(TicketChannelSelect())
        self.add_item(MentorChannelSelect())
        self.add_item(SaveChannelsButton())

class TicketChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select ticket creation channel",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.ticket_channel = self.values[0]
        await interaction.response.send_message(f"Selected ticket channel: {self.values[0].mention}", ephemeral=True)

class MentorChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select mentor notification channel",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.mentor_channel = self.values[0]
        await interaction.response.send_message(f"Selected mentor channel: {self.values[0].mention}", ephemeral=True)

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
        
        embed = discord.Embed(
            title=Titles.CHANNEL_CONFIG,
            description=Messages.CONFIG_NOTE,
            color=Colors.GREEN
        )
        embed.add_field(name="Ticket Channel", value=self.view.ticket_channel.mention, inline=True)
        embed.add_field(name="Mentor Channel", value=self.view.mentor_channel.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            ticket_embed = discord.Embed(
                title="Need 1:1 mentor help?",
                description="Select a technology you need help with and follow the instructions!",
                color=Colors.GREEN
            )
            
            from views.ticket_views import PublicCategorySelectionView
            view = PublicCategorySelectionView()
            await self.view.ticket_channel.send(embed=ticket_embed, view=view)
        except Exception as e:
            print(f"Failed to post ticket interface: {e}") 