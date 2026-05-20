interface Props {
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({ rows = 4, className = "" }: Props) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-14" />
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return <div className="skeleton h-32 rounded-2xl" />;
}
