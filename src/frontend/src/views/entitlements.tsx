import React, { useState, useEffect } from 'react';
import { User, Settings, Plus, Edit2, Trash2, Shield, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

interface Privilege {
  securable_id: string;
  securable_type: string;
  permission: string;
}

interface Persona {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  privileges: Privilege[];
  groups: string[];
}

const Entitlements: React.FC = () => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isPrivilegeDialogOpen, setIsPrivilegeDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPrivilege, setNewPrivilege] = useState<Partial<Privilege>>({
    securable_id: '',
    securable_type: 'table',
    permission: 'READ'
  });
  const { toast } = useToast();

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  const availableGroups = [
    'data_science_team',
    'ml_engineers',
    'data_engineering',
    'etl_team',
    'business_analysts',
    'reporting_team',
    'data_governance',
    'data_stewards',
    'compliance_team',
    'business_users',
    'report_viewers',
    'model_developers',
    'pipeline_operators',
    'analytics_users'
  ];

  useEffect(() => {
    fetchPersonas();
    setStaticSegments([]);
    setDynamicTitle('Entitlements');

    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchPersonas = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/entitlements/personas');
      if (!response.ok) throw new Error('Failed to fetch personas');
      const data = await response.json();
      setPersonas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load personas');
      toast({
        title: 'Error',
        description: 'Failed to load personas',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPersona = (persona: Persona) => {
    setSelectedPersona(persona);
  };

  const handleAddPersona = () => {
    setIsEditMode(false);
    setSelectedPersona(null);
    setIsDialogOpen(true);
  };

  const handleEditPersona = () => {
    if (selectedPersona) {
      setIsEditMode(true);
      setIsDialogOpen(true);
    }
  };

  const handleDeletePersona = async () => {
    if (!selectedPersona) return;
    
    try {
      const response = await fetch(`/api/entitlements/personas/${selectedPersona.id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) throw new Error('Failed to delete persona');
      
      await fetchPersonas();
      setSelectedPersona(null);
      toast({
        title: 'Success',
        description: 'Persona deleted successfully',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete persona');
      toast({
        title: 'Error',
        description: 'Failed to delete persona',
        variant: 'destructive',
      });
    }
  };

  const handleSavePersona = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    
    const personaData: Partial<Persona> = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
    };
    
    try {
      const method = isEditMode ? 'PUT' : 'POST';
      const url = isEditMode 
        ? `/api/entitlements/personas/${selectedPersona?.id}`
        : '/api/entitlements/personas';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(personaData),
      });

      if (!response.ok) throw new Error('Failed to save persona');
      
      await fetchPersonas();
      setIsDialogOpen(false);
      toast({
        title: 'Success',
        description: `Persona ${isEditMode ? 'updated' : 'created'} successfully`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save persona');
      toast({
        title: 'Error',
        description: 'Failed to save persona',
        variant: 'destructive',
      });
    }
  };

  const handleAddPrivilege = () => {
    setIsPrivilegeDialogOpen(true);
  };

  const handleSavePrivilege = async () => {
    if (!selectedPersona || !newPrivilege.securable_id) return;
    
    try {
      const response = await fetch(`/api/entitlements/personas/${selectedPersona.id}/privileges`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newPrivilege),
      });

      if (!response.ok) throw new Error('Failed to add privilege');
      
      const updatedPersona = await response.json();
      setSelectedPersona(updatedPersona);
      setPersonas(personas.map(p => 
        p.id === updatedPersona.id ? updatedPersona : p
      ));
      
      setIsPrivilegeDialogOpen(false);
      setNewPrivilege({
        securable_id: '',
        securable_type: 'table',
        permission: 'READ'
      });
      toast({
        title: 'Success',
        description: 'Privilege added successfully',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add privilege');
      toast({
        title: 'Error',
        description: 'Failed to add privilege',
        variant: 'destructive',
      });
    }
  };

  const handleRemovePrivilege = async (securableId: string) => {
    if (!selectedPersona) return;
    
    try {
      const response = await fetch(`/api/entitlements/personas/${selectedPersona.id}/privileges/${securableId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to remove privilege');
      
      const updatedPersona = await response.json();
      setSelectedPersona(updatedPersona);
      setPersonas(personas.map(p => 
        p.id === updatedPersona.id ? updatedPersona : p
      ));
      toast({
        title: 'Success',
        description: 'Privilege removed successfully',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove privilege');
      toast({
        title: 'Error',
        description: 'Failed to remove privilege',
        variant: 'destructive',
      });
    }
  };

  const getPermissionColor = (permission: string) => {
    switch (permission) {
      case 'READ':
        return 'bg-blue-100 text-blue-800';
      case 'WRITE':
        return 'bg-green-100 text-green-800';
      case 'MANAGE':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleUpdateGroups = async (personaId: string, groups: string[]) => {
    try {
      const response = await fetch(`/api/entitlements/personas/${personaId}/groups`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ groups }),
      });

      if (!response.ok) throw new Error('Failed to update groups');
      
      const updatedPersona = await response.json();
      setSelectedPersona(updatedPersona);
      setPersonas(personas.map(p => 
        p.id === updatedPersona.id ? updatedPersona : p
      ));
      toast({
        title: 'Success',
        description: 'Groups updated successfully',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update groups');
      toast({
        title: 'Error',
        description: 'Failed to update groups',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <Shield className="w-8 h-8" /> Entitlements
      </h1>
      <div className="flex justify-between items-center mb-6">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={handleAddPersona} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Persona
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{isEditMode ? 'Edit Persona' : 'Create New Persona'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSavePersona}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Persona Name</Label>
                  <Input
                    id="name"
                    name="name"
                    defaultValue={isEditMode && selectedPersona ? selectedPersona.name : ''}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    name="description"
                    defaultValue={isEditMode && selectedPersona ? selectedPersona.description : ''}
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit">
                  {isEditMode ? 'Save Changes' : 'Create Persona'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-800 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Personas List */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Personas</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[70vh]">
              {isLoading ? (
                <div className="flex justify-center items-center py-10">
                  <Loader2 className="animate-spin h-8 w-8 text-primary" />
                </div>
              ) : personas.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground">
                  No personas found. Create one to get started.
                </div>
              ) : (
                <div className="space-y-2">
                  {personas.map((persona) => (
                    <div
                      key={persona.id}
                      className={`p-4 rounded-md cursor-pointer ${
                        selectedPersona?.id === persona.id
                          ? 'bg-primary/10'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => handleSelectPersona(persona)}
                    >
                      <div className="flex items-center space-x-3">
                        <User className="w-5 h-5" />
                        <div>
                          <h3 className="font-medium">{persona.name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {persona.privileges.length} privileges
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Persona Details */}
        <Card className="md:col-span-3">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>
                {selectedPersona ? selectedPersona.name : 'Select a Persona'}
              </CardTitle>
              {selectedPersona && (
                <div className="flex space-x-2">
                  <Button variant="outline" onClick={handleEditPersona}>
                    <Edit2 className="w-4 h-4 mr-2" />
                    Edit
                  </Button>
                  <Button variant="outline" onClick={handleDeletePersona}>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedPersona ? (
              <Tabs defaultValue="privileges">
                <TabsList>
                  <TabsTrigger value="privileges">Access Privileges</TabsTrigger>
                  <TabsTrigger value="groups">Group Assignments</TabsTrigger>
                </TabsList>
                <TabsContent value="privileges">
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-medium">Privileges</h3>
                      <Button onClick={handleAddPrivilege}>
                        <Plus className="w-4 h-4 mr-2" />
                        Add Privilege
                      </Button>
                    </div>
                    {selectedPersona.privileges.length === 0 ? (
                      <div className="text-center text-muted-foreground py-4">
                        No privileges assigned to this persona.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {selectedPersona.privileges.map((privilege) => (
                          <div
                            key={privilege.securable_id}
                            className="flex items-center justify-between p-4 border rounded-md"
                          >
                            <div>
                              <div className="font-medium">{privilege.securable_id}</div>
                              <div className="text-sm text-muted-foreground">
                                {privilege.securable_type}
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Badge className={getPermissionColor(privilege.permission)}>
                                {privilege.permission}
                              </Badge>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRemovePrivilege(privilege.securable_id)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </TabsContent>
                <TabsContent value="groups">
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium">Assigned Groups</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedPersona.groups.map((group) => (
                        <Badge key={group} variant="outline">
                          {group}
                        </Badge>
                      ))}
                    </div>
                    <div className="space-y-2">
                      <Label>Add Groups</Label>
                      <Select
                        onValueChange={(value) => {
                          if (!selectedPersona.groups.includes(value)) {
                            handleUpdateGroups(selectedPersona.id, [...selectedPersona.groups, value]);
                          }
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select a group" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableGroups
                            .filter(group => !selectedPersona.groups.includes(group))
                            .map(group => (
                              <SelectItem key={group} value={group}>
                                {group}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            ) : (
              <div className="flex flex-col items-center justify-center h-[70vh] text-muted-foreground">
                <Settings className="w-12 h-12 mb-4" />
                <p className="text-lg">Select a persona to view details</p>
                <p className="text-sm">Or create a new one using the "Create Persona" button</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add Privilege Dialog */}
      <Dialog open={isPrivilegeDialogOpen} onOpenChange={setIsPrivilegeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Access Privilege</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="securable_id">Securable ID</Label>
              <Input
                id="securable_id"
                value={newPrivilege.securable_id}
                onChange={(e) => setNewPrivilege({...newPrivilege, securable_id: e.target.value})}
                placeholder="Example: catalog.schema.table"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="securable_type">Securable Type</Label>
              <Select
                value={newPrivilege.securable_type}
                onValueChange={(value) => setNewPrivilege({...newPrivilege, securable_type: value})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="catalog">Catalog</SelectItem>
                  <SelectItem value="schema">Schema</SelectItem>
                  <SelectItem value="table">Table</SelectItem>
                  <SelectItem value="view">View</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="permission">Permission</Label>
              <Select
                value={newPrivilege.permission}
                onValueChange={(value) => setNewPrivilege({...newPrivilege, permission: value})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select permission" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="READ">READ</SelectItem>
                  <SelectItem value="WRITE">WRITE</SelectItem>
                  <SelectItem value="MANAGE">MANAGE</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setIsPrivilegeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePrivilege} disabled={!newPrivilege.securable_id}>
              Add
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Entitlements; 