"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { ApiClient, type AgentChatResponse, type ProductCard } from "@/lib/api";

export type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type AgentState = {
  messages: UiMessage[];
  products: ProductCard[];
  refinements: string[];
  isLoading: boolean;
  lastUploadId?: string;
};

export function useAgentChat() {
  const [state, setState] = useState<AgentState>({
    messages: [
      {
        id: "m-welcome",
        role: "assistant",
        content:
          "Hi! I can help you find products. What are you looking for today?",
      },
    ],
    products: [],
    refinements: ["recommendations", "image search", "product details"],
    isLoading: false,
  });

  const abortRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const appendMessage = useCallback((msg: UiMessage) => {
    setState((prev) => ({ ...prev, messages: [...prev.messages, msg] }));
  }, []);

  const sendText = useCallback(
    async (text: string) => {
      const id = crypto.randomUUID();
      appendMessage({ id, role: "user", content: text });
      setState((prev) => ({ ...prev, isLoading: true }));

      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;

      try {
        const context = state.messages
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));
        const resp = await ApiClient.chat(
          { message: text, context },
          ac.signal
        );
        handleAgentResponse(resp);
      } catch (e: unknown) {
        const err = e as Error;
        appendMessage({
          id: crypto.randomUUID(),
          role: "assistant",
          content: err.message || "Something went wrong",
        });
      } finally {
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    },
    [appendMessage]
  );

  const uploadAndSearch = useCallback(
    async (file: File) => {
      setState((prev) => ({ ...prev, isLoading: true }));
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;

      try {
        const up = await ApiClient.uploadImage(file, ac.signal);
        setState((prev) => ({ ...prev, lastUploadId: up.upload_id }));
        const marker = `image:${up.upload_id}`;
        appendMessage({
          id: crypto.randomUUID(),
          role: "user",
          content: marker,
        });
        const context = state.messages
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));
        const resp = await ApiClient.chat(
          { message: marker, context },
          ac.signal
        );
        handleAgentResponse(resp);
      } catch (e: unknown) {
        const err = e as Error;
        appendMessage({
          id: crypto.randomUUID(),
          role: "assistant",
          content: err.message || "Upload failed",
        });
      } finally {
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    },
    [appendMessage]
  );

  const refineWith = useCallback(
    (chip: string) => {
      void sendText(chip);
    },
    [sendText]
  );

  const handleAgentResponse = useCallback(
    (resp: AgentChatResponse) => {
      appendMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: resp.answer,
      });
      setState((prev) => ({
        ...prev,
        products: resp.products ?? [],
        refinements: resp.refinements ?? prev.refinements,
      }));
    },
    [appendMessage]
  );

  const api = useMemo(
    () => ({ sendText, uploadAndSearch, refineWith, cancel }),
    [sendText, uploadAndSearch, refineWith, cancel]
  );

  return { state, ...api } as const;
}
