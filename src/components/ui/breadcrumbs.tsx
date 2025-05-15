import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Home as HomeIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import useBreadcrumbStore, { BreadcrumbSegment } from '@/stores/breadcrumb-store';

interface BreadcrumbsProps extends React.HTMLAttributes<HTMLElement> {}

export function Breadcrumbs({ className, ...props }: BreadcrumbsProps) {
  const { staticSegments, dynamicTitle } = useBreadcrumbStore();

  return (
    <nav
      aria-label="breadcrumb"
      className={cn('mb-4 text-sm text-muted-foreground', className)}
      {...props}
    >
      <ol className="list-none p-0 inline-flex items-center space-x-1">
        {/* Home Icon Link */}
        <li>
          <Link to="/" className="flex items-center hover:text-primary">
            <HomeIcon className="h-4 w-4 mr-1.5" />
          </Link>
        </li>

        {/* Static Segments */}
        {staticSegments.map((segment, index) => (
          <React.Fragment key={segment.path || index}>
            <li className="flex items-center">
              <ChevronRight className="h-4 w-4" />
            </li>
            <li className={cn(segment.path ? "hover:text-primary" : "font-medium text-foreground")}>
              {segment.path ? (
                <Link to={segment.path}>{segment.label}</Link>
              ) : (
                <span>{segment.label}</span>
              )}
            </li>
          </React.Fragment>
        ))}

        {/* Dynamic Title (Last Segment) - only if static segments exist AND dynamic title is present OR if no static segments but dynamic title is present */}
        {(staticSegments.length > 0 && dynamicTitle) || (staticSegments.length === 0 && dynamicTitle) ? (
          <>
            <li className="flex items-center">
              <ChevronRight className="h-4 w-4" />
            </li>
            <li className="font-medium text-foreground">
              <span>{dynamicTitle}</span>
            </li>
          </>
        ) : null}
      </ol>
    </nav>
  );
} 