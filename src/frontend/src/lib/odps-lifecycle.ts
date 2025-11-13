/**
 * ODPS Lifecycle State Machine (aligned with ODCS)
 *
 * Implements the unified lifecycle transitions for Data Products.
 * Reference: https://github.com/bitol-io/open-data-product-standard
 */

import { DataProductStatus } from '@/types/data-product';

/**
 * Defines allowed status transitions for ODPS lifecycle (aligned with ODCS).
 *
 * Lifecycle flow:
 * draft → [sandbox] → proposed → under_review → approved → active → certified → deprecated → retired
 *
 * Key rules:
 * - Sandbox is optional for testing before review
 * - Can return to draft from review states for revisions
 * - Can jump to deprecated from any status (emergency deprecation)
 * - Certified is elevated status after active
 * - Retired is terminal (no transitions out)
 */
export const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  [DataProductStatus.DRAFT]: [
    DataProductStatus.SANDBOX,
    DataProductStatus.PROPOSED,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.SANDBOX]: [
    DataProductStatus.DRAFT,
    DataProductStatus.PROPOSED,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.PROPOSED]: [
    DataProductStatus.DRAFT, // Back for revisions
    DataProductStatus.UNDER_REVIEW,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.UNDER_REVIEW]: [
    DataProductStatus.DRAFT, // Rejected, needs revisions
    DataProductStatus.APPROVED,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.APPROVED]: [
    DataProductStatus.ACTIVE,
    DataProductStatus.DRAFT, // Back for revisions
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.ACTIVE]: [
    DataProductStatus.CERTIFIED, // Elevate to certified
    DataProductStatus.DEPRECATED,
  ],
  [DataProductStatus.CERTIFIED]: [
    DataProductStatus.DEPRECATED,
    DataProductStatus.ACTIVE, // Demote from certified
  ],
  [DataProductStatus.DEPRECATED]: [
    DataProductStatus.RETIRED,
    DataProductStatus.ACTIVE, // Reactivation (if deprecation was premature)
  ],
  [DataProductStatus.RETIRED]: [], // Terminal state
};

/**
 * Status display configuration for UI
 */
export interface StatusConfig {
  label: string;
  description: string;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  icon?: string;
}

export const STATUS_CONFIG: Record<string, StatusConfig> = {
  [DataProductStatus.DRAFT]: {
    label: 'Draft',
    description: 'Initial development, not yet in review',
    variant: 'secondary',
    icon: '✏️',
  },
  [DataProductStatus.SANDBOX]: {
    label: 'Sandbox',
    description: 'Testing and validation phase',
    variant: 'secondary',
    icon: '🧪',
  },
  [DataProductStatus.PROPOSED]: {
    label: 'Proposed',
    description: 'Submitted for review',
    variant: 'secondary',
    icon: '💡',
  },
  [DataProductStatus.UNDER_REVIEW]: {
    label: 'Under Review',
    description: 'Being reviewed by data stewards',
    variant: 'outline',
    icon: '👀',
  },
  [DataProductStatus.APPROVED]: {
    label: 'Approved',
    description: 'Approved by stewards, ready to publish',
    variant: 'default',
    icon: '✔️',
  },
  [DataProductStatus.ACTIVE]: {
    label: 'Active',
    description: 'Published and available for consumption',
    variant: 'default',
    icon: '✅',
  },
  [DataProductStatus.CERTIFIED]: {
    label: 'Certified',
    description: 'Verified for high-value or regulated use',
    variant: 'default',
    icon: '🏅',
  },
  [DataProductStatus.DEPRECATED]: {
    label: 'Deprecated',
    description: 'Still available but marked for retirement',
    variant: 'outline',
    icon: '⚠️',
  },
  [DataProductStatus.RETIRED]: {
    label: 'Retired',
    description: 'No longer available, archived',
    variant: 'destructive',
    icon: '🔒',
  },
};

/**
 * Checks if a status transition is allowed
 */
export function canTransitionTo(currentStatus: string, targetStatus: string): boolean {
  const normalizedCurrent = currentStatus.toLowerCase();
  const normalizedTarget = targetStatus.toLowerCase();

  if (normalizedCurrent === normalizedTarget) {
    return false; // No transition to same status
  }

  const allowedTargets = ALLOWED_TRANSITIONS[normalizedCurrent] || [];
  return allowedTargets.includes(normalizedTarget);
}

/**
 * Gets all allowed target statuses from current status
 */
export function getAllowedTransitions(currentStatus: string): string[] {
  const normalizedCurrent = currentStatus.toLowerCase();
  return ALLOWED_TRANSITIONS[normalizedCurrent] || [];
}

/**
 * Gets status configuration for UI display
 */
export function getStatusConfig(status: string): StatusConfig {
  const normalizedStatus = status.toLowerCase();
  return STATUS_CONFIG[normalizedStatus] || {
    label: status,
    description: 'Unknown status',
    variant: 'secondary',
  };
}

/**
 * Validates a status transition and returns error message if invalid
 */
export function validateTransition(
  currentStatus: string,
  targetStatus: string
): { valid: boolean; error?: string } {
  const normalizedCurrent = currentStatus.toLowerCase();
  const normalizedTarget = targetStatus.toLowerCase();

  // Check if target status exists
  if (!Object.values(DataProductStatus).includes(normalizedTarget as DataProductStatus)) {
    return {
      valid: false,
      error: `Invalid target status: ${targetStatus}`,
    };
  }

  // Check if same status
  if (normalizedCurrent === normalizedTarget) {
    return {
      valid: false,
      error: 'Product is already in this status',
    };
  }

  // Check if transition is allowed
  if (!canTransitionTo(normalizedCurrent, normalizedTarget)) {
    const currentConfig = getStatusConfig(normalizedCurrent);
    const targetConfig = getStatusConfig(normalizedTarget);
    return {
      valid: false,
      error: `Cannot transition from ${currentConfig.label} to ${targetConfig.label}. Allowed transitions: ${getAllowedTransitions(normalizedCurrent)
        .map((s) => getStatusConfig(s).label)
        .join(', ') || 'none'}`,
    };
  }

  return { valid: true };
}

/**
 * Gets recommended next action for current status
 */
export function getRecommendedAction(currentStatus: string): string | null {
  const normalizedCurrent = currentStatus.toLowerCase();

  switch (normalizedCurrent) {
    case DataProductStatus.DRAFT:
      return 'Move to Sandbox for testing or submit for review';
    case DataProductStatus.SANDBOX:
      return 'Submit for review when testing is complete';
    case DataProductStatus.PROPOSED:
      return 'Wait for steward to initiate review';
    case DataProductStatus.UNDER_REVIEW:
      return 'Steward will approve or request revisions';
    case DataProductStatus.APPROVED:
      return 'Publish to Active to make available';
    case DataProductStatus.ACTIVE:
      return 'Certify for elevated status or deprecate when retiring';
    case DataProductStatus.CERTIFIED:
      return 'Deprecate when planning retirement';
    case DataProductStatus.DEPRECATED:
      return 'Retire when no longer in use';
    case DataProductStatus.RETIRED:
      return null; // Terminal state
    default:
      return null;
  }
}
