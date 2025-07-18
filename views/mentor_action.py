import discord
from datetime import datetime
from utils.db import get_firebase_db
from utils.styles import Colors, Emojis, Titles, Messages

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
        
        if current_ticket['status'] == 'closed':
            await interaction.response.send_message("This ticket is already closed!", ephemeral=True)
            return
        
        if current_ticket['mentor_id'] != interaction.user.id:
            await interaction.response.send_message("You can only resolve tickets assigned to you!", ephemeral=True)
            return
        
        success = db.close_ticket(self.ticket_id)
        if not success:
            await interaction.response.send_message("Failed to resolve ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Resolved",
            description="This ticket has been resolved.",
            color=Colors.GRAY
        )
        embed.add_field(name="Resolved by", value=interaction.user.display_name, inline=True)
        embed.add_field(name="Hacker", value=self.ticket['user_name'], inline=True)
        embed.add_field(name="Title", value=self.ticket.get('title', 'No title'), inline=False)
        embed.add_field(name="Resolved at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_CLOSED,
                description=f"Your ticket #{self.ticket_id} has been resolved by your mentor.",
                color=Colors.GRAY
            )
            user_embed.add_field(name="Resolved by", value=interaction.user.display_name, inline=True)
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
        
        if current_ticket['status'] == 'closed':
            await interaction.response.send_message("This ticket is already closed!", ephemeral=True)
            return
        
        if current_ticket['mentor_id'] != interaction.user.id:
            await interaction.response.send_message("You can only reassign tickets assigned to you!", ephemeral=True)
            return

        success = db.release_ticket(self.ticket_id)
        if not success:
            await interaction.response.send_message("Failed to reassign ticket. Please try again.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Ticket #{self.ticket_id} Reassigned",
            description="This ticket has been released back to the queue.",
            color=Colors.DISCORD_DEFAULT
        )
        embed.add_field(name="Reassigned by", value=interaction.user.display_name, inline=True)
        embed.add_field(name="Hacker", value=self.ticket['user_name'], inline=True)
        embed.add_field(name="Reassigned at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Notify the user that their ticket has been reassigned
        try:
            user = await interaction.client.fetch_user(self.ticket['user_id'])
            user_embed = discord.Embed(
                title=Titles.TICKET_REASSIGNED,
                description=f"Your ticket #{self.ticket_id} has been released back to the queue and is now available for other mentors to help you.",
                color=Colors.BLUE
            )
            user_embed.add_field(name="Previous Mentor", value=interaction.user.display_name, inline=True)
            user_embed.add_field(name="Ticket Title", value=self.ticket.get('title', 'No title'), inline=False)
            user_embed.add_field(name="Reassigned at", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            await user.send(embed=user_embed)
        except Exception as e:
            print(f"Failed to notify user {self.ticket['user_id']} about ticket reassignment: {e}")
        
        # Repost the ticket in the mentor channel
        mentor_channel_id = db.get_dev_config('mentor_channel')
        if not mentor_channel_id:
            print(f"No mentor channel configured. Ticket {self.ticket_id} was reassigned but not reposted.")
            return
            
        try:
            mentor_channel = interaction.guild.get_channel(int(mentor_channel_id))
            if not mentor_channel:
                print(f"Mentor channel {mentor_channel_id} not found in guild {interaction.guild.id}")
                return
                
            ticket_embed = discord.Embed(
                title=f"🎫 Ticket #{self.ticket_id} Available",
                description="A ticket has been released back to the queue and is available for mentors.",
                color=Colors.DISCORD_DEFAULT
            )
                                ticket_embed.add_field(name="Hacker", value=self.ticket['user_name'], inline=True)
            ticket_embed.add_field(name="Title", value=self.ticket.get('title', 'No title'), inline=False)
            ticket_embed.add_field(name="Description", value=self.ticket['description'][:200] + "..." if len(self.ticket['description']) > 200 else self.ticket['description'], inline=False)
            ticket_embed.add_field(name="Location", value=self.ticket['location'], inline=True)
            ticket_embed.add_field(name="Status", value="Available for mentoring", inline=True)
            
            if self.ticket['categories']:
                ticket_embed.add_field(name="Categories", value=", ".join(self.ticket['categories']), inline=False)
            
            from views.manage_ticket import AcceptTicketView
            view = AcceptTicketView(self.ticket_id)
            await mentor_channel.send(embed=ticket_embed, view=view)
            print(f"Successfully reposted ticket {self.ticket_id} in mentor channel {mentor_channel.name}")
            
        except Exception as e:
            print(f"Failed to repost ticket {self.ticket_id} in mentor channel: {e}")
            try:
                await interaction.followup.send("Ticket reassigned but there was an issue reposting it to the mentor channel. Please contact an administrator.", ephemeral=True)
            except:
                pass