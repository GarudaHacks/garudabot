import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

categories = {
    "Frontend", "React", "HTML/CSS", "Javascript/TypeScript", "Backend", 
    "Python", "Java", "C++", "C#", "Go", "Ideation",
    "Swift", "Kotlin", "Database", "SQL", "Pitching", "Cloud", "CI/CD", 
    "Hardware", "Mobile", "AI/ML", "Web3", "Cybersecurity", "Git", "Other"
}

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
        self.dev_configs = "dev_configs"
        
        if not firebase_admin._apps:
            if credentials_path and os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
            elif project_id:
                firebase_admin.initialize_app(project=project_id)
            else:
                cred_json = os.getenv('FIREBASE_CREDENTIALS')
                if cred_json:
                    cred_dict = json.loads(cred_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                else:
                    raise ValueError("Firebase credentials not found. Please provide credentials_path, project_id, or FIREBASE_CREDENTIALS environment variable.")
        
        self.db = firestore.client()

    def create_ticket(self, user_id: int, user_name: str, title: str, description: str, location: str, categories: List[str] = None) -> Dict[str, Any]:
        """Create a new ticket with a counter-based ID"""
        counter_doc = self.db.collection(self.dev_configs).document('counter').get()
        if counter_doc.exists:
            current_counter = counter_doc.to_dict().get('value', 0)
        else:
            current_counter = 0
        
        ticket_id = str(current_counter + 1)
        
        self.db.collection(self.dev_configs).document('counter').set({
            'value': current_counter + 1,
            'updated_at': datetime.now().isoformat()
        })
        
        if categories is None:
            categories = []
        else:
            categories = [cat for cat in categories if cat in globals()["categories"]]
        
        ticket = {
            'id': ticket_id,
            'user_id': user_id,
            'user_name': user_name,
            'title': title,
            'description': description,
            'location': location,
            'categories': categories,
            'status': 'open',
            'created_at': datetime.now().isoformat(),
            'mentor_id': None,
            'mentor_name': None,
            'closed_at': None
        }
        
        self.db.collection(self.tickets_collection).document(ticket_id).set(ticket)
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

    def get_user_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """Returns all tickets for a specific user"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("user_id", "==", user_id)
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

    def get_open_tickets(self) -> List[Dict[str, Any]]:
        """Returns all unresolved tickets"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("status", "==", "open")
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

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

    def close_ticket(self, ticket_id: int) -> bool:
        """Closes a pending ticket, changes status to 'closed'"""
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

    def release_ticket(self, ticket_id: int) -> bool:
        """Release a ticket back to the queue by removing mentor assignment"""
        try:
            ticket_ref = self.db.collection(self.tickets_collection).document(str(ticket_id))
            ticket_doc = ticket_ref.get()
            
            if not ticket_doc.exists:
                return False
            
            ticket_data = ticket_doc.to_dict()
            if ticket_data['status'] != 'open':
                return False
            
            # Update the ticket to remove mentor assignment
            ticket_ref.update({
                'mentor_id': None,
                'mentor_name': None
            })
            return True
        except Exception:
            return False

    def get_tickets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tickets for a specific category"""
        try:
            tickets = self.db.collection(self.tickets_collection).where(
                filter=FieldFilter("categories", "array_contains", category)
            ).stream()
            return [ticket.to_dict() for ticket in tickets]
        except Exception:
            return []

    def get_dev_config(self, config_key: str) -> Optional[str]:
        """Get development configuration from Firebase"""
        try:
            doc = self.db.collection(self.dev_configs).document(config_key).get()
            if doc.exists:
                return doc.to_dict().get('value')
            return None
        except Exception:
            return None

    def set_dev_config(self, config_key: str, value: str) -> bool:
        """Set development configuration in Firebase"""
        try:
            self.db.collection(self.dev_configs).document(config_key).set({
                'value': value,
                'updated_at': datetime.now().isoformat()
            })
            return True
        except Exception:
            return False

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