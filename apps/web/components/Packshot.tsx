/** A flat packshot of each Aurelle (fictional) product, drawn in SVG so it needs no photography. */
type Shape = "dropper" | "jar" | "tube" | "pump" | "stick" | "brand";
const PRODUCTS: Record<string, { shape: Shape; body: string; cap: string; label: string }> = {
  "Vitamin C Brightening Serum": { shape: "dropper", body: "#E8892B", cap: "#1B1B1F", label: "VIT C" },
  "Niacinamide 10% Clarifying Serum": { shape: "dropper", body: "#7FB89A", cap: "#1B1B1F", label: "NIA 10" },
  "Retinal Night Serum": { shape: "dropper", body: "#5B4AA8", cap: "#C9C3E8", label: "RETINAL" },
  "Kumkumadi Glow Oil": { shape: "dropper", body: "#B23A2A", cap: "#D9A441", label: "KUMKUMADI" },
  "Hyaluronic Water Gel": { shape: "jar", body: "#8EC5E8", cap: "#EDEBE6", label: "HYA GEL" },
  "Ceramide Barrier Cream": { shape: "jar", body: "#E9DCC6", cap: "#B89B6E", label: "CERAMIDE" },
  "SPF 50 Daily Sunscreen": { shape: "tube", body: "#F2C94C", cap: "#EDEBE6", label: "SPF 50" },
  "Gentle Rice Cleanser": { shape: "pump", body: "#EDEBE6", cap: "#9B9AA1", label: "RICE" },
  "Tinted Lip Balm": { shape: "stick", body: "#E78BA5", cap: "#EDEBE6", label: "LIP" },
};

export function Packshot({ product, className = "size-16" }: { product: string | null; className?: string }) {
  const p = (product && PRODUCTS[product]) || { shape: "brand" as Shape, body: "#4B3FD1", cap: "#EDEBE6", label: "AURELLE" };
  return (
    <svg viewBox="0 0 64 96" className={className} role="img" aria-label={product ? `${product} (illustration)` : "Aurelle brand"}>
      <ellipse cx="32" cy="92" rx="20" ry="3" fill="#000" opacity=".45" />
      {p.shape === "dropper" && (
        <>
          <rect x="27" y="4" width="10" height="16" rx="5" fill={p.cap} />
          <rect x="24" y="18" width="16" height="10" rx="2" fill={p.cap} />
          <rect x="16" y="28" width="32" height="62" rx="7" fill={p.body} />
          <rect x="19" y="32" width="5" height="50" rx="2.5" fill="#fff" opacity=".22" />
        </>
      )}
      {p.shape === "jar" && (
        <>
          <rect x="10" y="40" width="44" height="12" rx="3" fill={p.cap} />
          <rect x="8" y="50" width="48" height="40" rx="8" fill={p.body} />
          <rect x="12" y="54" width="6" height="30" rx="3" fill="#fff" opacity=".25" />
        </>
      )}
      {p.shape === "tube" && (
        <>
          <path d="M14 6 h36 l-4 66 h-28 z" fill={p.body} />
          <rect x="22" y="72" width="20" height="18" rx="3" fill={p.cap} />
          <rect x="18" y="10" width="4" height="56" rx="2" fill="#fff" opacity=".25" />
        </>
      )}
      {p.shape === "pump" && (
        <>
          <rect x="22" y="4" width="22" height="5" rx="2" fill={p.cap} />
          <rect x="29" y="8" width="6" height="12" fill={p.cap} />
          <rect x="24" y="18" width="16" height="8" rx="2" fill={p.cap} />
          <rect x="14" y="26" width="36" height="64" rx="9" fill={p.body} />
          <rect x="18" y="30" width="5" height="54" rx="2.5" fill="#fff" opacity=".35" />
        </>
      )}
      {p.shape === "stick" && (
        <>
          <rect x="24" y="14" width="16" height="22" rx="7" fill={p.body} />
          <rect x="20" y="34" width="24" height="56" rx="4" fill={p.cap} />
          <rect x="20" y="34" width="24" height="10" fill={p.body} opacity=".6" />
        </>
      )}
      {p.shape === "brand" && (
        <>
          <line x1="32" y1="4" x2="32" y2="40" stroke="#EDEBE6" strokeWidth="1.5" />
          <path d="M32 40 L48 62 L32 90 L16 62 Z" fill={p.body} />
        </>
      )}
      {p.shape !== "brand" && p.shape !== "stick" && (
        <text x="32" y={p.shape === "jar" ? 74 : 64} textAnchor="middle" fontSize="6.5" fontWeight="800" letterSpacing=".5"
          fill="#0C0C0E" opacity=".8" style={{ fontStretch: "72%" }}>{p.label}</text>
      )}
    </svg>
  );
}
