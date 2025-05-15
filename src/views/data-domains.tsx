import { useState, useEffect, useCallback, useMemo } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, PlusCircle, Loader2, AlertCircle, BoxSelect, ListTree, TableIcon } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { DataDomain } from '@/types/data-domain';
import { useApi } from '@/hooks/use-api';
import { useToast } from "@/hooks/use-toast";
import { DataDomainFormDialog } from '@/components/data-domains/data-domain-form-dialog';
import { RelativeDate } from '@/components/common/relative-date';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from "@/components/ui/badge";
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { Toaster } from "@/components/ui/toaster";
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { useNavigate } from 'react-router-dom';
import DataDomainGraphView from '@/components/data-domains/data-domain-graph-view';

// Placeholder for Graph View
// const DataDomainGraphViewPlaceholder = () => (
//   <div className="border rounded-lg p-8 text-center text-muted-foreground h-[calc(100vh-280px)] flex flex-col items-center justify-center">
//     <ListTree className="w-16 h-16 mb-4" />
//     <p className="text-lg font-semibold">Data Domain Graph View</p>
//     <p>This feature is under construction. Hierarchical relationships will be visualized here.</p>
//   </div>
// );

// Check API response helper (adjusted for nullable error)
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string | null | undefined }, name: string): T => {
    if (response.error) throw new Error(`${name} fetch failed: ${response.error}`);
    // Check if data exists, is an object, and has a 'detail' property that is a string
    if (response.data && typeof response.data === 'object' && response.data !== null && 'detail' in response.data && typeof (response.data as { detail: string }).detail === 'string') {
        throw new Error(`${name} fetch failed: ${(response.data as { detail: string }).detail}`);
    }
    if (response.data === null || response.data === undefined) throw new Error(`${name} fetch returned null or undefined data.`);
    return response.data as T;
};

export default function DataDomainsView() {
  const [domains, setDomains] = useState<DataDomain[]>([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingDomain, setEditingDomain] = useState<DataDomain | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deletingDomainId, setDeletingDomainId] = useState<string | null>(null);
  const [componentError, setComponentError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');

  const { get: apiGet, delete: apiDelete, loading: apiIsLoading } = useApi();
  const { toast } = useToast();
  const navigate = useNavigate();
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  const featureId = 'data-domains';
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  const fetchDataDomains = useCallback(async () => {
    if (!canRead && !permissionsLoading) {
        setComponentError("Permission Denied: Cannot view data domains.");
        return;
    }
    setComponentError(null);
    try {
      const response = await apiGet<DataDomain[]>('/api/data-domains');
      const data = checkApiResponse(response, 'Data Domains');
      const domainsData = Array.isArray(data) ? data : [];
      setDomains(domainsData);
      if (response.error) {
        setComponentError(response.error);
        setDomains([]);
        toast({ variant: "destructive", title: "Error fetching domains", description: response.error });
      }
    } catch (err: any) {
      setComponentError(err.message || 'Failed to load data domains');
      setDomains([]);
      toast({ variant: "destructive", title: "Error fetching domains", description: err.message });
    }
  }, [canRead, permissionsLoading, apiGet, toast, setComponentError]);

  useEffect(() => {
    fetchDataDomains();
    setStaticSegments([]);
    setDynamicTitle('Data Domains');
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [fetchDataDomains, setStaticSegments, setDynamicTitle]);

  const handleOpenCreateDialog = () => {
    if (!canWrite) {
        toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to create data domains." });
        return;
    }
    setEditingDomain(null);
    setIsFormOpen(true);
  };

  const handleOpenEditDialog = (domain: DataDomain) => {
    if (!canWrite) {
        toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to edit data domains." });
        return;
    }
    setEditingDomain(domain);
    setIsFormOpen(true);
  };

  const handleFormSubmitSuccess = (savedDomain: DataDomain) => {
    fetchDataDomains();
  };

  const openDeleteDialog = (domainId: string) => {
    if (!canAdmin) {
         toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to delete data domains." });
         return;
    }
    setDeletingDomainId(domainId);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingDomainId || !canAdmin) return;
    try {
      const response = await apiDelete(`/api/data-domains/${deletingDomainId}`);
      if (response.error) {
        let errorMessage = response.error;
        if (response.data && typeof response.data === 'object' && response.data !== null && 'detail' in response.data && typeof (response.data as { detail: string }).detail === 'string') {
            errorMessage = (response.data as { detail: string }).detail;
        }
        throw new Error(errorMessage || 'Failed to delete domain.');
      }
      toast({ title: "Domain Deleted", description: "The data domain was successfully deleted." });
      fetchDataDomains();
    } catch (err: any) {
       toast({ variant: "destructive", title: "Error Deleting Domain", description: err.message || 'Failed to delete domain.' });
       setComponentError(err.message || 'Failed to delete domain.');
    } finally {
       setIsDeleteDialogOpen(false);
       setDeletingDomainId(null);
    }
  };

  const handleNavigateToDomain = (domainId: string) => {
    navigate(`/data-domains/${domainId}`);
  };

  const columns = useMemo<ColumnDef<DataDomain>[]>(() => [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const domain = row.original;
        return (
          <div>
            <span 
              className="font-medium cursor-pointer hover:underline"
              onClick={() => handleNavigateToDomain(domain.id)}
            >
              {domain.name}
            </span>
            {domain.parent_name && (
              <div 
                className="text-xs text-muted-foreground cursor-pointer hover:underline"
                onClick={(e) => {
                    e.stopPropagation(); 
                    if (domain.parent_id) handleNavigateToDomain(domain.parent_id);
                }}
              >
                ↳ Parent: {domain.parent_name}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => (
        <div className="truncate max-w-sm text-sm text-muted-foreground">
          {row.getValue("description") || '-'}
        </div>
      ),
    },
    {
      accessorKey: "owner",
      header: "Owners",
      cell: ({ row }) => {
        const owners = row.original.owner;
        if (!owners || owners.length === 0) return '-' ;
        return (
            <div className="flex flex-col space-y-0.5">
                {owners.map((owner, index) => (
                    <Badge key={index} variant="outline" className="text-xs truncate w-fit">{owner}</Badge>
                ))}
            </div>
        );
      }
    },
    {
      accessorKey: "tags",
      header: "Tags",
      cell: ({ row }) => {
        const tags = row.original.tags;
        if (!tags || tags.length === 0) return '-' ;
        return (
            <div className="flex flex-wrap gap-1">
                {tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">{tag}</Badge>
                ))}
            </div>
        );
      }
    },
    {
        accessorKey: "children_count",
        header: "Children",
        cell: ({ row }) => row.original.children_count ?? 0,
    },
    {
      accessorKey: "updated_at",
      header: "Last Updated",
      cell: ({ row }) => {
         const dateValue = row.getValue("updated_at");
         return dateValue ? <RelativeDate date={dateValue as string | Date | number} /> : 'N/A';
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        const domain = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => handleNavigateToDomain(domain.id)}>
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleOpenEditDialog(domain)} disabled={!canWrite}>
                Edit Domain
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => openDeleteDialog(domain.id)}
                className="text-red-600 focus:text-red-600 focus:bg-red-50"
                disabled={!canAdmin}
              >
                Delete Domain
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ], [canWrite, canAdmin, navigate]);

  return (
    <div className="py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
           <BoxSelect className="w-8 h-8" />
           Data Domains
        </h1>
        <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 border rounded-md p-0.5">
                <Button
                    variant={viewMode === 'table' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('table')}
                    className="h-8 px-2"
                    title="Table View"
                >
                    <TableIcon className="h-4 w-4" />
                </Button>
                <Button
                    variant={viewMode === 'graph' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('graph')}
                    className="h-8 px-2"
                    title="Graph View"
                >
                    <ListTree className="h-4 w-4" />
                </Button>
            </div>
            <Button onClick={handleOpenCreateDialog} disabled={!canWrite || permissionsLoading || apiIsLoading}>
                <PlusCircle className="mr-2 h-4 w-4" /> Add New Domain
            </Button>
        </div>
      </div>

      {(apiIsLoading || permissionsLoading) ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : !canRead ? (
         <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Permission Denied</AlertTitle>
              <AlertDescription>You do not have permission to view data domains.</AlertDescription>
         </Alert>
      ) : componentError ? (
          <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error Loading Data</AlertTitle>
              <AlertDescription>{componentError}</AlertDescription>
          </Alert>
      ) : viewMode === 'table' ? (
        <>
          <DataTable 
             columns={columns} 
             data={domains} 
             searchColumn="name"
             toolbarActions={null} 
          />
          <DataDomainFormDialog
            isOpen={isFormOpen}
            onOpenChange={setIsFormOpen}
            domain={editingDomain}
            onSubmitSuccess={handleFormSubmitSuccess}
            allDomains={domains} 
          />
        </>
      ) : (
        <DataDomainGraphView domains={domains} />
      )}

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the data domain.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingDomainId(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700" disabled={apiIsLoading || permissionsLoading}>
               {(apiIsLoading || permissionsLoading) ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      <Toaster /> 
    </div>
  );
}