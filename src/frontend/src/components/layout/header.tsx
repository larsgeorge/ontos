import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import UserInfo from '@/components/ui/user-info';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { PanelLeftClose, PanelLeftOpen, BookOpenCheck } from 'lucide-react';
import NotificationBell from '@/components/ui/notification-bell';
import SearchBar from '@/components/ui/search-bar';
import { ProjectChooser } from '@/components/ui/project-chooser';
import { LanguageSelector } from '@/components/common/language-selector';
import { useNavigate } from 'react-router-dom';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface HeaderProps {
  onToggleSidebar: () => void;
  isSidebarCollapsed: boolean;
}

export function Header({ onToggleSidebar, isSidebarCollapsed }: HeaderProps) {
  const { t } = useTranslation('common');
  const navigate = useNavigate();
  
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-sidebar/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-sidebar/60">
       {/* Sidebar Toggle Button */}
        <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="shrink-0" 
        >
             {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            <span className="sr-only">{t('header.toggleSidebar')}</span>
         </Button>

      {/* Global Search Bar Container - Centered and Wider */}
      <div className="mx-auto max-w-2xl w-full">
        <SearchBar placeholder={t('header.searchPlaceholder')} />
      </div>

      {/* Right-aligned items */}
      <div className="ml-auto flex items-center gap-2 shrink-0">
          <ProjectChooser />
          <NotificationBell />
          <LanguageSelector />
         <ThemeToggle />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => navigate('/user-guide')}
              >
                <BookOpenCheck className="h-5 w-5" />
                <span className="sr-only">{t('header.userGuide')}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('header.userGuide')}</TooltipContent>
          </Tooltip>
        <UserInfo />
      </div>
    </header>
  );
}