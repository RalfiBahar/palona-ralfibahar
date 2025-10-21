"use client";
import { useRef } from "react";

type Props = {
  onUpload?: (file: File) => void;
};

export default function UploadButton({ onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload?.(file);
        }}
        className="hidden"
      />
      <button
        type="button"
        className="btn border bg-[hsl(var(--brand-sand))] text-[hsl(var(--brand-plum))]"
        onClick={() => inputRef.current?.click()}
      >
        Upload Image
      </button>
    </>
  );
}
