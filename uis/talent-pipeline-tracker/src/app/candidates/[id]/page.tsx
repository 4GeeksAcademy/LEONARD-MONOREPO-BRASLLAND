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
  const result = useApiData(id, () => Promise.all([
      getCandidateById(id),
      getCandidateNotes(id),
  ]));
  if (result?.error) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <article className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <h1 className="text-xl font-black text-red-900">Could not load candidate profile</h1>
          <p className="mt-2 text-sm text-red-800">{result.error}</p>
        </article>
      </main>
    );
  }
  if (!result?.data) return <main className="auth-status" role="status">Loading candidate...</main>;
  const [candidate, notesResponse] = result.data;

  return (
    <main className="mx-auto max-w-5xl space-y-4 px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/" className="text-sm font-semibold text-amber-700">
        Back to candidate list
      </Link>
      <CandidateDetailClient initialCandidate={candidate} initialNotes={notesResponse.data} />
    </main>
  );
}
