"use client";

import Link from "next/link";
import { use } from "react";
import { CandidateDetailClient } from "@/components/candidates/CandidateDetailClient";
import { getCandidateById, getCandidateNotes } from "@/services/trackerApi";
import { useApiData } from "@/hooks/useApiData";

type CandidateDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = use(params);
  const { data, error, isLoading, retry } = useApiData(id, () => Promise.all([
      getCandidateById(id),
      getCandidateNotes(id),
  ]));
  if (error) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <article className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <h1 className="text-xl font-black text-red-900">Could not load candidate profile</h1>
          <p className="mt-2 text-sm text-red-800">{error}</p>
          <div className="mt-3 flex gap-3">
            <button type="button" onClick={retry} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Try again</button>
            <Link href="/" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700">Candidate list</Link>
          </div>
        </article>
      </main>
    );
  }
  if (isLoading || !data) return <main className="auth-status" role="status">Loading candidate...</main>;
  const [candidate, notesResponse] = data;

  return (
    <main className="mx-auto max-w-5xl space-y-4 px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/" className="text-sm font-semibold text-amber-700">
        Back to candidate list
      </Link>
      <CandidateDetailClient initialCandidate={candidate} initialNotes={notesResponse.data} />
    </main>
  );
}
