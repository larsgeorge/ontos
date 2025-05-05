import { useState, useEffect, useCallback, useMemo } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, PlusCircle, Loader2, AlertCircle, BoxSelect } from 'lucide-react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { Toaster } from "@/components/ui/toaster";

// Check API response helper (adjusted for nullable error)
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string | null | undefined }, name: string): T => {
    if (response.error) throw new Error(`${name} fetch failed: ${response.error}`);
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    if (response.data === null || response.data === undefined) throw new Error(`${name} fetch returned null or undefined data.`);
    return response.data as T;
};

// Use default export
export default function DataDomainsView() {
  const [domains, setDomains] = useState<DataDomain[]>([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingDomain, setEditingDomain] = useState<DataDomain | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deletingDomainId, setDeletingDomainId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const api = useApi();
  const { toast } = useToast();
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();

  const featureId = 'data-domains';
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  const fetchDataDomains = useCallback(async () => {
    if (!canRead && !permissionsLoading) {
        setError("Permission Denied: Cannot view data domains.");
        setLoading(false);
        return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<DataDomain[]>('/api/data-domains');
      const data = checkApiResponse(response, 'Data Domains');
      setDomains(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Failed to load data domains');
      setDomains([]);
      toast({ variant: "destructive", title: "Error fetching domains", description: err.message });
    } finally {
      setLoading(false);
    }
  }, [canRead, permissionsLoading]);

  useEffect(() => {
    fetchDataDomains();
  }, [fetchDataDomains]);

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
    setLoading(true);
    try {
      const response = await api.delete(`/api/data-domains/${deletingDomainId}`);
      if (response.error) { 
        throw new Error(response.error);
      }
      toast({ title: "Domain Deleted", description: "The data domain was successfully deleted." });
      fetchDataDomains();
    } catch (err: any) {
       toast({ variant: "destructive", title: "Error Deleting Domain", description: err.message || 'Failed to delete domain.' });
    } finally {
       setIsDeleteDialogOpen(false);
       setDeletingDomainId(null);
       setLoading(false);
    }
  };

  const columns = useMemo<ColumnDef<DataDomain>[]>(() => [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => <div className="font-medium">{row.getValue("name")}</div>,
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
  ], [canWrite, canAdmin]);

  if (loading || permissionsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  if (!canRead) {
    return (
       <div className="container mx-auto py-10">
            <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>Permission Denied: Cannot view data domains.</AlertDescription>
            </Alert>
       </div>
    );
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
           <BoxSelect className="w-8 h-8" />
           Data Domains
        </h1>
        <DataDomainFormDialog
          isOpen={isFormOpen}
          onOpenChange={setIsFormOpen}
          domain={editingDomain}
          onSubmitSuccess={handleFormSubmitSuccess}
          trigger={
            <Button onClick={handleOpenCreateDialog} disabled={!canWrite}>
              <PlusCircle className="mr-2 h-4 w-4" /> Add New Domain
            </Button>
          }
        />
      </div>

      {error && (
          <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Error loading data: {error}</AlertDescription>
          </Alert>
      )}

      <DataTable 
         columns={columns} 
         data={domains} 
         searchColumn="name"
      />

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
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700" disabled={loading}>
               {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      <Toaster /> 
    </div>
  );
}