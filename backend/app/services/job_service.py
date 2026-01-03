"""Backward compatibility - re-export from jobs domain."""
from app.domains.jobs.service import JobService

__all__ = ['JobService']
