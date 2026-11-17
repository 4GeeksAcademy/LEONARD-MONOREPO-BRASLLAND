"use client";

import { useState } from "react";
import { formatDate } from "@/lib/format";
import { addCandidateNote, deleteCandidateNote, getCandidateNotes } from "@/services/trackerApi";
import type { CandidateNote } from "@/types/tracker";

type CandidateNotesPanelProps = {
  candidateId: string;
  notes: CandidateNote[];
  onNotesChange: (notes: CandidateNote[]) => void;
  onFeedback: (feedback: { message?: string; error?: string }) => void;
};

export function CandidateNotesPanel({ candidateId, notes, onNotesChange, onFeedback }: CandidateNotesPanelProps) {
  const [noteInput, setNoteInput] = useState("");
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);

  async function refreshNotes() {
    const response = await getCandidateNotes(candidateId);
    onNotesChange(response.data);
  }

  async function onAddNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!noteInput.trim()) {
      onFeedback({ error: "A note cannot be empty." });
      return;
    }

    try {
      setIsSavingNote(true);
      onFeedback({});
      await addCandidateNote(candidateId, noteInput.trim());
      await refreshNotes();
      setNoteInput("");
      onFeedback({ message: "Note added successfully." });
    } catch (error) {
      onFeedback({ error: error instanceof Error ? error.message : "Failed to add note." });
    } finally {
      setIsSavingNote(false);
    }
  }

  async function onDeleteNote(noteId: string) {
    try {
      setDeletingNoteId(noteId);
      onFeedback({});
      await deleteCandidateNote(candidateId, noteId);
      await refreshNotes();
      onFeedback({ message: "Note deleted successfully." });
    } catch (error) {
      onFeedback({ error: error instanceof Error ? error.message : "Failed to delete note." });
    } finally {
      setDeletingNoteId(null);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-black text-slate-900">Internal Notes</h2>

      <form className="mt-3 space-y-3" onSubmit={onAddNote}>
        <textarea
          value={noteInput}
          onChange={(event) => setNoteInput(event.target.value)}
          rows={3}
          placeholder="Add interview or screening notes for this profile."
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={isSavingNote}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
        >
          {isSavingNote ? "Saving note..." : "Add note"}
        </button>
      </form>

      <ul className="mt-5 space-y-3">
        {notes.map((note) => (
          <li key={note.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-sm text-slate-800">{note.content}</p>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>{formatDate(note.created_at)}</span>
              <button
                type="button"
                onClick={() => onDeleteNote(note.id)}
                disabled={deletingNoteId !== null}
                className="font-semibold text-red-700"
                title="Delete note"
              >
                {deletingNoteId === note.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </li>
        ))}
        {notes.length === 0 ? <li className="text-sm text-slate-500">No notes for this candidate yet.</li> : null}
      </ul>
    </div>
  );
}
