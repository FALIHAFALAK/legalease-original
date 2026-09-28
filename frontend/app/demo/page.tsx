
"use client";

import { useMemo, useState } from "react";

const documents = [
  {
    id: "nda",
    title: "Mutual Non-Disclosure Agreement",
    category: "Business",
    description: "Protect confidential information shared between two parties.",
    content: `MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is entered into between [Party One] and [Party Two].

1. PURPOSE
The parties wish to exchange confidential information for a permitted business purpose.

2. CONFIDENTIAL INFORMATION
Confidential information includes business plans, financial information, technical information, and other non-public information disclosed by either party.

3. OBLIGATIONS
Each party agrees to protect confidential information and not disclose it to unauthorized persons.

4. TERM
The parties may specify the duration of confidentiality obligations in the final agreement.

5. GENERAL
This sample is for demonstration only and must be reviewed and adapted before any real-world use.

Party One: [Party One]
Party Two: [Party Two]
Date: [Date]`,
  },
  {
    id: "rental",
    title: "Residential Rental Agreement",
    category: "Property",
    description: "A sample agreement for a residential rental arrangement.",
    content: `RESIDENTIAL RENTAL AGREEMENT

This Agreement is made between [Landlord Name] and [Tenant Name].

1. PROPERTY
The landlord agrees to rent the property located at [Property Address] to the tenant.

2. RENT
Monthly rent: [Monthly Rent]
Security deposit: [Security Deposit]

3. TERM
Tenancy begins on [Start Date] and ends on [End Date], subject to the final agreed terms.

4. RESPONSIBILITIES
The parties shall agree on maintenance, utility payments, and other responsibilities.

5. GENERAL
All terms must be reviewed for compliance with applicable local law before signing.

Landlord: [Landlord Name]
Tenant: [Tenant Name]
Date: [Date]`,
  },
  {
    id: "employment",
    title: "Employment Agreement",
    category: "Employment",
    description: "A sample agreement describing employment terms and responsibilities.",
    content: `EMPLOYMENT AGREEMENT

This Agreement is between [Employer Name] and [Employee Name].

1. POSITION
The employee will serve as [Job Title].

2. START DATE
Employment begins on [Start Date].

3. COMPENSATION
Compensation: [Salary]
Payment frequency: [Payment Frequency]

4. RESPONSIBILITIES
The employee agrees to perform the duties associated with the position and follow applicable workplace policies.

5. CONFIDENTIALITY
The employee shall protect confidential business information as agreed by the parties.

6. GENERAL
This sample requires appropriate legal and professional review before use.

Employer: [Employer Name]
Employee: [Employee Name]
Date: [Date]`,
  },
];

export default function DemoPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [selected, setSelected] = useState<(typeof documents)[number] | null>(null);
  const [showGenerator, setShowGenerator] = useState(false);
  const [partyOne, setPartyOne] = useState("");
  const [partyTwo, setPartyTwo] = useState("");
  const [date, setDate] = useState("");
  const [generated, setGenerated] = useState("");

  const filtered = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch =
        doc.title.toLowerCase().includes(search.toLowerCase()) ||
        doc.description.toLowerCase().includes(search.toLowerCase());

      const matchesCategory =
        category === "All" || doc.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [search, category]);

  function openGenerator(doc: (typeof documents)[number]) {
    setSelected(doc);
    setPartyOne("");
    setPartyTwo("");
    setDate("");
    setGenerated("");
    setShowGenerator(true);
  }

  function generateDocument() {
    if (!selected || !partyOne.trim() || !partyTwo.trim()) {
      alert("Please enter both party names.");
      return;
    }

    let text = selected.content;

    const replacements: Record<string, string> = {
      "[Party One]": partyOne,
      "[Party Two]": partyTwo,
      "[Landlord Name]": partyOne,
      "[Tenant Name]": partyTwo,
      "[Employer Name]": partyOne,
      "[Employee Name]": partyTwo,
      "[Date]": date || "Not specified",
    };

    Object.entries(replacements).forEach(([key, value]) => {
      text = text.split(key).join(value);
    });

    setGenerated(text);
  }

  function printDocument() {
    if (!generated) return;

    const w = window.open("", "_blank");

    if (!w) {
      alert("Please allow pop-ups to print your document.");
      return;
    }

    w.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>LegalEase Sample Document</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              max-width: 750px;
              margin: 50px auto;
              padding: 30px;
              color: #222;
              line-height: 1.8;
              white-space: pre-wrap;
            }
            h2 {
              font-size: 14px;
              color: #777;
              border-bottom: 1px solid #ddd;
              padding-bottom: 12px;
            }
            @media print {
              body { margin: 20px; }
            }
          </style>
        </head>
        <body>
          <h2>LEGALEASE · SAMPLE DOCUMENT</h2>
          ${generated.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}
          <p style="margin-top:40px;font-size:12px;color:#777">
            Demonstration only. Not a legal document or legal advice.
          </p>
          <script>
            window.onload = () => window.print();
          </script>
        </body>
      </html>
    `);

    w.document.close();
  }

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-[#20342b]">
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm text-amber-900">
        Demo mode: Sample data only. No real legal documents are
        created or saved.
      </div>

      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-stone-200 bg-white p-6 md:block">
          <a href="/" className="mb-10 block">
            <div className="text-2xl font-bold tracking-tight text-emerald-900">
              LegalEase<span className="text-amber-600">.</span>
            </div>
            <p className="mt-1 text-xs text-stone-500">
              Legal documents, simplified
            </p>
          </a>

          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-stone-400">
            Workspace
          </p>

          <button
            onClick={() => {
              setSelected(null);
              setShowGenerator(false);
            }}
            className="mb-2 w-full rounded-xl bg-emerald-50 px-4 py-3 text-left font-medium text-emerald-900"
          >
            ◫ &nbsp; Dashboard
          </button>

          <button
            onClick={() => {
              setCategory("All");
              setSearch("");
              setSelected(null);
              setShowGenerator(false);
            }}
            className="mb-2 w-full rounded-xl px-4 py-3 text-left text-stone-600 hover:bg-stone-100"
          >
            ▤ &nbsp; Templates
          </button>

          <button
            onClick={() => openGenerator(documents[0])}
            className="w-full rounded-xl px-4 py-3 text-left text-stone-600 hover:bg-stone-100"
          >
            ✧ &nbsp; Create document
          </button>

          <div className="mt-16 rounded-2xl bg-[#203e32] p-5 text-white">
            <p className="text-sm font-semibold">Need legal help?</p>
            <p className="mt-2 text-xs leading-5 text-emerald-100">
              This is a frontend demonstration. Consult a qualified
              lawyer for actual legal matters.
            </p>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="flex items-center justify-between border-b border-stone-200 bg-white px-5 py-5 md:px-10">
            <div>
              <p className="text-xs text-stone-500 md:hidden">
                LEGALEASE
              </p>
              <h1 className="text-lg font-semibold">Demo Workspace</h1>
            </div>

            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-medium text-emerald-800">
              ● Demo account
            </span>
          </header>

          <div className="mx-auto max-w-6xl p-5 md:p-10">
            {!selected && !showGenerator && (
              <>
                <div className="relative overflow-hidden rounded-3xl bg-[#203e32] p-7 text-white md:p-12">
                  <div className="relative z-10 max-w-2xl">
                    <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">
                      YOUR LEGAL WORKSPACE
                    </p>

                    <h2 className="text-3xl font-semibold leading-tight md:text-5xl">
                      Legal documents,
                      <br />
                      made simpler.
                    </h2>

                    <p className="mt-5 max-w-lg text-sm leading-6 text-emerald-100 md:text-base">
                      Explore sample templates and create a
                      personalized demonstration document in seconds.
                    </p>

                    <button
                      onClick={() => openGenerator(documents[0])}
                      className="mt-8 rounded-xl bg-white px-6 py-3 font-semibold text-emerald-950 transition hover:bg-emerald-50"
                    >
                      + Create a document
                    </button>
                  </div>

                  <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full border border-emerald-300/20 md:h-96 md:w-96" />
                  <div className="absolute -right-4 -top-4 h-48 w-48 rounded-full border border-emerald-300/20 md:h-72 md:w-72" />
                </div>

                <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  {[
                    ["03", "Sample templates"],
                    ["03", "Document categories"],
                    ["100%", "Demo mode"],
                  ].map(([value, label]) => (
                    <div
                      key={label}
                      className="rounded-2xl border border-stone-200 bg-white p-6"
                    >
                      <p className="text-3xl font-semibold">{value}</p>
                      <p className="mt-2 text-sm text-stone-500">{label}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-10">
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-widest text-emerald-800">
                        LIBRARY
                      </p>
                      <h2 className="mt-2 text-2xl font-semibold">
                        Explore templates
                      </h2>
                      <p className="mt-2 text-sm text-stone-500">
                        Select a template to read or create a sample.
                      </p>
                    </div>

                    <span className="text-sm text-stone-500">
                      {filtered.length} templates
                    </span>
                  </div>

                  <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search documents..."
                      className="min-w-0 flex-1 rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm outline-none focus:border-emerald-700"
                    />

                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm outline-none focus:border-emerald-700"
                    >
                      <option>All</option>
                      <option>Business</option>
                      <option>Property</option>
                      <option>Employment</option>
                    </select>
                  </div>

                  <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                    {filtered.map((doc) => (
                      <article
                        key={doc.id}
                        className="group rounded-2xl border border-stone-200 bg-white p-6 transition hover:-translate-y-1 hover:border-emerald-300 hover:shadow-lg"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-xl text-emerald-900">
                            ▤
                          </div>
                          <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-600">
                            {doc.category}
                          </span>
                        </div>

                        <h3 className="mt-5 text-lg font-semibold leading-7">
                          {doc.title}
                        </h3>

                        <p className="mt-3 min-h-12 text-sm leading-6 text-stone-500">
                          {doc.description}
                        </p>

                        <div className="mt-6 flex gap-3">
                          <button
                            onClick={() => setSelected(doc)}
                            className="flex-1 rounded-xl border border-stone-200 px-3 py-3 text-sm font-medium transition hover:bg-stone-50"
                          >
                            Read
                          </button>
                          <button
                            onClick={() => openGenerator(doc)}
                            className="flex-1 rounded-xl bg-emerald-900 px-3 py-3 text-sm font-medium text-white transition hover:bg-emerald-800"
                          >
                            Use template
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>

                  {filtered.length === 0 && (
                    <p className="mt-8 rounded-xl bg-white p-8 text-center text-stone-500">
                      No templates found. Try another search.
                    </p>
                  )}
                </div>
              </>
            )}

            {selected && !showGenerator && (
              <div className="mx-auto max-w-3xl">
                <button
                  onClick={() => setSelected(null)}
                  className="mb-6 text-sm font-medium text-emerald-800 hover:underline"
                >
                  ← Back to templates
                </button>

                <div className="rounded-3xl border border-stone-200 bg-white p-6 md:p-10">
                  <span className="text-xs font-semibold uppercase tracking-widest text-emerald-800">
                    {selected.category} · SAMPLE
                  </span>

                  <h2 className="mt-4 text-2xl font-semibold md:text-3xl">
                    {selected.title}
                  </h2>

                  <p className="mt-3 text-sm text-stone-500">
                    {selected.description}
                  </p>

                  <pre className="mt-8 whitespace-pre-wrap rounded-xl bg-stone-50 p-5 text-sm leading-7 text-stone-700">
                    {selected.content}
                  </pre>

                  <button
                    onClick={() => openGenerator(selected)}
                    className="mt-6 rounded-xl bg-emerald-900 px-6 py-3 font-medium text-white hover:bg-emerald-800"
                  >
                    Customize this template
                  </button>
                </div>
              </div>
            )}

            {showGenerator && selected && (
              <div className="mx-auto max-w-3xl">
                <button
                  onClick={() => {
                    setShowGenerator(false);
                    setGenerated("");
                  }}
                  className="mb-6 text-sm font-medium text-emerald-800 hover:underline"
                >
                  ← Back to dashboard
                </button>

                <div className="rounded-3xl border border-stone-200 bg-white p-6 md:p-10">
                  <span className="text-xs font-semibold uppercase tracking-widest text-emerald-800">
                    DOCUMENT BUILDER · DEMO
                  </span>

                  <h2 className="mt-4 text-2xl font-semibold">
                    Create a sample document
                  </h2>

                  <p className="mt-2 text-sm text-stone-500">
                    Template: {selected.title}
                  </p>

                  <div className="mt-8 grid gap-5">
                    <label className="text-sm font-medium">
                      First party / organization
                      <input
                        value={partyOne}
                        onChange={(e) => setPartyOne(e.target.value)}
                        placeholder="Enter first party name"
                        className="mt-2 w-full rounded-xl border border-stone-200 px-4 py-3 font-normal outline-none focus:border-emerald-700"
                      />
                    </label>

                    <label className="text-sm font-medium">
                      Second party / organization
                      <input
                        value={partyTwo}
                        onChange={(e) => setPartyTwo(e.target.value)}
                        placeholder="Enter second party name"
                        className="mt-2 w-full rounded-xl border border-stone-200 px-4 py-3 font-normal outline-none focus:border-emerald-700"
                      />
                    </label>

                    <label className="text-sm font-medium">
                      Date
                      <input
                        type="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                        className="mt-2 w-full rounded-xl border border-stone-200 px-4 py-3 font-normal outline-none focus:border-emerald-700"
                      />
                    </label>
                  </div>

                  <button
                    onClick={generateDocument}
                    className="mt-7 w-full rounded-xl bg-emerald-900 px-6 py-4 font-semibold text-white transition hover:bg-emerald-800"
                  >
                    Generate sample document
                  </button>

                  {generated && (
                    <div className="mt-8 border-t border-stone-200 pt-8">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h3 className="text-xl font-semibold">
                          Your sample document
                        </h3>
                        <button
                          onClick={printDocument}
                          className="rounded-xl bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-900 hover:bg-emerald-100"
                        >
                          Print / Save PDF
                        </button>
                      </div>

                      <pre className="mt-5 whitespace-pre-wrap rounded-xl bg-stone-50 p-5 text-sm leading-7 text-stone-700">
                        {generated}
                      </pre>

                      <p className="mt-4 text-xs leading-5 text-amber-800">
                        Demonstration only. This document is not legal
                        advice and should not be used as a final legal
                        agreement.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <footer className="mt-16 border-t border-stone-200 py-6 text-center text-xs leading-6 text-stone-500">
              © 2026 LegalEase · Interactive frontend demonstration.
              <br />
              No real documents are saved or transmitted.
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}
