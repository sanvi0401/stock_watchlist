import { Modal } from './ui'
import { PRIVACY_POLICY, TERMS_OF_SERVICE } from '../legal'

export function LegalModal({
  kind,
  onClose,
}: {
  kind: 'terms' | 'privacy' | null
  onClose: () => void
}) {
  if (!kind) return null
  const title = kind === 'terms' ? 'Terms of Service' : 'Privacy Policy'
  const body = kind === 'terms' ? TERMS_OF_SERVICE : PRIVACY_POLICY
  return (
    <Modal open title={title} onClose={onClose} wide>
      <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1 text-sm leading-relaxed text-[#CBD5E1] whitespace-pre-wrap">
        {body}
      </div>
      <button
        type="button"
        className="mt-4 w-full rounded bg-intel px-4 py-2 text-sm font-medium text-white"
        onClick={onClose}
      >
        Close
      </button>
    </Modal>
  )
}
