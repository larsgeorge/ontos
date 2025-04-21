import { FeatureAccessLevel } from "@/types/settings";

// Mirror of api/common/features.py ACCESS_LEVEL_ORDER
export const ACCESS_LEVEL_ORDER: Record<FeatureAccessLevel, number> = {
    [FeatureAccessLevel.NONE]: 0,
    [FeatureAccessLevel.READ_ONLY]: 1,
    [FeatureAccessLevel.FILTERED]: 2,
    [FeatureAccessLevel.READ_WRITE]: 3,
    [FeatureAccessLevel.FULL]: 4,
    [FeatureAccessLevel.ADMIN]: 5,
}; 