import React, { useState, useEffect } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { AppRole, FeatureConfig } from '@/types/settings'; // Assuming types are defined here or imported
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, Pencil, Trash2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
// Import the dialog (will be created next)
// import RoleFormDialog from './role-form-dialog';
import RoleFormDialog from './role-form-dialog'; // Uncomment and import

export default function RolesSettings() {
    const { get, delete: deleteApi } = useApi();
    const { toast } = useToast();
    const [roles, setRoles] = useState<AppRole[]>([]);
    const [features, setFeatures] = useState<Record<string, FeatureConfig>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [roleToEdit, setRoleToEdit] = useState<AppRole | null>(null);

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
        // TODO: Implement RoleFormDialog
    };

    const handleDeleteRole = async (roleId: string, roleName: string) => {
        if (!confirm(`Are you sure you want to delete the role "${roleName}"?`)) return;

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

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Application Roles</CardTitle>
                    <CardDescription>Manage user roles and their feature permissions.</CardDescription>
                </div>
                <Button onClick={() => handleOpenDialog()} size="sm" className="gap-1">
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
                ) : roles.length === 0 ? (
                    <p className="text-sm text-center text-muted-foreground py-4">No roles configured yet.</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Name</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead>Assigned Groups</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {roles.map((role) => (
                                <TableRow key={role.id}>
                                    <TableCell className="font-medium">{role.name}</TableCell>
                                    <TableCell>{role.description || '-'}</TableCell>
                                    <TableCell>
                                        {role.assigned_groups && role.assigned_groups.length > 0 ? (
                                            <div className="flex flex-wrap gap-1">
                                                {role.assigned_groups.map((group: string) => (
                                                    <Badge key={group} variant="secondary">{group}</Badge>
                                                ))}
                                            </div>
                                        ) : (
                                            <span className="text-xs text-muted-foreground">None</span>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(role)} title="Edit Role">
                                            <Pencil className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="text-destructive hover:text-destructive"
                                            onClick={() => handleDeleteRole(role.id, role.name)}
                                            disabled={role.id === 'admin'} // Example: Prevent deleting admin role
                                            title={role.id === 'admin' ? "Cannot delete default Admin role" : "Delete Role"}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
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