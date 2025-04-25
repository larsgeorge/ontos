import React, { useState, useEffect, useMemo } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { AppRole, FeatureConfig } from '@/types/settings'; // Assuming types are defined here or imported
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, Pencil, Trash2, AlertCircle, MoreHorizontal, ChevronDown, UserPlus } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import RoleFormDialog from './role-form-dialog'; // Uncomment and import

// --- DataTable Imports ---
import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getSortedRowModel,
    SortingState,
    useReactTable,
    Column, // Import Column type for header context
} from "@tanstack/react-table";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"; // Keep for DataTable structure
import { DataTable } from "@/components/ui/data-table"; // Import DataTable
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
// import { usePermissions } from '@/stores/permissions-store'; // Assuming permissions check needed
import { usePermissions } from '@/stores/permissions-store'; // Import the permissions hook

export default function RolesSettings() {
    const { get, post, delete: deleteApi } = useApi();
    const { toast } = useToast();
    const [roles, setRoles] = useState<AppRole[]>([]);
    const [features, setFeatures] = useState<Record<string, FeatureConfig>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [roleToEdit, setRoleToEdit] = useState<AppRole | null>(null);
    // const { hasPermission } = usePermissions(); // Get permission checking function
    // const featureId = 'settings'; // Or appropriate feature ID
    // const canWrite = hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
    // const canAdmin = hasPermission(featureId, FeatureAccessLevel.ADMIN);
    const { fetchPermissions, fetchAvailableRoles } = usePermissions(); // Get both actions

    const fetchData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [rolesResponse, featuresResponse] = await Promise.all([
                get<AppRole[]>('/api/settings/roles'),
                get<Record<string, FeatureConfig>>('/api/settings/features')
            ]);

            if (rolesResponse.error) throw new Error(`Roles fetch failed: ${rolesResponse.error}`);
            if (featuresResponse.error) throw new Error(`Features fetch failed: ${featuresResponse.error}`);

            setRoles(rolesResponse.data || []);
            setFeatures(featuresResponse.data || {});

        } catch (err: any) {
            console.error("Error fetching roles or features:", err);
            setError(err.message || 'Failed to load roles configuration.');
            setRoles([]);
            setFeatures({});
            toast({ title: 'Error', description: err.message, variant: 'destructive' });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleOpenDialog = (role?: AppRole) => {
        setRoleToEdit(role || null);
        setIsDialogOpen(true);
    };

    // Helper function to refresh permissions and roles
    const refreshPermissionsAndRoles = async () => {
        try {
            await Promise.all([fetchPermissions(), fetchAvailableRoles()]);
            toast({ title: 'Permissions Updated', description: 'User permissions and available roles refreshed.' });
        } catch (err: any) {
            console.error("Error refreshing permissions/roles:", err);
            toast({ title: 'Refresh Failed', description: `Could not refresh permissions/roles: ${err.message}`, variant: 'destructive' });
        }
    };

    // --- New function to handle access request ---
    const handleRequestAccess = async (role: AppRole) => {
        if (!confirm(`Request access to the role "${role.name}"?`)) return;

        toast({ title: 'Sending Request', description: `Requesting access to role ${role.name}...` });
        try {
            // TODO: Replace with actual API call
            // const response = await post(`/api/user/request-role/${role.id}`, {});
            // if (response.error) throw new Error(response.error);

            // --- Mock success for now ---
            // await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay
            // --- End Mock ---

            // Actual API Call
            const response = await post(`/api/user/request-role/${role.id}`, {}); // Empty body for POST
            if (response.error) {
                throw new Error(response.error);
            }

            toast({ title: 'Request Sent', description: `Your request for the role "${role.name}" has been submitted.` });
        } catch (err: any) {
            console.error("Error requesting role access:", err);
            toast({ title: 'Request Failed', description: err.message || 'Failed to submit access request.', variant: 'destructive' });
        }
    };

    const handleDeleteRole = async (roleId: string, roleName: string) => {
        if (!confirm(`Are you sure you want to delete the role "${roleName}"?`)) return;

        // Check permission before deleting (example)
        // if (!canAdmin) {
        //     toast({ title: 'Permission Denied', description: 'You do not have permission to delete roles.', variant: 'destructive' });
        //     return;
        // }

        try {
            await deleteApi(`/api/settings/roles/${roleId}`);
            toast({ title: 'Success', description: `Role "${roleName}" deleted.` });
            fetchData(); // Refresh list
            await fetchPermissions(); // Refresh user permissions
            await refreshPermissionsAndRoles(); // Call the combined refresh helper
        } catch (err: any) {
            console.error("Error deleting role:", err);
            const errorMsg = err.message || 'Failed to delete role.';
            toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
            setError(errorMsg);
        }
    };

    const handleDialogSubmitSuccess = async () => {
        fetchData(); // Refresh data after successful dialog submission
        await fetchPermissions(); // Refresh user permissions
        await refreshPermissionsAndRoles(); // Call the combined refresh helper
    };

    // --- Column Definitions ---
    const columns = useMemo<ColumnDef<AppRole>[]>(() => [
        {
            accessorKey: "name",
            header: ({ column }: { column: Column<AppRole, unknown> }) => (
                <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                    Name <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
            ),
            cell: ({ row }) => <div className="font-medium">{row.getValue("name")}</div>,
            enableSorting: true,
        },
        {
            accessorKey: "description",
            header: ({ column }: { column: Column<AppRole, unknown> }) => (
                 <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
                     Description <ChevronDown className="ml-2 h-4 w-4" />
                 </Button>
            ),
            cell: ({ row }) => <div>{row.getValue("description") || '-'}</div>,
            enableSorting: true,
        },
        {
            accessorKey: "assigned_groups",
            header: "Assigned Groups",
            cell: ({ row }) => {
                const groups = row.getValue("assigned_groups") as string[] || [];
                return (
                    groups.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                            {groups.map((group: string) => (
                                <Badge key={group} variant="secondary">{group}</Badge>
                            ))}
                        </div>
                    ) : (
                        <span className="text-xs text-muted-foreground">None</span>
                    )
                );
            },
            enableSorting: false,
        },
        {
            id: "request",
            header: "", // No header text needed
            cell: ({ row }) => {
                 const role = row.original;
                 // TODO: Add logic to potentially hide this button if user already has the role or equivalent access?
                 return (
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-8 gap-1"
                        onClick={() => handleRequestAccess(role)}
                    >
                        <UserPlus className="h-3.5 w-3.5" />
                        Request
                    </Button>
                 );
            },
            enableHiding: true, // Allow hiding if needed
        },
        {
            id: "actions",
            cell: ({ row }) => {
                const role = row.original;
                const isAdminRole = role.name.toLowerCase() === 'admin'; // Example check

                return (
                    <div className="flex justify-end">
                         <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="h-8 w-8 p-0">
                                    <span className="sr-only">Open menu</span>
                                    <MoreHorizontal className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem
                                    onClick={() => handleOpenDialog(role)}
                                    // disabled={!canWrite} // Example permission check
                                >
                                    <Pencil className="mr-2 h-4 w-4" /> Edit Role
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    onClick={() => handleDeleteRole(role.id, role.name)}
                                    className="text-destructive focus:text-destructive"
                                    disabled={isAdminRole} // Example: Disable deleting admin role
                                    // disabled={isAdminRole || !canAdmin} // Example with permission check
                                >
                                     <Trash2 className="mr-2 h-4 w-4" /> Delete Role
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                );
            },
            enableHiding: false,
        },
    ], [handleOpenDialog, handleDeleteRole, refreshPermissionsAndRoles]); // Add refreshPermissionsAndRoles to dependency array

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Application Roles</CardTitle>
                    <CardDescription>Manage user roles and their feature permissions.</CardDescription>
                </div>
                <Button
                    onClick={() => handleOpenDialog()}
                    size="sm"
                    className="gap-1"
                    // disabled={!canWrite} // Example permission check
                >
                    <Plus className="h-4 w-4" /> Create Role
                </Button>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex justify-center items-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    </div>
                ) : error ? (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                ) : (
                     // --- DataTable Implementation ---
                     <DataTable
                        columns={columns}
                        data={roles}
                        // Optional props (add if needed, like in data-products)
                        // searchColumn="name" // Example: If you add search input
                        // toolbarActions={<>...</>} // Example: If you add toolbar actions
                        // bulkActions={(selectedRows) => ...} // Example: If you add bulk actions
                     />
                 )}
            </CardContent>

            {/* Render RoleFormDialog */}
            {isDialogOpen && (
                <RoleFormDialog
                    isOpen={isDialogOpen}
                    onOpenChange={setIsDialogOpen}
                    initialRole={roleToEdit}
                    featuresConfig={features} // Pass the fetched features config
                    onSubmitSuccess={handleDialogSubmitSuccess}
                />
            )}
        </Card>
    );
} 