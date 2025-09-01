import { Button } from '@/components/ui/button';
import UserInfo from '@/components/ui/user-info';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import NotificationBell from '@/components/ui/notification-bell';
import SearchBar from '@/components/ui/search-bar';

interface HeaderProps {
  onToggleSidebar: () => void;
  isSidebarCollapsed: boolean;
}

export function Header({ onToggleSidebar, isSidebarCollapsed }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
       {/* Sidebar Toggle Button */}
        <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="shrink-0" 
        >
             {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            <span className="sr-only">Toggle sidebar</span>
         </Button>

      {/* Global Search Bar Container - Centered and Wider */}
      <div className="mx-auto max-w-2xl w-full">
        <SearchBar placeholder="Search features, assets..." />
      </div>

      {/* Right-aligned items */}
      <div className="ml-auto flex items-center gap-2 shrink-0">
          <NotificationBell />
         <ThemeToggle />
        <UserInfo />
      </div>
    </header>
  );
}