import React, { useState, useEffect } from 'react';
import { Edit2, Trash2, Plus, Gavel } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from '@/components/ui/badge';

interface SecurityFeature {
  id: string;
  name: string;
  description: string;
  type: 'row_filtering' | 'column_masking' | 'differential_privacy' | 'homomorphic_encryption' | 'envelope_encryption' | 'tokenization';
  status: string;
  target: string;
  conditions: string[];
  last_updated: string;
}

const SecurityFeatures: React.FC = () => {
  const [features, setFeatures] = useState<SecurityFeature[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingFeature, setEditingFeature] = useState<SecurityFeature | null>(null);
  const [newFeature, setNewFeature] = useState<Partial<SecurityFeature>>({
    name: '',
    description: '',
    type: 'row_filtering',
    status: 'active',
    target: '',
    conditions: []
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchFeatures();
  }, []);

  const fetchFeatures = async () => {
    try {
      const response = await fetch('/api/security-features');
      if (!response.ok) {
        throw new Error('Failed to fetch security features');
      }
      const data = await response.json();
      setFeatures(data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load security features',
        variant: 'destructive',
      });
    }
  };

  const handleSaveFeature = async () => {
    try {
      const url = editingFeature 
        ? `/api/security-features/${editingFeature.id}`
        : '/api/security-features';
      
      const method = editingFeature ? 'PUT' : 'POST';
      const body = editingFeature ? editingFeature : newFeature;

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('Failed to save security feature');
      }

      toast({
        title: 'Success',
        description: `Security feature ${editingFeature ? 'updated' : 'created'} successfully`,
      });

      fetchFeatures();
      setIsDialogOpen(false);
      setEditingFeature(null);
      setNewFeature({
        name: '',
        description: '',
        type: 'row_filtering',
        status: 'active',
        target: '',
        conditions: []
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save security feature',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteFeature = async (id: string) => {
    try {
      const response = await fetch(`/api/security-features/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete security feature');
      }

      toast({
        title: 'Success',
        description: 'Security feature deleted successfully',
      });

      fetchFeatures();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete security feature',
        variant: 'destructive',
      });
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
  };

  const formatType = (type: string) => {
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <Gavel className="w-8 h-8" /> Security Features
      </h1>
      <div className="flex justify-between items-center mb-6">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Security Feature
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingFeature ? 'Edit Security Feature' : 'Add Security Feature'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={editingFeature?.name || newFeature.name}
                  onChange={(e) => {
                    if (editingFeature) {
                      setEditingFeature({ ...editingFeature, name: e.target.value });
                    } else {
                      setNewFeature({ ...newFeature, name: e.target.value });
                    }
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={editingFeature?.description || newFeature.description}
                  onChange={(e) => {
                    if (editingFeature) {
                      setEditingFeature({ ...editingFeature, description: e.target.value });
                    } else {
                      setNewFeature({ ...newFeature, description: e.target.value });
                    }
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select
                  value={editingFeature?.type || newFeature.type}
                  onValueChange={(value) => {
                    if (editingFeature) {
                      setEditingFeature({ ...editingFeature, type: value as any });
                    } else {
                      setNewFeature({ ...newFeature, type: value as any });
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="row_filtering">Row Filtering</SelectItem>
                    <SelectItem value="column_masking">Column Masking</SelectItem>
                    <SelectItem value="differential_privacy">Differential Privacy</SelectItem>
                    <SelectItem value="homomorphic_encryption">Homomorphic Encryption</SelectItem>
                    <SelectItem value="envelope_encryption">Envelope Encryption</SelectItem>
                    <SelectItem value="tokenization">Tokenization</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="target">Target</Label>
                <Input
                  id="target"
                  value={editingFeature?.target || newFeature.target}
                  onChange={(e) => {
                    if (editingFeature) {
                      setEditingFeature({ ...editingFeature, target: e.target.value });
                    } else {
                      setNewFeature({ ...newFeature, target: e.target.value });
                    }
                  }}
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveFeature}>
                {editingFeature ? 'Save Changes' : 'Add Feature'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Conditions</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {features.map((feature) => (
              <TableRow key={feature.id}>
                <TableCell className="font-medium">{feature.name}</TableCell>
                <TableCell>{formatType(feature.type)}</TableCell>
                <TableCell>{feature.target}</TableCell>
                <TableCell>
                  <Badge className={getStatusColor(feature.status)}>
                    {feature.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {feature.conditions.map((condition, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {condition}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  {new Date(feature.last_updated).toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end space-x-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEditingFeature(feature);
                        setIsDialogOpen(true);
                      }}
                    >
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteFeature(feature.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default SecurityFeatures; 