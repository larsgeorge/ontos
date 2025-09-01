export type FeatureAccessLevel = 'None' | 'Read-only' | 'Read/Write' | 'Filtered' | 'Full' | 'Admin';

export interface AppRole {
  id: string;
  name: string;
  description?: string;
  assigned_groups: string[];
  feature_permissions: Record<string, FeatureAccessLevel>;
}

export interface FeatureConfig {
  name: string;
  allowed_levels: FeatureAccessLevel[];
}

export interface UserPermissions {
  [featureId: string]: FeatureAccessLevel;
}

// Based on api/common/features.py FeatureAccessLevel
export enum FeatureAccessLevel {
    NONE = "None",
    READ_ONLY = "Read-only",
    READ_WRITE = "Read/Write",
    FILTERED = "Filtered",
    FULL = "Full",
    ADMIN = "Admin",
}

// Based on api/common/features.py APP_FEATURES structure (API response)
export interface FeatureConfig {
    name: string;
    allowed_levels: FeatureAccessLevel[]; // Array of string enum values
}

// Based on api/models/settings.py AppRole
export interface AppRole {
    id: string;
    name: string;
    description?: string | null;
    assigned_groups: string[];
    feature_permissions: Record<string, FeatureAccessLevel>; // Key is feature ID
}

// Type alias for the permissions response
export type UserPermissions = Record<string, FeatureAccessLevel>; 