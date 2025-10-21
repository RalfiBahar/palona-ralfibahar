import ProductCard from "@/components/ProductCard";
import type { ProductCard as ApiProduct } from "@/lib/api";

type Props = {
  products: ApiProduct[];
  onOpenPdp?: (productId: string) => void;
};

export default function ProductGrid({ products, onOpenPdp }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} onOpenPdp={onOpenPdp} />
      ))}
    </div>
  );
}
