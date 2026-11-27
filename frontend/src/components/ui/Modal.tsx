import { useEffect, useId, useLayoutEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface ModalProps {
  onClose: () => void
  restoreFocus: () => void
  title: string
  children: ReactNode
}

export default function Modal({ onClose, restoreFocus, title, children }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useLayoutEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    dialog.showModal()
    dialog.querySelector<HTMLElement>('[data-dialog-initial-focus]')?.focus()
    return () => dialog.close()
  }, [])

  // Run after the parent commits so a removed trigger can fall back to a remaining control.
  useEffect(() => restoreFocus, [restoreFocus])

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="m-auto max-h-[calc(100%-2rem)] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-0 text-slate-100 shadow-2xl backdrop:bg-black/60 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onKeyDown={(event) => {
        if (event.key !== 'Tab' || event.ctrlKey || event.altKey || event.metaKey) return

        // Native modality makes the page inert. Wrap at the edge to keep Tab in the dialog.
        const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>(
          'button, input, textarea, select, a[href], [tabindex]'
        )).filter((control) => control.tabIndex >= 0 && !control.matches(':disabled') && control.getClientRects().length > 0)
        const first = controls[0]
        const last = controls[controls.length - 1]
        const edge = event.shiftKey ? first : last
        const next = event.shiftKey ? last : first
        if (event.target === edge && next) {
          event.preventDefault()
          next.focus()
        }
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 id={titleId} className="text-lg font-semibold text-slate-100">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 transition-colors p-1 rounded-lg hover:bg-slate-800"
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </dialog>,
    document.body
  )
}
