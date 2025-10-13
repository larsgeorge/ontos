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

// --- Approval Privileges ---
export enum ApprovalEntity {
    DOMAINS = 'DOMAINS',
    CONTRACTS = 'CONTRACTS',
    PRODUCTS = 'PRODUCTS',
    BUSINESS_TERMS = 'BUSINESS_TERMS',
    ASSET_REVIEWS = 'ASSET_REVIEWS',
}

export type ApprovalPrivileges = Partial<Record<ApprovalEntity, boolean>>;

export interface AppRole {
    id: string;
    name: string;
    description?: string | null;
    assigned_groups: string[];
    feature_permissions: Record<string, FeatureAccessLevel>;
    home_sections?: HomeSection[];
    approval_privileges?: ApprovalPrivileges;
}

export type UserPermissions = Record<string, FeatureAccessLevel>;