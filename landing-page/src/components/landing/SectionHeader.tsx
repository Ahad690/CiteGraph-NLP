export function SectionHeader({
  badge,
  title,
  subtitle,
  align = "center",
}: {
  badge: string;
  title: React.ReactNode;
  subtitle?: string;
  align?: "center" | "left";
}) {
  return (
    <div className={`max-w-3xl ${align === "center" ? "mx-auto text-center" : ""}`}>
      <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.14em] text-cyan-200">
        {badge}
      </div>
      <h2 className="mt-4 text-3xl md:text-5xl font-bold tracking-tight text-white leading-tight">
        {title}
      </h2>
      {subtitle && <p className="mt-4 text-lg text-slate-300 leading-relaxed">{subtitle}</p>}
    </div>
  );
}
