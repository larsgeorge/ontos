import { useState, useEffect } from 'react';
import { Bell, Info, AlertCircle, CheckCircle2, X, CheckSquare, Loader2 } from 'lucide-react';
import { Button } from './button';
import { Progress } from './progress';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './dropdown-menu';
import { Badge } from './badge';
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip';
import { ScrollArea } from './scroll-area';
import ConfirmRoleRequestDialog from '@/components/settings/confirm-role-request-dialog';
import ConfirmAccessRequestDialog from '@/components/access/confirm-access-request-dialog';
import HandleStewardReviewDialog from '@/components/data-contracts/handle-steward-review-dialog';
import HandlePublishRequestDialog from '@/components/data-contracts/handle-publish-request-dialog';
import HandleDeployRequestDialog from '@/components/data-contracts/handle-deploy-request-dialog';
import { useNotificationsStore } from '@/stores/notifications-store';
import { NotificationType } from '@/types/notification';

export default function NotificationBell() {
  const {
    notifications,
    unreadCount,
    isLoading,
    error,
    fetchNotifications,
    markAsRead,
    deleteNotification
  } = useNotificationsStore();

  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [selectedNotificationPayload, setSelectedNotificationPayload] = useState<Record<string, any> | null>(null);
  const [isAccessDialogOpen, setIsAccessDialogOpen] = useState(false);
  const [selectedAccessPayload, setSelectedAccessPayload] = useState<Record<string, any> | null>(null);
  const [isReviewDialogOpen, setIsReviewDialogOpen] = useState(false);
  const [selectedReviewPayload, setSelectedReviewPayload] = useState<Record<string, any> | null>(null);
  const [isPublishDialogOpen, setIsPublishDialogOpen] = useState(false);
  const [selectedPublishPayload, setSelectedPublishPayload] = useState<Record<string, any> | null>(null);
  const [isDeployDialogOpen, setIsDeployDialogOpen] = useState(false);
  const [selectedDeployPayload, setSelectedDeployPayload] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleDelete = async (id: string) => {
    await deleteNotification(id);
  };

  const handleMarkRead = async (id: string) => {
    await markAsRead(id);
  };

  const handleOpenConfirmDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedNotificationPayload(payload);
      setIsConfirmDialogOpen(true);
    } else {
      console.error("Cannot open confirmation dialog: payload is missing.");
    }
  };

  const handleOpenAccessDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedAccessPayload(payload);
      setIsAccessDialogOpen(true);
    } else {
      console.error("Cannot open access request dialog: payload is missing.");
    }
  };

  const handleOpenReviewDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedReviewPayload(payload);
      setIsReviewDialogOpen(true);
    } else {
      console.error("Cannot open review dialog: payload is missing.");
    }
  };

  const handleOpenPublishDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedPublishPayload(payload);
      setIsPublishDialogOpen(true);
    } else {
      console.error("Cannot open publish dialog: payload is missing.");
    }
  };

  const handleOpenDeployDialog = (payload: Record<string, any> | undefined | null) => {
    if (payload) {
      setSelectedDeployPayload(payload);
      setIsDeployDialogOpen(true);
    } else {
      console.error("Cannot open deploy dialog: payload is missing.");
    }
  };

  const handleDecisionMade = () => {
    fetchNotifications();
    setSelectedNotificationPayload(null);
    setIsConfirmDialogOpen(false);
    setSelectedAccessPayload(null);
    setIsAccessDialogOpen(false);
    setSelectedReviewPayload(null);
    setIsReviewDialogOpen(false);
    setSelectedPublishPayload(null);
    setIsPublishDialogOpen(false);
    setSelectedDeployPayload(null);
    setIsDeployDialogOpen(false);
  };

  const getIcon = (type: NotificationType) => {
    switch (type) {
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'action_required':
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case 'job_progress':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  return (
    <>
    <DropdownMenu onOpenChange={(open) => { if (open) fetchNotifications() }}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Bell className="h-5 w-5" />
              )}
              {unreadCount > 0 && !isLoading && (
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
          {isLoading ? (
             <div className="p-4 text-center text-sm text-muted-foreground">
                Loading notifications...
             </div>
          ) : error ? (
             <div className="p-4 text-center text-sm text-red-600">
                Error: {error}
             </div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="flex items-start gap-2 p-2 cursor-pointer"
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
                  {(notification.description || notification.message) && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {notification.description || notification.message}
                    </p>
                  )}
                  {/* Render link button if present */}
                  {notification.link && (
                    <a 
                      href={notification.link}
                      target="_blank" 
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()} // Prevent marking as read when clicking link
                      className="mt-2 inline-block" // Added inline-block for button alignment
                    >
                      <Button 
                        variant="outline" 
                        size="sm" // Changed to small size
                        className="h-7 px-2 text-xs" // Use text-xs for smaller font, adjust height/padding
                      >
                         Open
                      </Button>
                    </a>
                  )}
                  {notification.action_type === 'handle_role_request' && notification.action_payload && (
                    <Button
                      variant={notification.read ? "outline" : "default"}
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenConfirmDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      {notification.read ? "View Details" : "Approve/Deny"}
                    </Button>
                  )}
                  {notification.action_type === 'handle_access_request' && notification.action_payload && (
                    <Button
                      variant={notification.read ? "outline" : "default"}
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenAccessDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      {notification.read ? "View Details" : "Handle Request"}
                    </Button>
                  )}
                  {notification.action_type === 'handle_steward_review' && notification.action_payload && (
                    <Button
                      variant={notification.read ? "outline" : "default"}
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenReviewDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      {notification.read ? "View Details" : "Review Contract"}
                    </Button>
                  )}
                  {notification.action_type === 'handle_publish_request' && notification.action_payload && (
                    <Button
                      variant={notification.read ? "outline" : "default"}
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenPublishDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      {notification.read ? "View Details" : "Handle Publish"}
                    </Button>
                  )}
                  {notification.action_type === 'handle_deploy_request' && notification.action_payload && (
                    <Button
                      variant={notification.read ? "outline" : "default"}
                      size="sm"
                      className="mt-2 h-7 px-2 text-xs gap-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDeployDialog(notification.action_payload);
                      }}
                    >
                      <CheckSquare className="h-3.5 w-3.5" />
                      {notification.read ? "View Details" : "Handle Deploy"}
                    </Button>
                  )}
                  {(notification.type === 'job_progress' || notification.action_type === 'job_progress') && (notification.data || notification.action_payload) && (
                    <div className="mt-2">
                      <Progress value={Number((notification.data || notification.action_payload)?.progress ?? 0)} />
                      {((notification.data || notification.action_payload)?.status) && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Status: {String((notification.data || notification.action_payload)?.status)}
                        </p>
                      )}
                      {(notification.data || notification.action_payload)?.run_id && (
                        <p className="text-xs text-muted-foreground">
                          Run ID: {String((notification.data || notification.action_payload).run_id)}
                        </p>
                      )}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(notification.created_at).toLocaleString()}
                  </p>
                </div>
                {notification.can_delete && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0"
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
    {isAccessDialogOpen && selectedAccessPayload && (
      <ConfirmAccessRequestDialog
        isOpen={isAccessDialogOpen}
        onOpenChange={setIsAccessDialogOpen}
        requesterEmail={selectedAccessPayload?.requester_email ?? 'Unknown User'}
        entityType={(selectedAccessPayload?.entity_type ?? 'data_product') as 'data_product' | 'data_contract'}
        entityId={selectedAccessPayload?.entity_id ?? 'Unknown ID'}
        onDecisionMade={handleDecisionMade}
      />
    )}
    {selectedReviewPayload && (
      <HandleStewardReviewDialog
        isOpen={isReviewDialogOpen}
        onOpenChange={setIsReviewDialogOpen}
        contractId={selectedReviewPayload.contract_id ?? 'Unknown ID'}
        contractName={selectedReviewPayload.contract_name}
        requesterEmail={selectedReviewPayload.requester_email ?? 'Unknown User'}
        onDecisionMade={handleDecisionMade}
      />
    )}
    {selectedPublishPayload && (
      <HandlePublishRequestDialog
        isOpen={isPublishDialogOpen}
        onOpenChange={setIsPublishDialogOpen}
        contractId={selectedPublishPayload.contract_id ?? 'Unknown ID'}
        contractName={selectedPublishPayload.contract_name}
        requesterEmail={selectedPublishPayload.requester_email ?? 'Unknown User'}
        onDecisionMade={handleDecisionMade}
      />
    )}
    {selectedDeployPayload && (
      <HandleDeployRequestDialog
        isOpen={isDeployDialogOpen}
        onOpenChange={setIsDeployDialogOpen}
        contractId={selectedDeployPayload.contract_id ?? 'Unknown ID'}
        contractName={selectedDeployPayload.contract_name}
        requesterEmail={selectedDeployPayload.requester_email ?? 'Unknown User'}
        catalog={selectedDeployPayload.catalog}
        schema={selectedDeployPayload.schema}
        onDecisionMade={handleDecisionMade}
      />
    )}
    </>
  );
} 