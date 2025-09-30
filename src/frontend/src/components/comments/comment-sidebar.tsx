import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare, X, Plus, Trash2, Edit, Send, Users, Filter, Clock, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import {
  Comment,
  CommentCreate,
  CommentUpdate,
  CommentListResponse,
  CommentSidebarProps,
} from '@/types/comments';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/ui/avatar';
import { RelativeDate } from '@/components/common/relative-date';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CommentFormData {
  title: string;
  comment: string;
  audience: string[];
}

interface TimelineEntry {
  id: string;
  type: 'comment' | 'change';
  entity_type: string;
  entity_id: string;
  title?: string;
  content: string;
  username: string;
  timestamp: string;
  updated_at?: string;
  audience?: string[];
  status?: string;
  metadata?: {
    updated_by?: string;
    action?: string;
  };
}

interface TimelineResponse {
  timeline: TimelineEntry[];
  total_count: number;
  filter_type: string;
}

const CommentSidebar: React.FC<CommentSidebarProps> = ({
  entityType,
  entityId,
  isOpen,
  onToggle,
  className,
  fetchCountOnMount = true,
}) => {
  const { get, post, put, delete: deleteApi, loading } = useApi();
  const { toast } = useToast();
  
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [filterType, setFilterType] = useState<'all' | 'comments' | 'changes'>('all');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingComment, setEditingComment] = useState<Comment | null>(null);
  const [formData, setFormData] = useState<CommentFormData>({
    title: '',
    comment: '',
    audience: [],
  });

  // Available groups for audience selection (in a real app, fetch from API)
  const availableGroups = ['admin', 'data-producers', 'data-consumers', 'data-stewards'];

  const fetchCommentCount = useCallback(async () => {
    if (!entityType || !entityId) {
      console.debug('CommentSidebar: Skipping count fetch - missing entityType or entityId');
      return;
    }

    console.debug(`CommentSidebar: Fetching count for ${entityType}/${entityId}`);

    const response = await get<TimelineResponse>(
      `/api/entities/${entityType}/${entityId}/timeline/count?filter_type=all`
    );

    if (response.error) {
      console.warn(`CommentSidebar: Failed to load comment count for ${entityType}/${entityId}:`, response.error);
      return;
    }

    const count = response.data?.total_count || 0;
    console.debug(`CommentSidebar: Setting count to ${count} for ${entityType}/${entityId}`);
    setTotalCount(count);
  }, [entityType, entityId, get]);

  const fetchTimeline = async () => {
    const response = await get<TimelineResponse>(
      `/api/entities/${entityType}/${entityId}/timeline?filter_type=${filterType}`
    );
    
    if (response.error) {
      toast({
        title: 'Error',
        description: `Failed to load timeline: ${response.error}`,
        variant: 'destructive',
      });
      return;
    }
    
    setTimeline(response.data.timeline || []);
    setTotalCount(response.data.total_count || 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.comment.trim()) {
      toast({
        title: 'Error',
        description: 'Comment content is required',
        variant: 'destructive',
      });
      return;
    }

    const commentData: CommentCreate | CommentUpdate = {
      title: formData.title || null,
      comment: formData.comment,
      audience: formData.audience.length > 0 ? formData.audience : null,
    };

    if (editingComment) {
      // Update existing comment
      const response = await put<Comment>(
        `/api/comments/${editingComment.id}`,
        commentData
      );
      
      if (response.error) {
        toast({
          title: 'Error',
          description: `Failed to update comment: ${response.error}`,
          variant: 'destructive',
        });
        return;
      }
      
      toast({
        title: 'Success',
        description: 'Comment updated successfully',
      });
    } else {
      // Create new comment
      const createData: CommentCreate = {
        entity_id: entityId,
        entity_type: entityType,
        ...commentData,
      };
      
      const response = await post<Comment>(
        `/api/entities/${entityType}/${entityId}/comments`,
        createData
      );
      
      if (response.error) {
        toast({
          title: 'Error',
          description: `Failed to create comment: ${response.error}`,
          variant: 'destructive',
        });
        return;
      }
      
      toast({
        title: 'Success',
        description: 'Comment created successfully',
      });
    }
    
    // Reset form and refresh timeline
    setFormData({ title: '', comment: '', audience: [] });
    setEditingComment(null);
    setIsFormOpen(false);
    await fetchTimeline();

    // Update count if we're fetching it on mount (to keep button in sync)
    if (fetchCountOnMount) {
      await fetchCommentCount();
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm('Are you sure you want to delete this comment?')) {
      return;
    }
    
    const response = await deleteApi(`/api/comments/${commentId}`);
    
    if (response.error) {
      toast({
        title: 'Error',
        description: `Failed to delete comment: ${response.error}`,
        variant: 'destructive',
      });
      return;
    }
    
    toast({
      title: 'Success',
      description: 'Comment deleted successfully',
    });

    await fetchTimeline();

    // Update count if we're fetching it on mount (to keep button in sync)
    if (fetchCountOnMount) {
      await fetchCommentCount();
    }
  };

  const handleEdit = (comment: Comment) => {
    setEditingComment(comment);
    setFormData({
      title: comment.title || '',
      comment: comment.comment,
      audience: comment.audience || [],
    });
    setIsFormOpen(true);
  };

  const resetForm = () => {
    setFormData({ title: '', comment: '', audience: [] });
    setEditingComment(null);
    setIsFormOpen(false);
  };

  // Fetch comment count on mount if requested
  useEffect(() => {
    if (fetchCountOnMount) {
      fetchCommentCount();
    }
  }, [fetchCountOnMount, fetchCommentCount]);

  // Fetch timeline when sidebar opens or filter changes
  useEffect(() => {
    if (isOpen) {
      fetchTimeline();
    }
  }, [isOpen, entityType, entityId, filterType]);

  const CommentForm = React.useMemo(() => (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 border-t">
      <div>
        <Label htmlFor="title">Title (Optional)</Label>
        <Input
          id="title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          placeholder="Add a title for this comment..."
          className="mt-1"
        />
      </div>
      
      <div>
        <Label htmlFor="comment">Comment</Label>
        <Textarea
          id="comment"
          value={formData.comment}
          onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
          placeholder="Write your comment..."
          className="mt-1"
          rows={3}
          required
        />
      </div>
      
      <div>
        <Label>Visible to Groups (Optional)</Label>
        <div className="mt-2 space-y-2">
          <div className="text-xs text-muted-foreground">
            Leave all unchecked for visibility to all users
          </div>
          {availableGroups.map(group => (
            <div key={group} className="flex items-center space-x-2">
              <input
                type="checkbox"
                id={`group-${group}`}
                checked={formData.audience.includes(group)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData({ 
                      ...formData, 
                      audience: [...formData.audience, group] 
                    });
                  } else {
                    setFormData({ 
                      ...formData, 
                      audience: formData.audience.filter(g => g !== group) 
                    });
                  }
                }}
                className="rounded"
              />
              <Label htmlFor={`group-${group}`} className="text-sm font-normal">
                {group}
              </Label>
            </div>
          ))}
        </div>
        {formData.audience.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {formData.audience.map(group => (
              <Badge key={group} variant="secondary" className="text-xs">
                <Users className="w-3 h-3 mr-1" />
                {group}
              </Badge>
            ))}
          </div>
        )}
      </div>
      
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={loading}>
          <Send className="w-4 h-4 mr-1" />
          {editingComment ? 'Update' : 'Post'}
        </Button>
        {(editingComment || formData.title || formData.comment) && (
          <Button type="button" variant="outline" size="sm" onClick={resetForm}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  ), [formData, editingComment, loading, availableGroups, handleSubmit, resetForm]);

  const TimelineItem: React.FC<{ entry: TimelineEntry; canModify: boolean }> = ({ 
    entry, 
    canModify 
  }) => {
    const parsed = React.useMemo(() => {
      if (entry.type !== 'change') return null;
      try {
        const trimmed = (entry.content || '').trim();
        if (!trimmed || (trimmed[0] !== '{' && trimmed[0] !== '[')) return null;
        return JSON.parse(trimmed);
      } catch {
        return null;
      }
    }, [entry]);

    const renderParsedObject = (obj: any) => {
      // Special formatting for access_request_* actions
      const action = entry.metadata?.action || '';
      if (action.startsWith('access_request_')) {
        return (
          <div className="text-sm space-y-1">
            {obj.requester_email && (
              <div><span className="text-muted-foreground">Requester:</span> {obj.requester_email}</div>
            )}
            {obj.decision && (
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Decision:</span>
                <Badge variant={obj.decision === 'approve' ? 'secondary' : obj.decision === 'deny' ? 'destructive' : 'outline'} className="text-xs">
                  {String(obj.decision)}
                </Badge>
              </div>
            )}
            {obj.message && (
              <div><span className="text-muted-foreground">Message:</span> {String(obj.message)}</div>
            )}
          </div>
        );
      }
      
      // Special formatting for semantic link changes
      if (action.startsWith('SEMANTIC_LINK_')) {
        const operation = action === 'SEMANTIC_LINK_ADD'
          ? 'linked'
          : action === 'SEMANTIC_LINK_REMOVE'
          ? 'unlinked'
          : action.toLowerCase();
        const iri = typeof obj?.iri === 'string' ? obj.iri : undefined;
        const linkId = typeof obj?.link_id === 'string' ? obj.link_id : undefined;
        return (
          <div className="text-sm space-y-1">
            {iri && (
              <div><span className="text-muted-foreground">Iri:</span> {iri}</div>
            )}
            {linkId && (
              <div><span className="text-muted-foreground">Link Id:</span> {linkId}</div>
            )}
            <div><span className="text-muted-foreground">Operation:</span> {operation}</div>
          </div>
        );
      }
      // Generic key/value renderer
      return (
        <div className="text-sm space-y-1">
          {Object.entries(obj).map(([k, v]) => (
            <div key={k} className="flex gap-1">
              <span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}:</span>
              <span>{typeof v === 'string' ? v : JSON.stringify(v)}</span>
            </div>
          ))}
        </div>
      );
    };

    return (
      <div className={cn(
        "p-3 border rounded-lg space-y-2",
        entry.type === 'change' && "border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20"
      )}>
        <div className="flex items-center gap-2">
          {entry.type === 'comment' ? (
            <MessageSquare className="w-4 h-4 text-muted-foreground" />
          ) : (
            <Clock className="w-4 h-4 text-blue-600" />
          )}
          {entry.title && (
            <h4 className="font-medium text-sm">{entry.title}</h4>
          )}
          <Badge variant={entry.type === 'change' ? 'secondary' : 'outline'} className="text-xs">
            {entry.type}
          </Badge>
        </div>

        {parsed ? (
          renderParsedObject(parsed)
        ) : (
          <p className="text-sm text-foreground whitespace-pre-wrap">
            {entry.content}
          </p>
        )}

        {entry.audience && entry.audience.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {entry.audience.map(group => (
              <Badge key={group} variant="outline" className="text-xs">
                <Users className="w-3 h-3 mr-1" />
                {group}
              </Badge>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Avatar className="w-5 h-5">
              <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                {entry.username.charAt(0).toUpperCase()}
              </div>
            </Avatar>
            <span>{entry.username}</span>
            <RelativeDate date={new Date(entry.timestamp)} />
            {entry.updated_at && (
              <span className="italic">(edited)</span>
            )}
          </div>

          {canModify && entry.type === 'comment' && (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => handleEdit(entry as any)}
              >
                <Edit className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                onClick={() => handleDelete(entry.id)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Sheet open={isOpen} onOpenChange={onToggle}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className={cn("relative", className)}>
          <MessageSquare className="w-4 h-4 mr-1" />
          Comments
          {totalCount > 0 && (
            <Badge variant="secondary" className="ml-2 h-5 px-1 text-xs">
              {totalCount}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      
      <SheetContent side="right" className="w-full sm:max-w-lg flex flex-col h-full p-0">
        <SheetHeader className="p-4 pb-2">
          <SheetTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Activity Timeline
            {totalCount > 0 && (
              <Badge variant="secondary" className="h-5 px-2 text-xs">
                {totalCount}
              </Badge>
            )}
          </SheetTitle>
        </SheetHeader>
        
        {/* Filter Toolbar */}
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground">Filter:</span>
          </div>
          <div className="flex gap-2">
            <Button
              variant={filterType === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterType('all')}
              className="flex-1"
            >
              <FileText className="w-3 h-3 mr-1" />
              All
            </Button>
            <Button
              variant={filterType === 'comments' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterType('comments')}
              className="flex-1"
            >
              <MessageSquare className="w-3 h-3 mr-1" />
              Comments
            </Button>
            <Button
              variant={filterType === 'changes' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterType('changes')}
              className="flex-1"
            >
              <Clock className="w-3 h-3 mr-1" />
              Changes
            </Button>
          </div>
        </div>
        
        <div className="flex-1 flex flex-col">
          <div className="p-4 pt-0">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setIsFormOpen(!isFormOpen)}
              className="w-full"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Comment
            </Button>
          </div>
          
          {isFormOpen && CommentForm}
          
          <Separator />
          
          <ScrollArea className="flex-1">
            {timeline.length > 0 ? (
              <div className="p-4 space-y-3">
                {timeline.map(entry => (
                  <TimelineItem
                    key={entry.id}
                    entry={entry}
                    canModify={true} // TODO: Check actual permissions
                  />
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-muted-foreground">
                {filterType === 'comments' ? (
                  <>
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No comments yet</p>
                    <p className="text-xs">Be the first to add a comment!</p>
                  </>
                ) : filterType === 'changes' ? (
                  <>
                    <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No changes recorded</p>
                    <p className="text-xs">Changes will appear here when they occur</p>
                  </>
                ) : (
                  <>
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No activity yet</p>
                    <p className="text-xs">Comments and changes will appear here</p>
                  </>
                )}
              </div>
            )}
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CommentSidebar;