type Props = {
  role: "user" | "assistant";
  content: string;
  typing?: boolean;
};

export default function Message({ role, content, typing }: Props) {
  const isUser = role === "user";
  const imageMatch = /^image:\s*([\w\-.]+)$/.exec(content.trim());
  const imageUrl = imageMatch ? `/uploads/${imageMatch[1]}` : null;
  return (
    <div
      className={`flex items-start gap-3 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="h-7 w-7 shrink-0 rounded-md bg-[hsl(var(--brand-plum))]/10" />
      )}
      <div
        className={`max-w-[80%] rounded-lg text-sm font-sans ${
          imageUrl
            ? "p-0"
            : isUser
            ? "px-3 py-2 bg-[hsl(var(--brand-plum))] text-white"
            : "px-3 py-2 bg-[hsl(var(--brand-sand))] text-[hsl(var(--brand-plum))] border"
        }`}
      >
        {typing && !isUser ? (
          <div className="typing flex items-center gap-1">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        ) : imageUrl && isUser ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt="Uploaded image"
            className="block max-w-[280px] max-h-[220px] rounded-md object-cover"
          />
        ) : (
          content
        )}
      </div>
    </div>
  );
}
