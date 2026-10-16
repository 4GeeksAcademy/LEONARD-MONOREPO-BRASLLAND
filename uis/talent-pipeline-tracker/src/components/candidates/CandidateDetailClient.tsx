"use client";

import Link from "next/link";
import { useState } from "react";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/constants";
import { formatDate, formatEnumLabel } from "@/lib/format";
import { addCandidateNote, deleteCandidateNote, getCandidateNotes, patchCandidate } from "@/services/trackerApi";
import type { CandidateNote, CandidateRecord } from "@/types/tracker";

type CandidateDetailClientProps = {
  initialCandidate: CandidateRecord;
  initialNotes: CandidateNote[];
};

export function CandidateDetailClient({ initialCandidate, initialNotes }: CandidateDetailClientProps) {
  const [candidate, setCandidate] = useState(initialCandidate);
  const [notes, setNotes] = useState(initialNotes);
  const [noteInput, setNoteInput] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function refreshNotes() {
    const response = await getCandidateNotes(candidate.id);
    setNotes(response.data);
  }

  async function updateField(field: "status" | "stage", value: string) {
    try {
      setIsUpdating(true);
      setErrorMessage(null);
      setMessage(null);
      const updated = await patchCandidate(candidate.id, { [field]: value });
      setCandidate(updated);
      setMessage(`Candidate ${field} updated successfully.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update candidate field.");
    } finally {
      setIsUpdating(false);
    }
  }

  async function onAddNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!noteInput.trim()) {
      setErrorMessage("A note cannot be empty.");
      return;
    }

    try {
      setIsSavingNote(true);
      setErrorMessage(null);
      setMessage(null);
      await addCandidateNote(candidate.id, noteInput.trim());
      await refreshNotes();
      setNoteInput("");
      setMessage("Note added successfully.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to add note.");
    } finally {
      setIsSavingNote(false);
    }
  }

  async function onDeleteNote(noteId: string) {
    try {
      setDeletingNoteId(noteId);
      setErrorMessage(null);
      setMessage(null);
      await deleteCandidateNote(candidate.id, noteId);
      await refreshNotes();
      setMessage("Note deleted successfully.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to delete note.");
    } finally {
      setDeletingNoteId(null);
    }
  }

  return (
    <section className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Brasaland People and Culture</p>
            <h1 className="text-2xl font-black text-slate-900">{candidate.full_name}</h1>
            <p className="text-sm text-slate-600">{candidate.position}</p>
          </div>
          <Link href={`/candidates/${candidate.id}/edit`} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700">
            Edit Candidate
          </Link>
        </div>

        {errorMessage ? <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p> : null}
        {message ? <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}

        <dl className="mt-5 grid gap-3 text-sm md:grid-cols-2">
          <div><dt className="font-semibold text-slate-700">Email</dt><dd>{candidate.email}</dd></div>
          <div><dt className="font-semibold text-slate-700">Phone</dt><dd>{candidate.phone}</dd></div>
          <div><dt className="font-semibold text-slate-700">LinkedIn</dt><dd>{candidate.linkedin_url ? <a className="text-amber-700 underline" href={candidate.linkedin_url} target="_blank" rel="noreferrer">View profile</a> : "Not provided"}</dd></div>
          <div><dt className="font-semibold text-slate-700">CV</dt><dd>{candidate.cv_url ? <a className="text-amber-700 underline" href={candidate.cv_url} target="_blank" rel="noreferrer">Open CV</a> : "Not provided"}</dd></div>
          <div><dt className="font-semibold text-slate-700">Experience</dt><dd>{candidate.experience_years} years</dd></div>
          <div><dt className="font-semibold text-slate-700">Application date</dt><dd>{formatDate(candidate.applied_at)}</dd></div>
        </dl>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-700">
            Status
            <select
              disabled={isUpdating}
              value={candidate.status}
              onChange={(event) => updateField("status", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm font-semibold text-slate-700">
            Stage
            <select
              disabled={isUpdating}
              value={candidate.stage}
              onChange={(event) => updateField("stage", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              {STAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="mt-2 text-xs text-slate-500">
          Current status: {formatEnumLabel(candidate.status)}. Current stage: {formatEnumLabel(candidate.stage)}.
        </p>
      </div>

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
    </section>
  );
}
