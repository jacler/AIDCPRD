export function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 200 140"
      className="h-full w-full"
      aria-hidden
      fill="none"
    >
      <defs>
        <linearGradient id="rackGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="hsl(221 83% 60%)" />
          <stop offset="100%" stopColor="hsl(221 83% 45%)" />
        </linearGradient>
        <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="hsl(221 83% 53% / 0.15)" />
          <stop offset="100%" stopColor="hsl(214 32% 91% / 0.5)" />
        </linearGradient>
      </defs>

      <ellipse cx="100" cy="128" rx="72" ry="8" fill="hsl(221 83% 53% / 0.08)" />

      {/* Rack 1 */}
      <g transform="translate(28, 24)">
        <path
          d="M0 80 L20 70 L20 10 L0 20 Z"
          fill="url(#rackGrad)"
          opacity="0.85"
        />
        <path
          d="M20 10 L60 10 L60 70 L20 70 Z"
          fill="hsl(221 83% 97%)"
          stroke="hsl(221 83% 75%)"
          strokeWidth="1"
        />
        <path
          d="M60 10 L80 20 L80 80 L60 70 Z"
          fill="url(#rackGrad)"
          opacity="0.6"
        />
        {[18, 32, 46, 60].map((y) => (
          <rect
            key={y}
            x="26"
            y={y}
            width="28"
            height="8"
            rx="1"
            fill="hsl(221 83% 53% / 0.2)"
          />
        ))}
      </g>

      {/* Rack 2 - center */}
      <g transform="translate(72, 12)">
        <path d="M0 90 L18 82 L18 8 L0 16 Z" fill="url(#rackGrad)" />
        <path
          d="M18 8 L56 8 L56 82 L18 82 Z"
          fill="hsl(0 0% 100%)"
          stroke="hsl(221 83% 70%)"
          strokeWidth="1.5"
        />
        <path d="M56 8 L74 16 L74 90 L56 82 Z" fill="url(#rackGrad)" opacity="0.7" />
        {[20, 34, 48, 62, 76].map((y) => (
          <rect
            key={y}
            x="24"
            y={y}
            width="26"
            height="7"
            rx="1"
            fill="hsl(142 71% 45% / 0.35)"
          />
        ))}
        <circle cx="37" cy="14" r="3" fill="hsl(142 71% 45%)" />
      </g>

      {/* Rack 3 */}
      <g transform="translate(118, 28)">
        <path d="M0 76 L16 68 L16 12 L0 20 Z" fill="url(#rackGrad)" opacity="0.75" />
        <path
          d="M16 12 L52 12 L52 68 L16 68 Z"
          fill="hsl(221 83% 97%)"
          stroke="hsl(221 83% 75%)"
          strokeWidth="1"
        />
        <path d="M52 12 L68 20 L68 76 L52 68 Z" fill="url(#rackGrad)" opacity="0.55" />
        {[22, 36, 50].map((y) => (
          <rect
            key={y}
            x="22"
            y={y}
            width="24"
            height="7"
            rx="1"
            fill="hsl(221 83% 53% / 0.25)"
          />
        ))}
      </g>

      {/* Network links */}
      <path
        d="M68 52 Q100 38 132 56"
        stroke="hsl(221 83% 53%)"
        strokeWidth="1.5"
        strokeDasharray="4 3"
        opacity="0.6"
      />
      <path
        d="M48 72 Q100 58 152 68"
        stroke="hsl(221 83% 53%)"
        strokeWidth="1"
        opacity="0.4"
      />
      <circle cx="68" cy="52" r="3" fill="hsl(221 83% 53%)" />
      <circle cx="132" cy="56" r="3" fill="hsl(142 71% 45%)" />
    </svg>
  );
}
