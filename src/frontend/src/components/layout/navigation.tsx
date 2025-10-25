import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getNavigationGroups, FeatureConfig } from '@/config/features';
import React from 'react';
import { useTranslation } from 'react-i18next';
// Import the Zustand store hook
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';
import { Button } from '@/components/ui/button';
// Import permissions hook and types
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
// Add Home icon
import { Home as HomeIcon, Loader2 } from 'lucide-react';

interface NavigationProps {
  isCollapsed: boolean;
}

export function Navigation({ isCollapsed }: NavigationProps) {
  const { t } = useTranslation(['navigation', 'features']);
  const location = useLocation();
  // Select only the allowedMaturities from the store
  const allowedMaturities = useFeatureVisibilityStore((state) => state.allowedMaturities);
  // Get permissions state and checker
  const { permissions, isLoading: permissionsLoading, hasPermission } = usePermissions();

  // Get navigation groups based on maturity filters
  const rawNavigationGroups = getNavigationGroups(allowedMaturities);

  // IDs of features to show ungrouped after Home
  const ungroupedFeatureIds = ['data-domains', 'teams', 'projects'];

  // Filter groups and items based on permissions (only run when permissions are loaded)
  const { navigationGroups, ungroupedItems } = React.useMemo(() => {
    if (permissionsLoading || Object.keys(permissions).length === 0) {
      // Return empty or skeleton while loading/empty to prevent flashing
      return { navigationGroups: [], ungroupedItems: [] };
    }

    // Extract ungrouped items from the raw navigation groups
    const extractedUngroupedItems: FeatureConfig[] = [];
    
    const filteredGroups = rawNavigationGroups
      .map(group => ({
        ...group,
        // Filter items within the group
        items: group.items.filter(item => {
          const hasAccess = item.id === 'about' || hasPermission(item.id, FeatureAccessLevel.READ_ONLY);
          
          // If this item should be ungrouped and has access, add it to ungroupedItems
          if (ungroupedFeatureIds.includes(item.id) && hasAccess) {
            extractedUngroupedItems.push(item);
            return false; // Remove from group
          }
          
          return hasAccess;
        })
      }))
      .filter(group => group.items.length > 0); // Remove groups that become empty after filtering

    return { 
      navigationGroups: filteredGroups, 
      ungroupedItems: extractedUngroupedItems 
    };
  }, [rawNavigationGroups, permissions, permissionsLoading, hasPermission]);

  // Handle loading state for permissions
  if (permissionsLoading) {
     // Show a loading indicator instead of an empty sidebar
     return (
         <div className="flex justify-center items-center h-full p-4">
             <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
         </div>
     );
  }

  // Define the Home link separately
  const homeLink: FeatureConfig = {
    id: 'home',
    name: t('navigation:home'),
    path: '/',
    description: 'Dashboard overview', // Optional description
    icon: HomeIcon, // Use imported HomeIcon
    group: 'System', // Assign to a group, or handle separately
    maturity: 'ga', // Treat as GA
  };

  // Map group names to i18n keys
  const groupKeyMap: Record<string, string> = {
    'Data Products': 'dataProducts',
    'Governance': 'governance',
    'Operations': 'operations',
    'Security': 'security',
    'System': 'system',
  };

  const translateGroupName = (groupName: string) => {
    const key = groupKeyMap[groupName] || groupName;
    return t(`navigation:groups.${key}`, { defaultValue: groupName });
  };

  const translateFeatureName = (featureId: string, defaultName: string) => {
    return t(`features:${featureId}.name`, { defaultValue: defaultName });
  };

  return (
    <ScrollArea className="h-full py-2">
      <TooltipProvider delayDuration={0}>
        <nav className={cn("flex flex-col px-1 gap-1")}>
          {/* Render Home Link First */}
          {
            isCollapsed ? (
                  <Tooltip key={homeLink.path}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                          'flex items-center justify-center rounded-lg p-2 transition-colors',
                          location.pathname === homeLink.path
                            ? 'bg-muted text-primary'
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        )}
                        aria-label={homeLink.name}
                        asChild
                      >
                        <NavLink to={homeLink.path}>
                          <homeLink.icon className="h-5 w-5" />
                          <span className="sr-only">{homeLink.name}</span>
                        </NavLink>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="flex items-center gap-4">
                      {homeLink.name}
                    </TooltipContent>
                  </Tooltip>
            ) : (
                  <NavLink
                    key={homeLink.path}
                    to={homeLink.path}
                    className={({ isActive: navIsActive }) =>
                      cn(
                        'flex items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                        navIsActive
                          ? 'bg-muted text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )
                    }
                  >
                    <homeLink.icon className="h-5 w-5 shrink-0" />
                    <span className="flex-1 min-w-0 truncate">{homeLink.name}</span>
                  </NavLink>
            )
          }
          {/* Render Ungrouped Items (Domains, Teams, Projects) */}
          {ungroupedItems.map((item: FeatureConfig) => {
            const isActive = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);
            const translatedName = translateFeatureName(item.id, item.name);

            return isCollapsed ? (
              <Tooltip key={item.path}>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      'flex items-center justify-center rounded-lg p-2 transition-colors',
                      isActive
                        ? 'bg-muted text-primary'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                    aria-label={translatedName}
                    asChild
                  >
                    <NavLink to={item.path}>
                      <item.icon className="h-5 w-5" />
                      <span className="sr-only">{translatedName}</span>
                    </NavLink>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {translatedName}
                  {item.maturity !== 'ga' && (
                    <sup className={cn(
                      "ml-1 text-[10px] font-bold px-1 py-0.5 rounded whitespace-nowrap",
                      item.maturity === 'beta' ? "bg-yellow-500/20 text-yellow-700 dark:bg-yellow-500/30 dark:text-yellow-400" : "",
                      item.maturity === 'alpha' ? "bg-purple-500/20 text-purple-700 dark:bg-purple-500/30 dark:text-purple-400" : ""
                    )}>
                      {item.maturity === 'beta' ? 'β' : 'α'}
                    </sup>
                  )}
                </TooltipContent>
              </Tooltip>
            ) : (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive: navIsActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                    navIsActive
                      ? 'bg-muted text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                <item.icon className="h-5 w-5 shrink-0" />
                <span className="flex-1 min-w-0 truncate">
                  {translatedName}
                  {item.maturity !== 'ga' && (
                    <sup className={cn(
                      "ml-1 text-[10px] font-bold px-1 py-0.5 rounded whitespace-nowrap",
                      item.maturity === 'beta' ? "bg-yellow-500/20 text-yellow-700 dark:bg-yellow-500/30 dark:text-yellow-400" : "",
                      item.maturity === 'alpha' ? "bg-purple-500/20 text-purple-700 dark:bg-purple-500/30 dark:text-purple-400" : ""
                    )}>
                      {item.maturity === 'beta' ? 'β' : 'α'}
                    </sup>
                  )}
                </span>
              </NavLink>
            );
          })}
          {/* Render Other Groups */}
          {navigationGroups.map((group) => (
            <div key={group.name} className={cn("w-full", isCollapsed ? "" : "mb-2 last:mb-0")}>
              {!isCollapsed && group.items.length > 0 && (
                <h2 className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {translateGroupName(group.name)}
                </h2>
              )}
              {group.items.map((item: FeatureConfig) => {
                const isActive = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);
                const translatedName = translateFeatureName(item.id, item.name);

                return isCollapsed ? (
                  <Tooltip key={item.path}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                          'flex items-center justify-center rounded-lg p-2 transition-colors',
                          isActive
                            ? 'bg-muted text-primary'
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        )}
                        aria-label={translatedName}
                        asChild
                      >
                        <NavLink to={item.path}>
                          <item.icon className="h-5 w-5" />
                          <span className="sr-only">{translatedName}</span>
                        </NavLink>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      {translatedName}
                      {item.maturity !== 'ga' && (
                        <sup className={cn(
                          "ml-1 text-[10px] font-bold px-1 py-0.5 rounded whitespace-nowrap",
                          item.maturity === 'beta' ? "bg-yellow-500/20 text-yellow-700 dark:bg-yellow-500/30 dark:text-yellow-400" : "",
                          item.maturity === 'alpha' ? "bg-purple-500/20 text-purple-700 dark:bg-purple-500/30 dark:text-purple-400" : ""
                        )}>
                          {item.maturity === 'beta' ? 'β' : 'α'}
                        </sup>
                      )}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive: navIsActive }) =>
                      cn(
                        'flex items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                        navIsActive
                          ? 'bg-muted text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )
                    }
                  >
                    <item.icon className="h-5 w-5 shrink-0" />
                    <span className="flex-1 min-w-0 truncate">
                      {translatedName}
                      {item.maturity !== 'ga' && (
                        <sup className={cn(
                          "ml-1 text-[10px] font-bold px-1 py-0.5 rounded whitespace-nowrap",
                          item.maturity === 'beta' ? "bg-yellow-500/20 text-yellow-700 dark:bg-yellow-500/30 dark:text-yellow-400" : "",
                          item.maturity === 'alpha' ? "bg-purple-500/20 text-purple-700 dark:bg-purple-500/30 dark:text-purple-400" : ""
                        )}>
                          {item.maturity === 'beta' ? 'β' : 'α'}
                        </sup>
                      )}
                    </span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
      </TooltipProvider>
    </ScrollArea>
  );
}