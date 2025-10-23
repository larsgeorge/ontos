/**
 * ODPS v1.0.0 Lifecycle State Machine
 *
 * Implements the Open Data Product Standard lifecycle transitions.
 * Reference: https://github.com/bitol-io/open-data-product-standard
 */

import { DataProductStatus } from '@/types/data-product';

/**
 * Defines allowed status transitions for ODPS v1.0.0 lifecycle.
 *
 * Lifecycle flow:
 * proposed → draft → active → deprecated → retired
 *
 * Additional rules:
 * - Can go back from draft to proposed (refinement)
 * - Can skip proposed and start at draft
 * - Can jump from any status to deprecated (emergency deprecation)
 * - Retired is terminal (no transitions out)
 */
export const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  [DataProductStatus.PROPOSED]: [
    DataProductStatus.DRAFT,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.DRAFT]: [
    DataProductStatus.PROPOSED, // Back to refinement
    DataProductStatus.ACTIVE,
    DataProductStatus.DEPRECATED, // Emergency deprecation
  ],
  [DataProductStatus.ACTIVE]: [
    DataProductStatus.DEPRECATED,
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
  [DataProductStatus.PROPOSED]: {
    label: 'Proposed',
    description: 'Initial proposal, not yet in development',
    variant: 'secondary',
    icon: '💡',
  },
  [DataProductStatus.DRAFT]: {
    label: 'Draft',
    description: 'Under development, not yet published',
    variant: 'secondary',
    icon: '✏️',
  },
  [DataProductStatus.ACTIVE]: {
    label: 'Active',
    description: 'Published and available for consumption',
    variant: 'default',
    icon: '✅',
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
    case DataProductStatus.PROPOSED:
      return 'Move to Draft to start development';
    case DataProductStatus.DRAFT:
      return 'Publish to Active when ready for production';
    case DataProductStatus.ACTIVE:
      return 'Mark as Deprecated when planning retirement';
    case DataProductStatus.DEPRECATED:
      return 'Retire when no longer in use';
    case DataProductStatus.RETIRED:
      return null; // Terminal state
    default:
      return null;
  }
}
