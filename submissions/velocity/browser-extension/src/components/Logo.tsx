interface LogoProps {
  className?: string
}

/**
 * PromptShield AI brand mark, matching the admin-dashboard's Logo.tsx and
 * the generated extension toolbar icons (public/icons/icon*.png) so the
 * popup, dashboard, and browser toolbar all show the same shield mark.
 */
export function Logo({ className = "h-5 w-5" }: LogoProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="ps-mark-grad-ext" x1="6" y1="4" x2="42" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#a259ff" />
          <stop offset="55%" stopColor="#7e14ff" />
          <stop offset="100%" stopColor="#47bfff" />
        </linearGradient>
      </defs>
      <path
        d="M24 4 L40 10 V22 C40 33 33.5 41 24 45 C14.5 41 8 33 8 22 V10 Z"
        fill="url(#ps-mark-grad-ext)"
      />
      <path
        d="M17 23.5 L21.8 28.5 L31.5 17.5"
        fill="none"
        stroke="white"
        strokeWidth="3.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
