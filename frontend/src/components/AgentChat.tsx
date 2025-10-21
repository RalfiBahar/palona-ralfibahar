"use client";
import { useEffect, useRef, useState } from "react";
import UploadButton from "@/components/UploadButton";
import RefineChips from "@/components/RefineChips";
import Message from "@/components/Message";
import { useAgentChat } from "@/lib/useAgentChat";
import type { ProductCard as ApiProduct } from "@/lib/api";

type Props = {
  onProducts?: (products: ApiProduct[]) => void;
};

export default function AgentChat({ onProducts }: Props) {
  const { state, sendText, uploadAndSearch, refineWith } = useAgentChat();
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [state.messages.length]);

  useEffect(() => {
    if (onProducts) {
      onProducts(state.products || []);
    }
  }, [onProducts, state.products]);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b pb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-[hsl(var(--brand-plum))]/10" />
          <div className="font-semibold text-[hsl(var(--brand-plum))]">
            Agent
          </div>
        </div>
        <UploadButton onUpload={(f) => void uploadAndSearch(f)} />
      </header>
      <div
        ref={listRef}
        className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1"
      >
        {state.messages.map((m) => (
          <Message key={m.id} role={m.role} content={m.content} />
        ))}
        {state.isLoading ? (
          <Message key="typing" role="assistant" content="" typing />
        ) : null}
      </div>
      <div className="mt-4">
        <RefineChips chips={state.refinements} onChip={(q) => refineWith(q)} />
      </div>
      <form
        className="mt-3 flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const text = input.trim();
          if (!text) return;
          setInput("");
          void sendText(text);
        }}
      >
        <input
          className="flex-1 rounded-md border px-3 py-2 outline-none focus:ring-2 focus:ring-[hsl(var(--brand-plum))]/40 placeholder-gray-500"
          placeholder="Ask about products, upload images, or refine..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          className="btn-primary"
          type="submit"
          disabled={state.isLoading}
        >
          {state.isLoading ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
