import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home as HomeIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getFeatureNameByPath } from '@/config/features'; // Import the helper
import useBreadcrumbStore from '@/stores/breadcrumb-store'; // <-- Import store

interface BreadcrumbsProps extends React.HTMLAttributes<HTMLElement> {}

export function Breadcrumbs({ className, ...props }: BreadcrumbsProps) {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);
  const dynamicTitle = useBreadcrumbStore((state) => state.dynamicTitle); // <-- Get dynamic title

  // Temporary mapping - ideally sourced from a shared config
  // const pathMap: { [key: string]: string } = {
  //   'data-products': 'Data Products',
  //   'data-contracts': 'Data Contracts',
  //   'business-glossary': 'Business Glossary',
  //   'master-data': 'Master Data Management',
  //   'compliance': 'Compliance',
  //   'estate-manager': 'Estate Manager',
  //   'security': 'Security Features',
  //   'entitlements': 'Entitlements',
  //   'entitlements-sync': 'Entitlements Sync',
  //   'catalog-commander': 'Catalog Commander',
  //   'settings': 'Settings',
  //   'about': 'About',
  // };

  // Function to get display name (using the new helper)
  const getDisplayName = (pathSegment: string): string => {
      // Use the helper function from features config
      return getFeatureNameByPath(pathSegment);
  };


  return (
    <nav
      aria-label="breadcrumb"
      className={cn('mb-4 text-sm text-muted-foreground', className)}
      {...props}
    >
      <ol className="list-none p-0 inline-flex items-center space-x-1">
        <li>
          <Link to="/" className="flex items-center hover:text-primary">
            <HomeIcon className="h-4 w-4 mr-1.5" />
          </Link>
        </li>
        {pathnames.length > 0 && (
          <li>
            <ChevronRight className="h-4 w-4" />
          </li>
        )}
        {pathnames.map((value, index) => {
          const to = `/${pathnames.slice(0, index + 1).join('/')}`;
          const isLast = index === pathnames.length - 1;
          const displayName = getDisplayName(value);
          // Use dynamic title if it's the last segment and dynamic title exists
          const finalDisplayName = isLast && dynamicTitle ? dynamicTitle : displayName;

          return (
            <React.Fragment key={to}>
              <li>
                {isLast ? (
                  <span className="font-medium text-foreground">{finalDisplayName}</span>
                ) : (
                  <Link to={to} className="hover:text-primary">
                    {finalDisplayName}
                  </Link>
                )}
              </li>
              {!isLast && (
                <li>
                  <ChevronRight className="h-4 w-4" />
                </li>
              )}
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
} 