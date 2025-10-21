import Link from "next/link";

export default function HomePage() {
  return (
    <main
      className="min-h-dvh flex flex-col items-center justify-center gap-8 p-6 text-center"
      style={{
        background: "linear-gradient(180deg, #FFFBF1 0%, #ffffff 100%)",
      }}
    >
      <div className="max-w-2xl">
        <div className="inline-block rounded-full bg-[hsl(var(--brand-plum))]/10 px-3 py-1 text-xs font-semibold text-[hsl(var(--brand-plum))]">
          Palona
        </div>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-[hsl(var(--brand-plum))] sm:text-5xl">
          Shop with an AI Agent
        </h1>
        <p className="mt-3 text-neutral-600">
          Ask questions, refine with chips, and explore a curated product grid.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link href="/chat" className="btn-primary">
            Open Chat
          </Link>
        </div>
      </div>
    </main>
  );
}
