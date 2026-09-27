import { formatDate, shiftDate } from '../utils'
import { ChevronLeft, ChevronRight } from './Icons'

export default function DateNav({ value, onChange }: { value: string; onChange: (d: string) => void }) {
  return (
    <div className="date-nav">
      <button
        type="button"
        className="btn btn-ghost btn-icon"
        onClick={() => onChange(shiftDate(value, -1))}
        aria-label="Previous day"
      >
        <ChevronLeft />
      </button>
      <strong>{formatDate(value)}</strong>
      <button
        type="button"
        className="btn btn-ghost btn-icon"
        onClick={() => onChange(shiftDate(value, 1))}
        aria-label="Next day"
      >
        <ChevronRight />
      </button>
    </div>
  )
}
