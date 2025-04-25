import { useState, useEffect } from 'react';
import { Bell, Info, AlertCircle, CheckCircle2, X, CheckSquare } from 'lucide-react';
import { Button } from './button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './dropdown-menu';
import { Badge } from './badge';
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip';
import { ScrollArea } from './scroll-area';
import ConfirmRoleRequestDialog from '@/components/settings/confirm-role-request-dialog';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  subtitle?: string;
  description?: string;
  created_at: string;
  read: boolean;
  can_delete: boolean;
  action_type?: string;
  action_payload?: Record<string, any>;
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [selectedNotificationPayload, setSelectedNotificationPayload] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await fetch('/api/notifications');
      if (!response.ok) throw new Error('Failed to fetch notifications');
      const data = await response.json();
      setNotifications(data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`/api/notifications/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete notification');
      setNotifications(notifications.filter(n => n.id !== id));
    } catch (error) {
      console.error('Error deleting notification:', error);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      const response = await fetch(`/api/notifications/${id}/read`, {
        method: 'PUT',
      });
      if (!response.ok) throw new Error('Failed to mark notification as read');
      const updatedNotification = await response.json();
      setNotifications(notifications.map(n => 
        n.id === id ? updatedNotification : n
      ));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const handleOpenConfirmDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedNotificationPayload(payload);
      setIsConfirmDialogOpen(true);
    } else {
      console.error("Cannot open confirmation dialog: payload is missing.");
    }
  };

  const handleDecisionMade = () => {
    fetchNotifications();
    setSelectedNotificationPayload(null);
    setIsConfirmDialogOpen(false);
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <>
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center p-0 text-[10px] leading-none"
                >
                  {unreadCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>Notifications</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-80">
        <ScrollArea className="h-[400px]">
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="flex items-start gap-2 p-2"
                onClick={() => !notification.read && handleMarkRead(notification.id)}
                onSelect={(e) => {
                  if (notification.action_type) {
                    e.preventDefault();
                  }
                }}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {getIcon(notification.type)}
                    <p className="text-sm font-medium">{notification.title}</p>
                  </div>
                  {notification.subtitle && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {notification.subtitle}
                    </p>
                  )}
                  {notification.description && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {notification.description}
                    </p>
                  )}
                  {notification.action_type === 'handle_role_request' && notification.action_payload && (
                    <Button
                      variant="default"
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenConfirmDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      Approve/Deny
                    </Button>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(notification.created_at).toLocaleString()}
                  </p>
                </div>
                {notification.can_delete && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(notification.id);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
                {!notification.read && (
                  <div className="h-2 w-2 rounded-full bg-primary absolute right-2 top-2" />
                )}
              </DropdownMenuItem>
            ))
          )}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
    {isConfirmDialogOpen && selectedNotificationPayload && (
      <ConfirmRoleRequestDialog
        isOpen={isConfirmDialogOpen}
        onOpenChange={setIsConfirmDialogOpen}
        requesterEmail={selectedNotificationPayload?.requester_email ?? 'Unknown User'}
        roleId={selectedNotificationPayload?.role_id ?? 'Unknown Role ID'}
        roleName={selectedNotificationPayload?.role_name ?? 'Unknown Role Name'}
        onDecisionMade={handleDecisionMade}
      />
    )}
    </>
  );
} 