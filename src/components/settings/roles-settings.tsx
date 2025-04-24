import React, { useState, useEffect, useMemo } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { AppRole, FeatureConfig } from '@/types/settings'; // Assuming types are defined here or imported
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, Pencil, Trash2, AlertCircle, MoreHorizontal, ChevronDown } from 'lucide-react';
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

export default function RolesSettings() {
    const { get, delete: deleteApi } = useApi();
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
        } catch (err: any) {
            console.error("Error deleting role:", err);
            const errorMsg = err.message || 'Failed to delete role.';
            toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
            setError(errorMsg);
        }
    };

    const handleDialogSubmitSuccess = () => {
        fetchData(); // Refresh data after successful dialog submission
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
    ], [handleOpenDialog, handleDeleteRole]); // Add dependencies if needed (e.g., canWrite, canAdmin)

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