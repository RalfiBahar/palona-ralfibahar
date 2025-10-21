type Props = {
  chips?: string[];
  onChip?: (query: string) => void;
};

const defaultChips = [
  "under $50",
  "free shipping",
  "eco-friendly",
  "best sellers",
];

export default function RefineChips({ chips = defaultChips, onChip }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((c: string) => (
        <button
          key={c}
          type="button"
          className="chip border-neutral-200 bg-white hover:bg-[hsl(var(--brand-sand))]"
          onClick={() => onChip?.(c)}
        >
          {c}
        </button>
      ))}
    </div>
  );
}
