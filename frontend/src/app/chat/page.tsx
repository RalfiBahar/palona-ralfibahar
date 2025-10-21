"use client";
import { useMemo, useState } from "react";
import { AgentChat, ProductGrid } from "@/components";
import type { ProductCard } from "@/lib/api";
import { ApiClient } from "@/lib/api";

export default function ChatPage() {
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [modal, setModal] = useState<{ open: boolean; content?: string }>(
    () => ({ open: false })
  );

  const onProducts = (list: ProductCard[]) => {
    setProducts(list);
  };

  const openPdp = async (productId: string) => {
    try {
      const detail = await ApiClient.getProduct(productId);
      setModal({
        open: true,
        content: `${detail.title || "Product"} — ${detail.brand || ""}`,
      });
    } catch (e) {
      setModal({ open: true, content: "Failed to load product details." });
    }
  };

  const closeModal = () => setModal({ open: false });

  return (
    <main
      className="min-h-dvh grid grid-cols-1 gap-4 p-4 md:grid-cols-[1.1fr,1.4fr] md:gap-6 md:p-6"
      style={{
        background: "linear-gradient(180deg, #FFFBF1 0%, #ffffff 100%)",
      }}
    >
      <section className="card p-4 md:p-6">
        <AgentChat onProducts={onProducts} />
      </section>
      <section className="card p-4 md:p-6">
        {/* ProductGrid displays products; AgentChat currently holds them. We'll pass empty here and rely on a shared source soon. */}
        <ProductGrid products={products} onOpenPdp={openPdp} />
      </section>

      {modal.open ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm text-neutral-900">{modal.content}</div>
            <div className="flex justify-end">
              <button className="btn border" onClick={closeModal}>
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
