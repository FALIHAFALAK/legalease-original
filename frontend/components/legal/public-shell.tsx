import { SiteFooter } from '@/components/legal/site-footer';
import { SiteHeader } from '@/components/legal/site-header';

export function PublicShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen"><SiteHeader /><main>{children}</main><SiteFooter /></div>;
}
