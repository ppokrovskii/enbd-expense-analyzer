"""Persons domain service."""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from .models import Person


class PersonService:
    """Service for managing persons."""
    
    @staticmethod
    def get_persons(db: Session, user_id: str) -> List[Person]:
        """Get all persons for a user."""
        return db.query(Person).filter(Person.user_id == user_id).order_by(Person.name).all()
    
    @staticmethod
    def get_person(db: Session, person_id: int, user_id: str) -> Optional[Person]:
        """Get a specific person, ensuring it belongs to the user."""
        return db.query(Person).filter(
            Person.id == person_id,
            Person.user_id == user_id
        ).first()
    
    @staticmethod
    def get_active_person(db: Session, user_id: str) -> Optional[Person]:
        """Get the currently active person for a user."""
        return db.query(Person).filter(
            Person.user_id == user_id,
            Person.is_active == True
        ).first()
    
    @staticmethod
    def create_person(db: Session, user_id: str, name: str) -> Person:
        """Create a new person for a user.
        
        If this is the first person, make it active automatically.
        """
        # Check if user has any persons
        existing_count = db.query(Person).filter(Person.user_id == user_id).count()
        is_first = existing_count == 0
        
        person = Person(
            user_id=user_id,
            name=name,
            is_active=is_first,  # First person is auto-active
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(person)
        db.commit()
        db.refresh(person)
        return person
    
    @staticmethod
    def update_person(db: Session, person_id: int, user_id: str, name: Optional[str] = None) -> Optional[Person]:
        """Update a person's details."""
        person = PersonService.get_person(db, person_id, user_id)
        if not person:
            return None
        
        if name:
            person.name = name
        person.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(person)
        return person
    
    @staticmethod
    def activate_person(db: Session, person_id: int, user_id: str) -> Optional[Person]:
        """Make a person active, deactivating any currently active person."""
        person = PersonService.get_person(db, person_id, user_id)
        if not person:
            return None
        
        # Deactivate all other persons for this user
        db.query(Person).filter(
            Person.user_id == user_id,
            Person.id != person_id
        ).update({"is_active": False})
        
        # Activate the selected person
        person.is_active = True
        person.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(person)
        return person
    
    @staticmethod
    def delete_person(db: Session, person_id: int, user_id: str) -> bool:
        """Delete a person and all their data.
        
        Note: This cascades to delete all related data (transactions, categories, etc.)
        when person_id foreign keys are added with ON DELETE CASCADE.
        
        Returns True if deleted, False if not found.
        """
        person = PersonService.get_person(db, person_id, user_id)
        if not person:
            return False
        
        # Check if this is the active person
        was_active = person.is_active
        
        db.delete(person)
        db.commit()
        
        # If we deleted the active person, activate another one if available
        if was_active:
            remaining = db.query(Person).filter(Person.user_id == user_id).first()
            if remaining:
                remaining.is_active = True
                db.commit()
        
        return True
    
    @staticmethod
    def ensure_default_person(db: Session, user_id: str) -> Person:
        """Ensure a user has at least one person, creating default if needed.
        
        This is useful for migration or first-time setup.
        """
        active = PersonService.get_active_person(db, user_id)
        if active:
            return active
        
        # Check if user has any persons
        existing = db.query(Person).filter(Person.user_id == user_id).first()
        if existing:
            # Make the first one active
            existing.is_active = True
            db.commit()
            return existing
        
        # Create default person
        return PersonService.create_person(db, user_id, "Default")

