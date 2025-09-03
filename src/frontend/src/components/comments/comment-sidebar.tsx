import React, { useState, useEffect } from 'react';
import { MessageSquare, X, Plus, Trash2, Edit, Send, Users } from 'lucide-react';
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

const CommentSidebar: React.FC<CommentSidebarProps> = ({
  entityType,
  entityId,
  isOpen,
  onToggle,
  className,
}) => {
  const { get, post, put, delete: deleteApi, loading } = useApi();
  const { toast } = useToast();
  
  const [comments, setComments] = useState<Comment[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingComment, setEditingComment] = useState<Comment | null>(null);
  const [formData, setFormData] = useState<CommentFormData>({
    title: '',
    comment: '',
    audience: [],
  });

  // Available groups for audience selection (in a real app, fetch from API)
  const availableGroups = ['admin', 'data-producers', 'data-consumers', 'data-stewards'];

  const fetchComments = async () => {
    const response = await get<CommentListResponse>(
      `/api/entities/${entityType}/${entityId}/comments`
    );
    
    if (response.error) {
      toast({
        title: 'Error',
        description: `Failed to load comments: ${response.error}`,
        variant: 'destructive',
      });
      return;
    }
    
    setComments(response.data.comments || []);
    setTotalCount(response.data.total_count || 0);
    setVisibleCount(response.data.visible_count || 0);
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
    
    // Reset form and refresh comments
    setFormData({ title: '', comment: '', audience: [] });
    setEditingComment(null);
    setIsFormOpen(false);
    await fetchComments();
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
    
    await fetchComments();
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

  // Fetch comments when sidebar opens
  useEffect(() => {
    if (isOpen) {
      fetchComments();
    }
  }, [isOpen, entityType, entityId]);

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

  const CommentItem: React.FC<{ comment: Comment; canModify: boolean }> = ({ 
    comment, 
    canModify 
  }) => (
    <div className="p-3 border rounded-lg space-y-2">
      {comment.title && (
        <h4 className="font-medium text-sm">{comment.title}</h4>
      )}
      
      <p className="text-sm text-foreground whitespace-pre-wrap">
        {comment.comment}
      </p>
      
      {comment.audience && comment.audience.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {comment.audience.map(group => (
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
              {comment.created_by.charAt(0).toUpperCase()}
            </div>
          </Avatar>
          <span>{comment.created_by}</span>
          <RelativeDate date={comment.created_at} />
          {comment.updated_at !== comment.created_at && (
            <span className="italic">(edited)</span>
          )}
        </div>
        
        {canModify && (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => handleEdit(comment)}
            >
              <Edit className="w-3 h-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
              onClick={() => handleDelete(comment.id)}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <Sheet open={isOpen} onOpenChange={onToggle}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className={cn("relative", className)}>
          <MessageSquare className="w-4 h-4 mr-1" />
          Comments
          {visibleCount > 0 && (
            <Badge variant="secondary" className="ml-2 h-5 px-1 text-xs">
              {visibleCount}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      
      <SheetContent side="right" className="w-full sm:max-w-lg flex flex-col h-full p-0">
        <SheetHeader className="p-4 pb-2">
          <SheetTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Comments
            {totalCount > 0 && (
              <Badge variant="secondary" className="h-5 px-2 text-xs">
                {visibleCount}/{totalCount}
              </Badge>
            )}
          </SheetTitle>
          {totalCount !== visibleCount && (
            <p className="text-sm text-muted-foreground">
              Showing {visibleCount} of {totalCount} comments based on your permissions
            </p>
          )}
        </SheetHeader>
        
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
            {comments.length > 0 ? (
              <div className="p-4 space-y-3">
                {comments.map(comment => (
                  <CommentItem
                    key={comment.id}
                    comment={comment}
                    canModify={true} // TODO: Check actual permissions
                  />
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-muted-foreground">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No comments yet</p>
                <p className="text-xs">Be the first to add a comment!</p>
              </div>
            )}
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CommentSidebar;