
"use client";

import Link from "next/link";

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-stone-50 px-6 py-12 text-stone-900">
      <div className="mx-auto max-w-4xl">
        <p className="mb-3 text-sm font-medium uppercase tracking-widest text-emerald-700">
          LegalEase · Interactive Demo
        </p>

        <h1 className="mb-4 text-4xl font-bold">
          Welcome to LegalEase
        </h1>

        <p className="mb-8 max-w-2xl text-lg text-stone-600">
          Explore a sample legal document dashboard. This is a
          demonstration using sample data, not a live legal service.
        </p>

        <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold">
            Sample Documents
          </h2>

          <div className="space-y-4">
            <div className="rounded-xl bg-stone-50 p-4">
              <h3 className="font-semibold">
                Mutual Non-Disclosure Agreement
              </h3>
              <p className="mt-1 text-sm text-stone-600">
                Status: Sample · Ready to explore
              </p>
            </div>

            <div className="rounded-xl bg-stone-50 p-4">
              <h3 className="font-semibold">
                Rental Agreement
              </h3>
              <p className="mt-1 text-sm text-stone-600">
                Status: Sample · Ready to explore
              </p>
            </div>

            <div className="rounded-xl bg-stone-50 p-4">
              <h3 className="font-semibold">
                Employment Agreement
              </h3>
              <p className="mt-1 text-sm text-stone-600">
                Status: Sample · Ready to explore
              </p>
            </div>
          </div>

          <p className="mt-6 text-sm text-amber-700">
            Demo mode: These are sample documents. No real legal
            documents are created or saved.
          </p>
        </div>

        <Link
          href="/"
          className="mt-8 inline-block rounded-lg bg-emerald-800 px-6 py-3 font-medium text-white hover:bg-emerald-700"
        >
          Back to LegalEase
        </Link>
      </div>
    </main>
  );
}
