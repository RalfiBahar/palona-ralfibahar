export type ProductCard = {
  id: string;
  title?: string | null;
  brand?: string | null;
  image_url?: string | null;
  price_cents?: number | null;
  currency?: string;
  in_stock?: boolean;
  url?: string | null;
  badges?: string[] | null;
};

export type ProductDetail = ProductCard & {
  category?: string[] | null;
  description?: string | null;
  color?: string[] | null;
  material?: string[] | null;
  size?: string[] | null;
  gender?: string | null;
  attributes?: Record<string, unknown> | null;
  rating?: number | null;
  keywords?: string[] | null;
};

export type AgentChatRequest = {
  message: string;
  context?: Array<Record<string, unknown>> | null;
};

export type AgentChatResponse = {
  intent: "chitchat" | "text_recommendation" | "image_search" | "catalog_qna";
  answer: string;
  products?: ProductCard[] | null;
  refinements?: string[] | null;
};

export type UploadResponse = {
  upload_id: string;
  url: string;
};

async function http<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export const ApiClient = {
  async chat(
    body: AgentChatRequest,
    signal?: AbortSignal
  ): Promise<AgentChatResponse> {
    return http<AgentChatResponse>("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  },

  async uploadImage(file: File, signal?: AbortSignal): Promise<UploadResponse> {
    const form = new FormData();
    form.append("file", file);
    return http<UploadResponse>("/api/uploads", {
      method: "POST",
      body: form,
      signal,
    });
  },

  async getProduct(
    productId: string,
    signal?: AbortSignal
  ): Promise<ProductDetail> {
    const isServer = typeof window === "undefined";
    const base = isServer
      ? process.env.API_BASE_URL || "http://localhost:8000"
      : "";
    const url = `${base}/products/${productId}`;
    return http<ProductDetail>(url, { signal });
  },
};

export function formatPrice(
  priceCents?: number | null,
  currency: string = "USD"
): string {
  if (priceCents == null) return "";
  const amount = priceCents / 100;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(amount);
  } catch {
    return `$${amount.toFixed(2)}`;
  }
}
