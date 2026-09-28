import type { Metadata } from 'next';
import { DM_Serif_Display, Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/components/auth-provider';
import { ThemeProvider } from '@/components/theme-provider';
import { ToastProvider } from '@/components/toast-provider';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
});

const dmSerif = DM_Serif_Display({
  subsets: ['latin'],
  display: 'swap',
  weight: '400',
  variable: '--font-serif',
});

export const metadata: Metadata = {
  title: { default: 'LegalEase — Legal work, made clearer', template: '%s | LegalEase' },
  description: 'AI-assisted legal document drafting, review, and general legal information for modern teams.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${dmSerif.variable}`} suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            {children}
            <ToastProvider />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
