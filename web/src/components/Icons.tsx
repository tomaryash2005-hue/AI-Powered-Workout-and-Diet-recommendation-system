import type { ReactNode } from 'react'

const Svg = ({ children, className }: { children: ReactNode; className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    className={className}
  >
    {children}
  </svg>
)

export const PulseIcon = () => (
  <Svg>
    <path d="M3 12h4l2-5 4 10 2-5h6" />
  </Svg>
)

export const HomeIcon = () => (
  <Svg>
    <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />
  </Svg>
)

export const SaladIcon = () => (
  <Svg>
    <path d="M3 11h18a9 9 0 0 1-18 0Z" />
    <path d="M7 11c0-3 2-5 5-5M12 11c0-2.5 1.5-4 4-4.5M17 11a3 3 0 0 0-2-2.8" />
  </Svg>
)

export const DumbbellIcon = () => (
  <Svg>
    <path d="M6 7v10M3 9v6M18 7v10M21 9v6M6 12h12" />
  </Svg>
)

export const JournalIcon = () => (
  <Svg>
    <path d="M5 4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z" />
    <path d="M9 8h6M9 12h6M9 16h3" />
  </Svg>
)

export const ChartIcon = () => (
  <Svg>
    <path d="M4 20V4M4 20h16M8 16l4-5 3 3 5-6" />
  </Svg>
)

export const UserIcon = () => (
  <Svg>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0" />
  </Svg>
)

export const AlertIcon = () => (
  <Svg>
    <path d="M12 3 2 20h20z" />
    <path d="M12 10v4M12 17h.01" />
  </Svg>
)

export const ChevronLeft = () => (
  <Svg>
    <path d="m15 18-6-6 6-6" />
  </Svg>
)

export const ChevronRight = () => (
  <Svg>
    <path d="m9 18 6-6-6-6" />
  </Svg>
)

export const ChevronDown = ({ className }: { className?: string }) => (
  <Svg className={className}>
    <path d="m6 9 6 6 6-6" />
  </Svg>
)

export const TrashIcon = () => (
  <Svg>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
  </Svg>
)

export const PlusIcon = () => (
  <Svg>
    <path d="M12 5v14M5 12h14" />
  </Svg>
)

export const LogoutIcon = () => (
  <Svg>
    <path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H3" />
  </Svg>
)
