import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'Property Intelligence AI', description: 'A conversational property concierge for DarGlobal and Wasalt.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
