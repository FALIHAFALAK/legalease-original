'use client';

import { Toaster } from 'sonner';

export function ToastProvider() {
  return (
    // Sonner's own <=600px rule sets `left: 16px; right: 16px; width: 100%`, which over-constrains
    // the fixed toaster and pushes it past the right edge of a phone viewport. Capping the width
    // inline (inline styles outrank that media query) keeps it inside the viewport at every size.
    <Toaster
      position="top-right"
      richColors
      closeButton
      style={{ width: 'min(356px, calc(100% - 2rem))' }}
    />
  );
}
