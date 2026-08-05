interface LogoProps {
  className?: string
  /** Render the filled rounded-square app-icon variant instead of the bare mark. */
  variant?: "mark" | "icon"
}

/**
 * The single PromptShield AI brand mark - a shield with an embedded checkmark,
 * rendered as inline SVG so it stays crisp at any size and can be recolored
 * via currentColor / gradient stops. Used across the sidebar, popup, landing
 * page, loading splash, and 404 page so the brand stays visually consistent.
 * The extension toolbar icons (16/48/128 PNG) are generated from this exact
 * geometry - see browser-extension/scripts/generate_icons.py.
 */
export function Logo({ className = "h-6 w-6", variant = "mark" }: LogoProps) {
  if (variant === "icon") {
    return (
      <svg viewBox="0 0 128 128" className={className} xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="ps-icon-bg" x1="0" y1="0" x2="128" y2="128" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#863bff" />
            <stop offset="100%" stopColor="#4c1adb" />
          </linearGradient>
        </defs>
        <rect width="128" height="128" rx="28" fill="url(#ps-icon-bg)" />
        <path
          d="M64 24 L94 34 V60 C94 82 82 97 64 106 C46 97 34 82 34 60 V34 Z"
          fill="white"
          fillOpacity="0.96"
        />
        <path
          d="M50 63 L59 73 L80 49"
          fill="none"
          stroke="#7e14ff"
          strokeWidth="7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 48 48" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="ps-mark-grad" x1="6" y1="4" x2="42" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#a259ff" />
          <stop offset="55%" stopColor="#7e14ff" />
          <stop offset="100%" stopColor="#47bfff" />
        </linearGradient>
      </defs>
      <path
        d="M24 4 L40 10 V22 C40 33 33.5 41 24 45 C14.5 41 8 33 8 22 V10 Z"
        fill="url(#ps-mark-grad)"
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
