// Based on api/common/features.py

export enum FeatureAccessLevel {
  NONE = "None",
  READ_ONLY = "Read-only",
  READ_WRITE = "Read/Write",
  FILTERED = "Filtered",
  FULL = "Full",
  ADMIN = "Admin",
}

// Optional: Define the order if needed in frontend logic
export const ACCESS_LEVEL_ORDER: Record<FeatureAccessLevel, number> = {
  [FeatureAccessLevel.NONE]: 0,
  [FeatureAccessLevel.READ_ONLY]: 1,
  [FeatureAccessLevel.FILTERED]: 2,
  [FeatureAccessLevel.READ_WRITE]: 3,
  [FeatureAccessLevel.FULL]: 4,
  [FeatureAccessLevel.ADMIN]: 5,
}; 