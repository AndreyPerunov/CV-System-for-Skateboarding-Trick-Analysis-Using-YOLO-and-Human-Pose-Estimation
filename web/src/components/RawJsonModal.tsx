"use client"

import { useEffect, useState } from "react"

interface Props {
  open: boolean
  data: unknown
  title?: string
  onClose: () => void
}

export function RawJsonModal({ open, data, title = "Raw analysis JSON", onClose }: Props) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    document.body.style.overflow = "hidden"
    return () => {
      window.removeEventListener("keydown", onKey)
      document.body.style.overflow = ""
    }
  }, [open, onClose])

  if (!open) return null

  const json = JSON.stringify(data, null, 2)

  async function copy() {
    try {
      await navigator.clipboard.writeText(json)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {}
  }

  function download() {
    const blob = new Blob([json], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "analysis.json"
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">{title}</div>
          <div className="modal-meta mono">
            {(json.length / 1024).toFixed(1)} KB · {json.split("\n").length.toLocaleString()} lines
          </div>
          <button className="btn btn-sm" onClick={copy}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button className="btn btn-sm" onClick={download}>
            Download
          </button>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <pre className="modal-body mono">{json}</pre>
      </div>
    </div>
  )
}
