export function fmtTime(s: number, fps = 60): string {
  if (!isFinite(s)) s = 0;
  const m   = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  const fr  = Math.floor((s % 1) * fps);
  return `${m}:${sec.toString().padStart(2, "0")}.${fr.toString().padStart(2, "0")}`;
}

export function fmtClock(s: number): string {
  const m   = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}
