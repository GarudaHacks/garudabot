"""
Styles and colors
"""
class Colors:
    GREEN = 0x00ff00
    RED = 0xff0000
    BLUE = 0x0099ff
    GRAY = 0x808080
    DEFAULT = 0x2f3136

class Emojis:
    # Ticket status
    OPEN_TICKET = "🟢"
    CLOSED_TICKET = "🔴"
    TICKET = "🎫"
    
    # Actions
    CREATE = "📝"
    LIST = "📋"
    SEARCH = "🔍"
    CLOSE = "🔒"
    ACCEPT = "✅"
    DENY = "❌"
    CONFIG = "⚙️"
    SETUP = "🔧"
    SYNC = "🔄"
    
    # Categories
    HACKER_COMMANDS = "📝"
    MENTOR_COMMANDS = "👨‍🏫"
    ADMIN_COMMANDS = "⚙️"
    
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"

class Titles:
    TICKET_CREATED = "🎫 Ticket Created"
    TICKET_CLOSED = "🔒 Ticket Closed"
    TICKET_ACCEPTED = "✅ Ticket Accepted"
    TICKET_ASSIGNED = "🎫 Ticket Assigned"
    NEW_TICKET = "🎫 New Ticket"
    TICKET_REASSIGNED = "🔄 Ticket Reassigned"
    
    # Lists
    YOUR_TICKETS = "📝 Your Tickets"
    OPEN_TICKETS = "📝 Open Tickets"
    ASSIGNED_TICKETS = "📝 Your Assigned Tickets"
    MY_TICKETS = "📝 My Assigned Tickets"
    SEARCH_RESULTS = "🔍 Search Results"
    
    # Setup
    BOT_SETUP = "🔧 Bot Setup"
    CHANNEL_CONFIG = "✅ Channel Configuration Updated"
    CONFIG_SUCCESS = "✅ Configuration Updated"
    
    # Errors
    WRONG_CHANNEL = "❌ Wrong Channel"
    TOO_MANY_TICKETS = "Too Many Open Tickets"
    TICKET_NOT_FOUND = "❌ Ticket Not Found"
    PERMISSION_ERROR = "❌ Permission Error"

# Common messages
class Messages:
    TICKET_CREATED_SUCCESS = "Your ticket has been created successfully!"
    TICKET_CLOSED_SUCCESS = "Your ticket has been closed."
    TICKET_ACCEPTED_SUCCESS = "You have accepted the ticket"
    TICKET_ASSIGNED_SUCCESS = "Your ticket has been assigned to a mentor!"
    TICKET_REASSIGNED_SUCCESS = "Ticket has been reassigned to"
    
    # Errors
    WRONG_CHANNEL_MSG = "Tickets can only be created in the designated ticket channel."
    TOO_MANY_TICKETS_MSG = "You already have 5 open tickets. Please close these tickets before creating a new one."
    TICKET_NOT_FOUND_MSG = "Ticket not found."
    PERMISSION_DENIED_MSG = "You need administrator permissions to configure channels."
    MENTOR_ROLE_REQUIRED = "You need the Mentor role to use this command."
    
    # Setup
    SETUP_COMPLETE = "The bot is ready to handle tickets!"
    SYNC_SUCCESS = "Slash commands cleared and resynced successfully!"
    
    # Lists
    NO_TICKETS = "You don't have any tickets yet."
    NO_OPEN_TICKETS = "No open tickets at the moment!"
    NO_ASSIGNED_TICKETS = "You don't have any assigned tickets at the moment!"
    NO_SEARCH_RESULTS = "No tickets found matching"

# Footer messages
class Footers:
    CONFIG_NOTE = "Tickets can now be created in the ticket channel, and mentors will be notified in the mentor channel." 