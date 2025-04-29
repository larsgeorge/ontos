import React, { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CreateVersionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  currentVersion: string;
  productTitle: string;
  onSubmit: (newVersion: string) => void; // Callback with the new version string
}

const CreateVersionDialog: React.FC<CreateVersionDialogProps> = ({
  isOpen,
  onOpenChange,
  currentVersion,
  productTitle,
  onSubmit,
}) => {
  const [newVersion, setNewVersion] = useState<string>(currentVersion); // Pre-fill with current
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = () => {
    const trimmedVersion = newVersion.trim();
    if (!trimmedVersion) {
      setError("Version string cannot be empty.");
      return;
    }
    setError(null);
    onSubmit(trimmedVersion);
    onOpenChange(false); // Close dialog on successful submit
  };

  const handleCancel = () => {
    setError(null);
    setNewVersion(currentVersion); // Reset input on cancel
    onOpenChange(false);
  };

  // Reset input when dialog opens/closes externally
  React.useEffect(() => {
    if (isOpen) {
      setNewVersion(currentVersion); // Reset to current when opened
      setError(null);
    }
  }, [isOpen, currentVersion]);


  return (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Create New Version</AlertDialogTitle>
          <AlertDialogDescription>
            Enter the new version identifier for data product "{productTitle}". 
            It's often helpful to increment based on the current version ({currentVersion}).
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="py-4">
          <Label htmlFor="new-version-input" className="mb-2 block">
            New Version String
          </Label>
          <Input
            id="new-version-input"
            value={newVersion}
            onChange={(e) => setNewVersion(e.target.value)}
            placeholder="e.g., v1.1, v2.0-beta"
            className={error ? "border-destructive" : ""}
          />
          {error && <p className="text-sm text-destructive mt-1">{error}</p>}
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleSubmit}>Create Version</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default CreateVersionDialog; 