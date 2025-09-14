// Single source of truth for settings types

export enum FeatureAccessLevel {
    NONE = "None",
    READ_ONLY = "Read-only",
    READ_WRITE = "Read/Write",
    FILTERED = "Filtered",
    FULL = "Full",
    ADMIN = "Admin",
}

export interface FeatureConfig {
    name: string;
    allowed_levels: FeatureAccessLevel[];
}

export enum HomeSection {
    REQUIRED_ACTIONS = 'REQUIRED_ACTIONS',
    DATA_CURATION = 'DATA_CURATION',
    DISCOVERY = 'DISCOVERY',
}

export interface AppRole {
    id: string;
    name: string;
    description?: string | null;
    assigned_groups: string[];
    feature_permissions: Record<string, FeatureAccessLevel>;
    home_sections?: HomeSection[];
}

export type UserPermissions = Record<string, FeatureAccessLevel>;