// Corresponds to api/models/data_asset_reviews.py

// --- Enums --- //
export enum ReviewRequestStatus {
    QUEUED = "queued",
    IN_REVIEW = "in_review",
    APPROVED = "approved",
    NEEDS_REVIEW = "needs_review",
    DENIED = "denied",
    CANCELLED = "cancelled",
}

export enum ReviewedAssetStatus {
    PENDING = "pending",
    APPROVED = "approved",
    REJECTED = "rejected",
    NEEDS_CLARIFICATION = "needs_clarification",
}

export enum AssetType {
    TABLE = "table",
    VIEW = "view",
    FUNCTION = "function",
    MODEL = "model",
    VOLUME = "volume",
    NOTEBOOK = "notebook",
    // Add others as needed
}

// --- Interfaces --- //

// Interface for an asset being reviewed
export interface ReviewedAsset {
    id?: string;
    asset_fqn: string;
    asset_type: AssetType;
    status: ReviewedAssetStatus;
    comments?: string | null;
    updated_at: string; // ISO date string
}

// Interface for creating a new review request
export interface DataAssetReviewRequestCreate {
    requester_email: string;
    reviewer_email: string;
    asset_fqns: string[];
    notes?: string | null;
}

// Interface for the full data asset review request
export interface DataAssetReviewRequest {
    id: string;
    requester_email: string;
    reviewer_email: string;
    status: ReviewRequestStatus;
    notes?: string | null;
    created_at: string; // ISO date string
    updated_at: string; // ISO date string
    assets: ReviewedAsset[];
}

// Interface for updating the overall request status
export interface DataAssetReviewRequestUpdateStatus {
    status: ReviewRequestStatus;
    notes?: string | null;
}

// Interface for updating a specific asset's status
export interface ReviewedAssetUpdate {
    status: ReviewedAssetStatus;
    comments?: string | null;
}

// --- Types for Dropdowns/Distinct Values (if needed) --- //
export type ReviewStatus = ReviewRequestStatus | ReviewedAssetStatus;

// Type for Catalog items (similar to Catalog Commander)
export interface CatalogItem {
  id: string;       // FQN (e.g., catalog.schema.table)
  name: string;     // Display name (e.g., table name)
  type: 'catalog' | 'schema' | 'table' | 'view' | 'function'; // Extend as needed
  children?: CatalogItem[];
  hasChildren?: boolean;
}

// Type for Asset Definition (plain text)
export type AssetDefinition = string;

// Type for Table Preview Data (reuse from Catalog Commander or define similarly)
export interface TablePreview {
  schema: Array<{ name: string; type: string; nullable: boolean }>;
  data: any[];
  total_rows?: number; // Optional based on backend capability
}

// --- LLM Analysis Types --- //
export interface AssetAnalysisResponse {
    request_id: string;
    asset_id: string;
    analysis_summary: string;
    model_used?: string | null;
    timestamp: string; // ISO date string
} 