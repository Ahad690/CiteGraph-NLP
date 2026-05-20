import { useEffect, useState } from "react";

export function CookieConsent() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem("cgnlp_cookie")) return;
    const t = setTimeout(() => setShow(true), 2000);
    return () => clearTimeout(t);
  }, []);

  if (!show) return null;
  const set = (v: string) => {
    localStorage.setItem("cgnlp_cookie", v);
    setShow(false);
  };

  return (
    <div className="fixed bottom-4 inset-x-4 md:left-auto md:right-6 md:max-w-md z-50 animate-slide-up">
      <div className="rounded-2xl border border-cyan-400/30 bg-slate-950/90 backdrop-blur-xl p-5 shadow-2xl shadow-black/40">
        <p className="text-sm text-slate-200">
          We use cookies to improve the research experience and understand product usage.
        </p>
        <div className="mt-4 flex gap-2 justify-end">
          <button onClick={() => set("declined")} className="px-3 py-2 text-sm text-slate-300 hover:text-white">Decline</button>
          <button onClick={() => set("accepted")} className="px-4 py-2 text-sm rounded-lg bg-gradient-to-r from-indigo to-cyan text-white font-semibold">
            Accept All
          </button>
        </div>
      </div>
    </div>
  );
}
