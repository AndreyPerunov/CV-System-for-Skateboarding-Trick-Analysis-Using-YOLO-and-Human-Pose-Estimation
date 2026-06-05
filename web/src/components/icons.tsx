import * as React from "react";

type SvgProps = React.SVGProps<SVGSVGElement>;

const base = (props: SvgProps): SvgProps => ({
  width:        16,
  height:       16,
  viewBox:      "0 0 24 24",
  fill:         "none",
  stroke:       "currentColor",
  strokeWidth:  1.6,
  strokeLinecap:  "round",
  strokeLinejoin: "round",
  ...props,
});

export const IconPlay      = (p: SvgProps) => <svg {...base({ ...p, fill: "currentColor", stroke: "none" })}><path d="M7 5l12 7-12 7V5z" /></svg>;
export const IconPause     = (p: SvgProps) => <svg {...base(p)}><rect x={6}  y={5} width={4} height={14} rx={1} fill="currentColor" stroke="none" /><rect x={14} y={5} width={4} height={14} rx={1} fill="currentColor" stroke="none" /></svg>;
export const IconStepBack  = (p: SvgProps) => <svg {...base(p)}><path d="M18 5L8 12l10 7V5z" fill="currentColor" stroke="none" /><rect x={5} y={5} width={2} height={14} fill="currentColor" stroke="none" /></svg>;
export const IconStepFwd   = (p: SvgProps) => <svg {...base(p)}><path d="M6 5l10 7-10 7V5z" fill="currentColor" stroke="none" /><rect x={17} y={5} width={2} height={14} fill="currentColor" stroke="none" /></svg>;
export const IconLoop      = (p: SvgProps) => <svg {...base(p)}><path d="M17 2l4 4-4 4M3 12V8a4 4 0 014-4h13M7 22l-4-4 4-4M21 12v4a4 4 0 01-4 4H4" /></svg>;
export const IconVolume    = (p: SvgProps) => <svg {...base(p)}><path d="M11 5L6 9H2v6h4l5 4V5zM15.5 8.5a5 5 0 010 7M19 5a9 9 0 010 14" /></svg>;
export const IconUpload    = (p: SvgProps) => <svg {...base(p)}><path d="M12 3v12M7 8l5-5 5 5M5 21h14" /></svg>;
export const IconGrid      = (p: SvgProps) => <svg {...base(p)}><rect x={3}  y={3}  width={7} height={7} rx={1} /><rect x={14} y={3}  width={7} height={7} rx={1} /><rect x={3}  y={14} width={7} height={7} rx={1} /><rect x={14} y={14} width={7} height={7} rx={1} /></svg>;
export const IconBody      = (p: SvgProps) => <svg {...base(p)}><circle cx={12} cy={5} r={2} /><path d="M12 7v5M8 11l4 1 4-1M9 21l3-9 3 9M10 13l-2 5M14 13l2 5" /></svg>;
export const IconBoard     = (p: SvgProps) => <svg {...base(p)}><rect x={3} y={10} width={18} height={4} rx={2} /><circle cx={7} cy={17} r={1.5} /><circle cx={17} cy={17} r={1.5} /></svg>;
export const IconMask      = (p: SvgProps) => <svg {...base(p)}><path d="M3 12c2-5 6-7 9-7s7 2 9 7c-2 5-6 7-9 7s-7-2-9-7z" /></svg>;
export const IconAxes      = (p: SvgProps) => <svg {...base(p)}><path d="M5 19V5M5 19h14M5 12h6M12 19v-6" /></svg>;
export const IconKnee      = (p: SvgProps) => <svg {...base(p)}><path d="M7 3v6l-3 5M17 3v6l3 5M7 9l5 4 5-4M9 21h6" /></svg>;
export const IconCoM       = (p: SvgProps) => <svg {...base(p)}><circle cx={12} cy={12} r={3} /><circle cx={12} cy={12} r={9} /><path d="M12 3v2M12 19v2M3 12h2M19 12h2" /></svg>;
