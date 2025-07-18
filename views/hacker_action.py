import discord
from datetime import datetime
from utils.db import get_firebase_db
from utils.styles import Colors, Emojis, Titles, Messages

class UserTicketView(discord.ui.View):
    def __init__(self, ticket_id: str, ticket: dict):
        super().__init__(timeout=None)
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
            description="This ticket has been closed.",
            color=Colors.GRAY
        )
        embed.add_field(name="Closed by", value=interaction.user.display_name, inline=True)
        embed.add_field(name="Closed at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        button.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        if current_ticket['mentor_id']:
            try:
                mentor = await interaction.client.fetch_user(current_ticket['mentor_id'])
                mentor_embed = discord.Embed(
                    title=Titles.TICKET_CLOSED,
                    description=f"Ticket #{self.ticket_id} has been closed by the user.",
                    color=Colors.GRAY
                )
                mentor_embed.add_field(name="Closed by", value=interaction.user.display_name, inline=True)
                await mentor.send(embed=mentor_embed)
            except:
                pass