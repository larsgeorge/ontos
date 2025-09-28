import React from 'react';
import { Badge } from '@/components/ui/badge';
import { X, Info } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// Type for rich tag object (matches backend AssignedTag)
export interface AssignedTag {
  tag_id: string;
  tag_name: string;
  namespace_id: string;
  namespace_name: string;
  status: 'active' | 'draft' | 'candidate' | 'deprecated' | 'inactive' | 'retired';
  fully_qualified_name: string;
  assigned_value?: string;
  assigned_by?: string;
  assigned_at: string;
}

export interface TagChipProps {
  /** Tag data - can be a simple string or rich AssignedTag object */
  tag: string | AssignedTag;
  /** Whether the tag can be removed */
  removable?: boolean;
  /** Callback when tag is removed */
  onRemove?: (tag: string | AssignedTag) => void;
  /** Additional CSS classes */
  className?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant based on tag status or custom */
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

const getVariantFromStatus = (status?: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
  switch (status) {
    case 'active':
      return 'default';
    case 'deprecated':
    case 'retired':
    case 'inactive':
      return 'destructive';
    case 'draft':
    case 'candidate':
      return 'secondary';
    default:
      return 'default';
  }
};

const getSizeClasses = (size: TagChipProps['size'] = 'md') => {
  switch (size) {
    case 'sm':
      return 'text-xs px-1.5 py-0.5';
    case 'lg':
      return 'text-base px-3 py-1.5';
    case 'md':
    default:
      return 'text-sm px-2 py-1';
  }
};

const TagChip: React.FC<TagChipProps> = ({
  tag,
  removable = false,
  onRemove,
  className,
  size = 'md',
  variant,
}) => {
  const isRichTag = typeof tag === 'object';
  const tagName = isRichTag ? tag.tag_name : tag;
  const displayName = isRichTag && tag.assigned_value ?
    `${tag.tag_name}: ${tag.assigned_value}` : tagName;

  // Determine variant based on tag status if not explicitly provided
  const effectiveVariant = variant || (isRichTag ? getVariantFromStatus(tag.status) : 'default');

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove?.(tag);
  };

  const chipContent = (
    <Badge
      variant={effectiveVariant}
      className={cn(
        'inline-flex items-center gap-1.5 font-medium',
        getSizeClasses(size),
        removable && 'pr-1',
        className
      )}
    >
      <span className="truncate">{displayName}</span>

      {isRichTag && (
        <Info className="h-3 w-3 text-muted-foreground flex-shrink-0" />
      )}

      {removable && (
        <button
          onClick={handleRemove}
          className="flex-shrink-0 rounded-full p-0.5 hover:bg-background/20 transition-colors"
          aria-label={`Remove ${tagName} tag`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </Badge>
  );

  // If it's a rich tag, wrap with tooltip to show metadata
  if (isRichTag) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {chipContent}
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <div className="space-y-1 text-sm">
              <div className="font-semibold">{tag.fully_qualified_name}</div>
              {tag.assigned_value && (
                <div><span className="font-medium">Value:</span> {tag.assigned_value}</div>
              )}
              <div><span className="font-medium">Status:</span> {tag.status}</div>
              <div><span className="font-medium">Namespace:</span> {tag.namespace_name}</div>
              {tag.assigned_by && (
                <div><span className="font-medium">Assigned by:</span> {tag.assigned_by}</div>
              )}
              <div><span className="font-medium">Assigned:</span> {new Date(tag.assigned_at).toLocaleDateString()}</div>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return chipContent;
};

export default TagChip;