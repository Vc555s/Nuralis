import { Brain, Menu, Settings, Sun, Moon, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/stores/useAppStore';
import { useEffect, useState } from 'react';

export function AppHeader() {
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();
  const [theme, setTheme] = useState<'light' | 'dark' | 'pink'>('light');

  useEffect(() => {
    const stored = (localStorage.getItem('theme') as 'light' | 'dark' | 'pink' | null);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initial: 'light' | 'dark' | 'pink' = stored || (prefersDark ? 'dark' : 'light');
    setTheme(initial);
    document.documentElement.classList.toggle('dark', initial === 'dark');
    document.documentElement.classList.toggle('theme-pink', initial === 'pink');
  }, []);

  const cycleTheme = () => {
    const order: Array<'light' | 'dark' | 'pink'> = ['light', 'dark', 'pink'];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setTheme(next);
    document.documentElement.classList.toggle('dark', next === 'dark');
    document.documentElement.classList.toggle('theme-pink', next === 'pink');
    if (next !== 'dark') document.documentElement.classList.remove('dark');
    if (next !== 'pink') document.documentElement.classList.remove('theme-pink');
    localStorage.setItem('theme', next);
  };

  return (
    <header className="h-16 border-b border-border bg-background/95 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-50">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="hover:bg-muted transition-colors"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-brand-secondary rounded-full border-2 border-background status-online"></div>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Nuralis Research Analyst</h1>
            <p className="text-sm text-foreground-secondary">Advanced Research Intelligence Platform</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="hover:bg-muted transition-colors" onClick={cycleTheme} aria-label="Cycle theme">
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : theme === 'pink' ? <Heart className="h-4 w-4 text-pink-500" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button variant="ghost" size="sm" className="hover:bg-muted transition-colors">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}