import { ApiClient, formatPrice, type ProductDetail } from "@/lib/api";
import Link from "next/link";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProductPage({ params }: PageProps) {
  const { id } = await params;
  let product: ProductDetail | null = null;
  try {
    product = await ApiClient.getProduct(id);
  } catch {
    product = null;
  }

  if (!product) {
    return (
      <main className="min-h-dvh p-6">
        <div className="mx-auto max-w-3xl">
          <div className="card p-6">
            <div className="text-sm text-neutral-700">Product not found.</div>
            <div className="mt-4">
              <Link className="btn border" href="/chat">
                Back to chat
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-dvh p-4 md:p-6">
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-[1.1fr,1.2fr]">
        <div className="card overflow-hidden">
          <div className="aspect-4/3 w-full bg-neutral-100">
            {product.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={product.image_url}
                alt={product.title || "Product"}
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>
        </div>
        <div className="card p-4 md:p-6">
          <div className="text-xs text-neutral-500">{product.brand || ""}</div>
          <h1 className="mt-1 text-xl font-semibold text-neutral-900">
            {product.title || "Product"}
          </h1>
          <div className="mt-2 text-lg text-neutral-800">
            {formatPrice(product.price_cents, product.currency || "USD")}
          </div>

          {product.description ? (
            <p className="mt-4 text-sm leading-6 text-neutral-700">
              {product.description}
            </p>
          ) : null}

          <div className="mt-6 flex flex-wrap gap-2">
            {product.color?.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
            {product.size?.map((s) => (
              <span key={s} className="chip">
                {s}
              </span>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-2">
            {product.url ? (
              <a
                className="btn-primary"
                href={product.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                Buy now
              </a>
            ) : null}
            <Link className="btn border" href="/chat">
              Back to chat
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
