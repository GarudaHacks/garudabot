import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

class FirebaseTicketDatabase:
    """Firebase Firestore database interface to manage tickets"""
    
    def __init__(self, credentials_path: str = None, project_id: str = None):
        """
        Initialize Firebase connection
        
        Args:
            credentials_path: Path to Firebase service account key JSON file
            project_id: Firebase project ID (optional if using service account)
        """
        self.db = None
        self.tickets_collection = "tickets"
        self.counter_collection = "counters"
        
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            if credentials_path and os.path.exists(credentials_path):
                # Use service account key file
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
            elif project_id:
                # Use default credentials (for Google Cloud)
                firebase_admin.initialize_app(project=project_id)
            else:
                # Try to use environment variable for credentials
                cred_json = os.getenv('FIREBASE_CREDENTIALS')
                if cred_json:
                    cred_dict = json.loads(cred_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                else:
                    raise ValueError("Firebase credentials not found. Please provide credentials_path, project_id, or FIREBASE_CREDENTIALS environment variable.")
        
        self.db = firestore.client()

    def _get_next_ticket_id(self) -> int:
        """Get the next available ticket ID using a counter document"""
        counter_ref = self.db.collection(self.counter_collection).document('ticket_counter')
        
        try:
            # Try to get the current counter
            counter_doc = counter_ref.get()
            if counter_doc.exists:
                current_id = counter_doc.to_dict().get('current_id', 0)
            else:
                current_id = 0
            
            # Increment and update
            new_id = current_id + 1
            counter_ref.set({'current_id': new_id})
            return new_id
            
        except Exception as e:
            # Fallback: get max ID from existing tickets
            tickets = self.db.collection(self.tickets_collection).stream()
            max_id = 0
            for ticket in tickets:
                ticket_data = ticket.to_dict()
                max_id = max(max_id, ticket_data.get('id', 0))
            return max_id + 1

    def create_ticket(self, user_id: int, user_name: str, description: str) -> Dict[str, Any]:
        """Create a new ticket"""
        ticket_id = self._get_next_ticket_id()
        
        ticket = {
            'id': ticket_id,
            'user_id': user_id,
            'user_name': user_name,
            'description': description,
            'status': 'open',
            'created_at': datetime.now().isoformat(),
            'mentor_id': None,
            'mentor_name': None,
            'closed_at': None
        }
        
        # Add to Firestore
        self.db.collection(self.tickets_collection).document(str(ticket_id)).set(ticket)
        return ticket

    def get_ticket_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket by ID"""
        try:
            doc = self.db.collection(self.tickets_collection).document(str(ticket_id)).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception:
            return None

    # Get tickets related into one user
    def get_user_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all tickets for a specific user"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("user_id", "==", user_id)
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

    # Return all unresolved tickets
    def get_open_tickets(self) -> List[Dict[str, Any]]:
        """Get all open tickets"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("status", "==", "open")
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

    # Get all tickets handled by a mentor
    def get_mentor_tickets(self, mentor_id: int) -> List[Dict[str, Any]]:
        """Get all tickets assigned to a mentor"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("mentor_id", "==", mentor_id)
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

    # Assign a ticket to a specific mentor, changes status to 'pending'
    def assign_ticket(self, ticket_id: int, mentor_id: int, mentor_name: str) -> bool:
        """Assign a ticket to a mentor"""
        try:
            ticket_ref = self.db.collection(self.tickets_collection).document(str(ticket_id))
            ticket_doc = ticket_ref.get()
            
            if not ticket_doc.exists:
                return False
            
            ticket_data = ticket_doc.to_dict()
            if ticket_data['status'] != 'open':
                return False
            
            # Update the ticket
            ticket_ref.update({
                'mentor_id': mentor_id,
                'mentor_name': mentor_name
            })
            return True
        except Exception:
            return False

    # Closes a pending ticket, changes status to 'closed'
    def close_ticket(self, ticket_id: int) -> bool:
        """Close a ticket"""
        try:
            ticket_ref = self.db.collection(self.tickets_collection).document(str(ticket_id))
            ticket_doc = ticket_ref.get()
            
            if not ticket_doc.exists:
                return False
            
            ticket_data = ticket_doc.to_dict()
            if ticket_data['status'] == 'closed':
                return False
            
            # Update the ticket
            ticket_ref.update({
                'status': 'closed',
                'closed_at': datetime.now().isoformat()
            })
            return True
        except Exception:
            return False

    def reassign_ticket(self, ticket_id: int, new_mentor_id: int, new_mentor_name: str) -> bool:
        """Reassign a ticket to a different mentor"""
        try:
            ticket_ref = self.db.collection(self.tickets_collection).document(str(ticket_id))
            ticket_doc = ticket_ref.get()
            
            if not ticket_doc.exists:
                return False
            
            ticket_data = ticket_doc.to_dict()
            if ticket_data['status'] != 'open':
                return False
            
            # Update the ticket
            ticket_ref.update({
                'mentor_id': new_mentor_id,
                'mentor_name': new_mentor_name
            })
            return True
        except Exception:
            return False

    # Utility function to display ticket statistics
    # TODO: Should be able to show ticket statistics related to all mentors
    def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics"""
        try:
            # Get total tickets
            total_tickets = len(list(self.db.collection(self.tickets_collection).stream()))
            
            # Get open tickets
            open_tickets = len(list(self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("status", "==", "open")
            ).stream()))
            
            closed_tickets = total_tickets - open_tickets
            
            return {
                'total': total_tickets,
                'open': open_tickets,
                'closed': closed_tickets
            }
        except Exception:
            return {'total': 0, 'open': 0, 'closed': 0}

    # Search for a specific ticket based on a string query
    # TODO: Search by description, title, or category
    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Search tickets by description or user name"""
        query = query.lower()
        results = []
        
        try:
            # Get all tickets and filter locally (Firestore doesn't support full-text search)
            tickets = self.db.collection(self.tickets_collection).stream()
            
            for ticket_doc in tickets:
                ticket_data = ticket_doc.to_dict()
                if (query in ticket_data['description'].lower() or 
                    query in ticket_data['user_name'].lower() or
                    query in str(ticket_data['id'])):
                    results.append(ticket_data)
            
            return results
        except Exception:
            return []

# Global Firebase database instance
firebase_db = None

def init_firebase_db(credentials_path: str = None, project_id: str = None):
    """Initialize the global Firebase database instance"""
    global firebase_db
    firebase_db = FirebaseTicketDatabase(credentials_path, project_id)
    return firebase_db

def get_firebase_db() -> FirebaseTicketDatabase:
    """Get the global Firebase database instance"""
    global firebase_db
    if firebase_db is None:
        raise RuntimeError("Firebase database not initialized. Call init_firebase_db() first.")
    return firebase_db 