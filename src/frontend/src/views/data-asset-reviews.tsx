import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ColumnDef } from "@tanstack/react-table";
import { Plus, AlertCircle, Loader2, ClipboardCheck, ChevronDown, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DataTable } from "@/components/ui/data-table";
import { Toaster } from "@/components/ui/toaster";
import { useToast } from "@/hooks/use-toast";
import { useApi } from '@/hooks/use-api';
import { RelativeDate } from '@/components/common/relative-date';
import { DataAssetReviewRequest, ReviewRequestStatus } from '@/types/data-asset-review';

// Import the Create Dialog
import CreateReviewRequestDialog from '@/components/data-asset-reviews/create-review-request-dialog';

// Helper function to check API response (reuse if available globally)
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string }, name: string): T => {
    if (response.error) {
        throw new Error(`${name} fetch failed: ${response.error}`);
    }
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    if (response.data === null || response.data === undefined) {
        throw new Error(`${name} fetch returned null or undefined data.`);
    }
    return response.data as T;
};

export default function DataAssetReviews() {
    const [requests, setRequests] = useState<DataAssetReviewRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

    const api = useApi();
    const { get, delete: deleteApi } = api;
    const navigate = useNavigate();
    const { toast } = useToast();

    const fetchRequests = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await get<DataAssetReviewRequest[]>('/api/data-asset-reviews');
            const requestsData = checkApiResponse(response, 'Review Requests');
            setRequests(Array.isArray(requestsData) ? requestsData : []);
        } catch (err: any) {
            console.error('Error fetching review requests:', err);
            setError(err.message || 'Failed to load review requests');
            setRequests([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, [get]);

    const handleOpenCreateDialog = () => {
        setIsCreateDialogOpen(true);
    };

    const handleCreateSuccess = (newRequest: DataAssetReviewRequest) => {
        toast({ title: 'Success', description: `Review request ${newRequest.id} created.` });
        fetchRequests(); // Refresh the list
        setIsCreateDialogOpen(false);
        // Optional: Navigate to the new request's details page
        // navigate(`/data-asset-reviews/${newRequest.id}`);
    };

    const handleDeleteRequest = async (id: string, skipConfirm = false) => {
        if (!skipConfirm && !confirm('Are you sure you want to delete this review request?')) {
            return;
        }
        try {
            await deleteApi(`/api/data-asset-reviews/${id}`);
            toast({ title: 'Success', description: 'Review request deleted.' });
            fetchRequests(); // Refresh list
        } catch (err: any) {
            const errorMsg = err.message || 'Failed to delete request.';
            toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
            setError(errorMsg);
            if (skipConfirm) throw err; // Re-throw for bulk delete
        }
    };

    // --- Status Color Helper --- //
    const getStatusColor = (status: ReviewRequestStatus): "default" | "secondary" | "destructive" | "outline" => {
        switch (status) {
            case ReviewRequestStatus.APPROVED: return 'default'; // Greenish or success
            case ReviewRequestStatus.IN_REVIEW: return 'secondary'; // Blueish or info
            case ReviewRequestStatus.NEEDS_REVIEW: return 'outline'; // Changed from 'warning' to 'outline'
            case ReviewRequestStatus.DENIED: return 'destructive'; // Reddish
            case ReviewRequestStatus.CANCELLED: return 'outline'; // Greyish
            case ReviewRequestStatus.QUEUED: return 'outline'; // Default/Greyish
            default: return 'outline';
        }
    };

    // --- Column Definitions --- //
    const columns = useMemo<ColumnDef<DataAssetReviewRequest>[]>(() => [
        {
            accessorKey: "id",
            header: ({ column }) => (
                <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                    Request ID <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
            ),
            cell: ({ row }) => <div className="text-xs">{row.original.id}</div>,
        },
        {
            accessorKey: "status",
            header: ({ column }) => (
                <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                    Status <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
            ),
            cell: ({ row }) => (
                <Badge variant={getStatusColor(row.original.status)}>{row.original.status}</Badge>
            ),
        },
        {
            accessorKey: "reviewer_email",
            header: "Reviewer",
            cell: ({ row }) => <div>{row.original.reviewer_email}</div>,
        },
        {
            accessorKey: "requester_email",
            header: "Requester",
            cell: ({ row }) => <div>{row.original.requester_email}</div>,
        },
        {
            accessorKey: "assets",
            header: "Assets",
            cell: ({ row }) => <Badge variant="outline">{row.original.assets?.length ?? 0}</Badge>,
            enableSorting: false,
        },
        {
            accessorKey: "created_at",
            header: ({ column }) => (
                <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                    Created <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
            ),
            cell: ({ row }) => <RelativeDate date={row.original.created_at} />,
        },
        {
            accessorKey: "updated_at",
            header: ({ column }) => (
                <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                    Updated <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
            ),
            cell: ({ row }) => <RelativeDate date={row.original.updated_at} />,
        },
        {
            id: "actions",
            enableHiding: false,
            cell: ({ row }) => {
                const request = row.original;
                return (
                    <div className="flex space-x-1 justify-end">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive"
                            onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteRequest(request.id, false);
                            }}
                            title="Delete Request"
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                );
            },
        },
    ], [handleDeleteRequest, getStatusColor]);

    return (
        <div className="py-6">
            <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
                <ClipboardCheck className="w-8 h-8" />
                Data Asset Reviews
            </h1>

            {error && (
                <Alert variant="destructive" className="mb-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {loading ? (
                <div className="flex justify-center items-center h-64">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                </div>
            ) : (
                <DataTable
                    columns={columns}
                    data={requests}
                    searchColumn="reviewer_email" // Or search by ID, requester, etc.
                    toolbarActions={
                        <>
                            <Button onClick={handleOpenCreateDialog} className="gap-2 h-9">
                                <Plus className="h-4 w-4" />
                                Create Request
                            </Button>
                            {/* Add other toolbar actions if needed */}
                        </>
                    }
                    bulkActions={(selectedRows) => (
                        <Button
                            variant="destructive"
                            size="sm"
                            className="h-9"
                            onClick={async () => {
                                const selectedIds = selectedRows.map(r => r.id).filter((id): id is string => !!id);
                                if (selectedIds.length === 0) return;
                                if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected request(s)?`)) return;

                                try {
                                    await Promise.all(selectedIds.map(id => deleteApi(`/api/data-asset-reviews/${id}`)));
                                    toast({ title: 'Bulk Delete Success', description: `${selectedIds.length} request(s) deleted.` });
                                    fetchRequests();
                                } catch (err: any) {
                                    console.error("Bulk delete failed:", err);
                                    toast({ title: 'Bulk Delete Error', description: `Some requests could not be deleted. ${err.message}`, variant: 'destructive' });
                                    fetchRequests(); // Still refresh to see partial success/failure
                                }
                            }}
                            disabled={selectedRows.length === 0}
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete Selected ({selectedRows.length})
                        </Button>
                    )}
                    onRowClick={(row) => {
                        const requestId = row.original.id;
                        if (requestId) {
                            navigate(`/data-asset-reviews/${requestId}`);
                        }
                    }}
                />
            )}

            {/* Create Request Dialog */}
            <CreateReviewRequestDialog
                 isOpen={isCreateDialogOpen}
                 onOpenChange={setIsCreateDialogOpen}
                 api={api} // Pass API hooks
                 onSubmitSuccess={handleCreateSuccess}
             />

            <Toaster />
        </div>
    );
} 