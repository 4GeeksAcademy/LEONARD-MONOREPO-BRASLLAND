import dynamic from "next/dynamic";
import Link from "next/link";

// The form is the heaviest component in the app and is only needed on create/edit routes.
const CandidateForm = dynamic(
  () => import("@/components/candidates/CandidateForm").then((module) => module.CandidateForm),
  { loading: () => <p className="auth-status" role="status">Loading form...</p> },
);

export default function NewCandidatePage() {
  return (
    <main className="mx-auto max-w-4xl space-y-4 px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/" className="text-sm font-semibold text-amber-700">
        Back to candidate list
      </Link>
      <CandidateForm mode="create" />
    </main>
  );
}
