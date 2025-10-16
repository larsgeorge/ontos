/**
 * Deployment policy that controls which catalogs/schemas a user can deploy to.
 * 
 * Policies are resolved from user's roles and group memberships.
 * Template variables ({username}, {email}) are resolved at runtime.
 */
export interface DeploymentPolicy {
  /** Catalogs user can deploy to (wildcards and templates supported) */
  allowed_catalogs: string[];
  
  /** Schemas user can deploy to (wildcards and templates supported) */
  allowed_schemas: string[];
  
  /** Default catalog to pre-select in UI */
  default_catalog?: string;
  
  /** Default schema to pre-select in UI */
  default_schema?: string;
  
  /** Whether deployments require admin approval (overrides catalog-level approval) */
  require_approval: boolean;
  
  /** Whether this user can approve deployment requests */
  can_approve_deployments: boolean;
}

/**
 * API Response type for GET /api/user/deployment-policy
 */
export type DeploymentPolicyResponse = DeploymentPolicy;

