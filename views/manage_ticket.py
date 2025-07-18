import discord
from datetime import datetime
from utils.db import get_firebase_db
from utils.styles import Colors, Emojis, Titles, Messages

"""
Views for managing tickets (acceptance, resolution, etc.)
"""
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
            await interaction.response.send_message("Failed to accept ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Accepted",
            description=f"Accepted by {interaction.user.mention}",
            color=Colors.GREEN
        )
        embed.add_field(name="Hacker", value=ticket['user_name'], inline=True)
        embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
        embed.add_field(name="Description", value=ticket['description'], inline=False)
        embed.add_field(name="Location", value=ticket.get('location', 'No location'), inline=False)
        if ticket.get('categories'):
            embed.add_field(name="Categories", value=", ".join(ticket['categories']), inline=False)
        embed.add_field(name="Accepted at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        try:
            user = await interaction.client.fetch_user(ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_ASSIGNED,
                description=Messages.TICKET_ASSIGNED_SUCCESS,
                color=Colors.GREEN
            )
            user_embed.add_field(name="Mentor", value=interaction.user.mention, inline=True)
            user_embed.add_field(name="Title", value=ticket.get('title', 'No title'), inline=False)
            user_embed.add_field(name="Description", value=ticket['description'], inline=False)
            
            from views.mentor_action import MentorActionView
            view = MentorActionView(self.ticket_id, ticket)
            await user.send(embed=user_embed, view=view)
        except:
            pass

async def notify_mentors(interaction, ticket):
    """Notify mentors about a new ticket"""
    db = get_firebase_db()
    mentor_channel_id = db.get_dev_config('mentor_channel')
    
    if not mentor_channel_id:
        return
    
    try:
        mentor_channel = interaction.guild.get_channel(int(mentor_channel_id))
        if not mentor_channel:
            return
        
        embed = discord.Embed(
            title=f"Ticket #{ticket['id']}",
            color=Colors.DISCORD_DEFAULT
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