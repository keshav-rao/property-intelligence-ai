// Small inline icons (no icon library needed).
type P = { size?: number; className?: string };

export const SendIcon = ({ size = 20 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4.5 12 3 4.8a.8.8 0 0 1 1.1-.9l16 7.4a.8.8 0 0 1 0 1.4l-16 7.4a.8.8 0 0 1-1.1-.9L4.5 12Zm0 0H12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const CloseIcon = ({ size = 22 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
  </svg>
);

export const RestartIcon = ({ size = 19 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ChatIcon = ({ size = 26 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M5 18.5 3.5 21l.8-3.6A8.5 8.5 0 1 1 7.7 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="8.5" cy="12" r="1.1" fill="currentColor" /><circle cx="12" cy="12" r="1.1" fill="currentColor" /><circle cx="15.5" cy="12" r="1.1" fill="currentColor" />
  </svg>
);

export const ExternalIcon = ({ size = 13 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const PinIcon = ({ size = 12 }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" stroke="currentColor" strokeWidth="2" />
    <circle cx="12" cy="9.5" r="2.4" stroke="currentColor" strokeWidth="2" />
  </svg>
);

/** The assistant's avatar: a key over a stylised roofline, in navy, bronze and purple. */
export const ConciergeMark = ({ size = 30 }: P) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M8 22 24 9l16 13" stroke="#081C2A" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M13 21v16h22V21" stroke="#081C2A" strokeWidth="3.2" strokeLinejoin="round" />
    <circle cx="21" cy="29" r="4.2" stroke="#8A7650" strokeWidth="2.6" />
    <path d="M25 29h7m-3 0v3" stroke="#6F10A2" strokeWidth="2.6" strokeLinecap="round" />
  </svg>
);
