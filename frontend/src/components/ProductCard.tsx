import Link from "next/link";
import type { ProductCard as ApiProduct } from "@/lib/api";
import { formatPrice } from "@/lib/api";

type Props = {
  product: ApiProduct;
  onOpenPdp?: (productId: string) => void;
};

export default function ProductCard({ product, onOpenPdp }: Props) {
  const handleOpen = () => {
    if (product.url) {
      window.open(product.url, "_blank", "noopener,noreferrer");
    } else if (onOpenPdp) {
      onOpenPdp(product.id);
    }
  };

  return (
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
      <div className="space-y-1 p-3">
        <div className="line-clamp-2 text-sm font-medium text-neutral-900">
          {product.title || "Untitled"}
        </div>
        <div className="text-sm text-neutral-600">
          {formatPrice(product.price_cents, product.currency || "USD")}
        </div>
        <div className="mt-2">
          {/*q<button className="btn w-full border" onClick={handleOpen}>
            Open PDP
          </button>*/}
          <a
            className="btn w-full border"
            href={`/products/${product.id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Show Details
          </a>
        </div>
      </div>
    </div>
  );
}
