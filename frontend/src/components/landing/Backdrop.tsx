export function Backdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #94a3b8 1px, transparent 1px), linear-gradient(to bottom, #94a3b8 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse at center, black 40%, transparent 75%)",
        }}
      />
      <div className="absolute -top-32 -left-32 w-[480px] h-[480px] rounded-full bg-indigo/20 blur-[120px] animate-float" />
      <div className="absolute top-20 -right-32 w-[420px] h-[420px] rounded-full bg-cyan/20 blur-[120px] animate-float" style={{ animationDelay: "1.5s" }} />
      <div className="absolute bottom-0 left-1/3 w-[420px] h-[420px] rounded-full bg-purple/15 blur-[140px] animate-float" style={{ animationDelay: "3s" }} />
    </div>
  );
}
