"use client";

import { useState, useRef, useEffect } from "react";
import { usePerson, Person } from "../hooks/usePerson";

export default function PersonSwitcher() {
  const { persons, activePerson, loading, switchPerson, createPerson, deletePerson, updatePerson } = usePerson();
  const [isOpen, setIsOpen] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [newPersonName, setNewPersonName] = useState("");
  const [editPersonName, setEditPersonName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSwitchPerson = async (person: Person) => {
    await switchPerson(person.id);
    setIsOpen(false);
  };

  const handleCreatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPersonName.trim()) return;

    setIsCreating(true);
    await createPerson(newPersonName.trim());
    setNewPersonName("");
    setShowAddModal(false);
    setIsCreating(false);
  };

  const handleEditPerson = (person: Person, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingPerson(person);
    setEditPersonName(person.name);
    setShowEditModal(true);
    setIsOpen(false);
  };

  const handleUpdatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editPersonName.trim() || !editingPerson) return;

    setIsUpdating(true);
    await updatePerson(editingPerson.id, editPersonName.trim());
    setEditPersonName("");
    setEditingPerson(null);
    setShowEditModal(false);
    setIsUpdating(false);
  };

  const handleDeletePerson = async (personId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this person and all their data?")) {
      await deletePerson(personId);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)]/50">
        <div className="w-7 h-7 rounded-full bg-[var(--color-bg-tertiary)] animate-pulse" />
        <span className="text-sm text-[var(--color-text-secondary)]">Loading...</span>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)]/50 hover:bg-[var(--color-bg-tertiary)] transition-apple"
      >
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] flex items-center justify-center text-white text-xs font-semibold">
          {activePerson?.name?.[0]?.toUpperCase() || "?"}
        </div>
        
        {/* Name */}
        <span className="text-sm font-medium text-[var(--color-text-primary)]">
          {activePerson?.name || "Select Person"}
        </span>
        
        {/* Chevron */}
        <svg
          className={`w-4 h-4 text-[var(--color-text-secondary)] transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-[var(--color-bg-secondary)] rounded-xl border border-white/5 shadow-2xl overflow-hidden z-50">
          <div className="p-2">
            <div className="text-xs font-medium text-[var(--color-text-tertiary)] px-3 py-2 uppercase tracking-wider">
              Switch Person
            </div>
            
            {/* Person List */}
            {persons.map((person) => (
              <button
                key={person.id}
                onClick={() => handleSwitchPerson(person)}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg transition-apple ${
                  person.is_active
                    ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                    : "hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${
                    person.is_active
                      ? "bg-[var(--color-primary)] text-white"
                      : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]"
                  }`}>
                    {person.name[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium">{person.name}</span>
                </div>
                
                <div className="flex items-center gap-1">
                  {person.is_active && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-primary)]/20 text-[var(--color-primary)]">
                      Active
                    </span>
                  )}
                  
                  {/* Edit Button */}
                  <button
                    onClick={(e) => handleEditPerson(person, e)}
                    className="p-1 rounded hover:bg-[var(--color-primary)]/10 text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)] transition-apple"
                    title="Rename person"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                  
                  {/* Delete Button (only if more than 1 person) */}
                  {persons.length > 1 && (
                    <button
                      onClick={(e) => handleDeletePerson(person.id, e)}
                      className="p-1 rounded hover:bg-red-500/10 text-[var(--color-text-tertiary)] hover:text-red-500 transition-apple"
                      title="Delete person"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>
              </button>
            ))}
            
            {/* Divider */}
            <div className="my-2 border-t border-white/5" />
            
            {/* Add Person Button */}
            <button
              onClick={() => {
                setShowAddModal(true);
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] transition-apple"
            >
              <div className="w-8 h-8 rounded-full border-2 border-dashed border-[var(--color-text-tertiary)] flex items-center justify-center">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <span className="text-sm font-medium">Add Person</span>
            </button>
          </div>
        </div>
      )}

      {/* Add Person Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[20vh] z-50">
          <div className="bg-[var(--color-bg-secondary)] rounded-2xl border border-white/5 p-6 w-96 shadow-2xl animate-in fade-in slide-in-from-top-4 duration-200">
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
              Add New Person
            </h3>
            
            <form onSubmit={handleCreatePerson}>
              <input
                type="text"
                value={newPersonName}
                onChange={(e) => setNewPersonName(e.target.value)}
                placeholder="Enter name (e.g., Wife, Partner)"
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-primary)]/50 transition-apple"
                autoFocus
              />
              
              <div className="flex gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setNewPersonName("");
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-white/10 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-apple"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newPersonName.trim() || isCreating}
                  className="flex-1 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                >
                  {isCreating ? "Creating..." : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Person Modal */}
      {showEditModal && editingPerson && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[20vh] z-50">
          <div className="bg-[var(--color-bg-secondary)] rounded-2xl border border-white/5 p-6 w-96 shadow-2xl animate-in fade-in slide-in-from-top-4 duration-200">
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
              Rename Person
            </h3>
            
            <form onSubmit={handleUpdatePerson}>
              <input
                type="text"
                value={editPersonName}
                onChange={(e) => setEditPersonName(e.target.value)}
                placeholder="Enter new name"
                className="w-full px-4 py-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-primary)]/50 transition-apple"
                autoFocus
              />
              
              <div className="flex gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setEditPersonName("");
                    setEditingPerson(null);
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-white/10 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-apple"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!editPersonName.trim() || isUpdating}
                  className="flex-1 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                >
                  {isUpdating ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
