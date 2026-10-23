"use client";

import { useState } from "react";

import { EDGE, type Group, TAG } from "@/components/severity";

export type Box = { n: number; bbox: [number, number, number, number]; group: Group };

/** The uploaded image with each image finding's box drawn on it. Boxes are in the original image's
 * pixels, so they're placed as percentages of its natural size and scale with the thumbnail. */
export function ImageWithBoxes({ src, boxes }: { src: string; boxes: Box[] }) {
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  return (
    <figure className="space-y-2">
      <div className="relative inline-block max-w-full">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt="The uploaded image; its findings are listed with the others" className="block max-h-80 w-auto max-w-full"
          onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} />
        {size && boxes.map((b) => (
          <div key={b.n} aria-hidden data-testid={`image-box-${b.n}`}
            className={`absolute border-2 ${EDGE[b.group]} bg-transparent`}
            style={{
              left: `${(b.bbox[0] / size.w) * 100}%`,
              top: `${(b.bbox[1] / size.h) * 100}%`,
              width: `${((b.bbox[2] - b.bbox[0]) / size.w) * 100}%`,
              height: `${((b.bbox[3] - b.bbox[1]) / size.h) * 100}%`,
            }}>
            <span className={`absolute -left-0.5 -top-6 rounded border px-1.5 text-xs font-semibold ${TAG[b.group]}`}>{b.n}</span>
          </div>
        ))}
      </div>
      {boxes.length > 0 && (
        <figcaption className="text-xs text-muted-foreground">Numbered boxes match the findings with the same numbers.</figcaption>
      )}
    </figure>
  );
}
