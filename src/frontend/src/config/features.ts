import {
    Database,
    FileTextIcon,
    BookOpen,
    Users, // Using Users icon from About for MDM for now
    CheckCircle, // Using CheckCircle icon from About for Compliance for now
    Globe,
    Lock, // Using Lock icon from About for Security for now
    Shield,
    RefreshCw, // Using RefreshCw icon from About for Entitlements Sync for now
    GitBranch, // Using GitBranch icon from About for Catalog Commander for now
    Settings,
    Info,
    ClipboardCheck, // Added icon for Data Asset Review
    BoxSelect, // Added icon for Data Domain
    Search, // Added icon for Search
    type LucideIcon, // Import LucideIcon type
  } from 'lucide-react';
  
  export type FeatureMaturity = 'ga' | 'beta' | 'alpha';
  export type FeatureGroup = 'Data Management' | 'Security' | 'Tools' | 'System';
  
  export interface FeatureConfig {
    id: string; // Unique identifier, e.g., 'data-products'
    name: string;
    path: string;
    description: string;
    icon: LucideIcon; // Use LucideIcon type
    group: FeatureGroup;
    maturity: FeatureMaturity;
    showInLanding?: boolean; // Show on Home/About pages?
  }
  
  export const features: FeatureConfig[] = [
    // Data Management
    {
      id: 'data-domains',
      name: 'Data Domains',
      path: '/data-domains',
      description: 'Organize data products and assets into logical domains.',
      icon: BoxSelect,
      group: 'Data Management',
      maturity: 'ga',
      showInLanding: true,
    },
    {
      id: 'data-contracts',
      name: 'Data Contracts',
      path: '/data-contracts',
      description: 'Define and enforce technical metadata standards.',
      icon: FileTextIcon,
      group: 'Data Management',
      maturity: 'ga',
      showInLanding: true,
    },
    {
      id: 'data-products',
      name: 'Data Products',
      path: '/data-products',
      description: 'Group and manage related Databricks assets with tags.',
      icon: Database,
      group: 'Data Management',
      maturity: 'ga',
      showInLanding: true,
    },
    {
      id: 'business-glossary',
      name: 'Business Glossary',
      path: '/business-glossary',
      description: 'Create and manage business terms and definitions.',
      icon: BookOpen,
      group: 'Data Management',
      maturity: 'ga',
      showInLanding: true,
    },
    {
      id: 'compliance',
      name: 'Compliance',
      path: '/compliance',
      description: 'Create, verify compliance rules, and calculate scores.',
      icon: CheckCircle,
      group: 'Data Management',
      maturity: 'beta',
      showInLanding: true,
    },
    {
      id: 'estate-manager',
      name: 'Estate Manager',
      path: '/estate-manager',
      description: 'Manage multiple Databricks instances across regions and clouds.',
      icon: Globe,
      group: 'Data Management',
      maturity: 'alpha',
      showInLanding: true,
    },
    {
      id: 'master-data',
      name: 'Master Data Management',
      path: '/master-data',
      description: 'Build a golden record of your data.',
      icon: Users,
      group: 'Data Management',
      maturity: 'alpha', // Requires external setup
      showInLanding: true,
    },
    // Security
    {
      id: 'security',
      name: 'Security Features',
      path: '/security',
      description: 'Enable advanced security like differential privacy.',
      icon: Lock,
      group: 'Security',
      maturity: 'alpha',
      showInLanding: true,
    },
    {
      id: 'entitlements',
      name: 'Entitlements',
      path: '/entitlements',
      description: 'Manage access privileges through personas and groups.',
      icon: Shield,
      group: 'Security',
      maturity: 'beta',
      showInLanding: true,
    },
    {
      id: 'entitlements-sync',
      name: 'Entitlements Sync',
      path: '/entitlements-sync',
      description: 'Synchronize entitlements with external systems.',
      icon: RefreshCw,
      group: 'Security',
      maturity: 'alpha',
      showInLanding: true,
    },
    {
      id: 'data-asset-reviews',
      name: 'Data Asset Review',
      path: '/data-asset-reviews',
      description: 'Review and approve Databricks assets like tables, views, and functions.',
      icon: ClipboardCheck, // Use the imported icon
      group: 'Security',
      maturity: 'alpha',
      showInLanding: true,
    },
    // Tools
    {
      id: 'catalog-commander',
      name: 'Catalog Commander',
      path: '/catalog-commander',
      description: 'Side-by-side catalog explorer for asset management.',
      icon: GitBranch,
      group: 'Tools',
      maturity: 'ga',
      showInLanding: true,
    },
    {
      id: 'search',
      name: 'Search',
      path: '/search',
      description: 'Search across data products, contracts, and knowledge graph.',
      icon: Search,
      group: 'Tools',
      maturity: 'ga',
      showInLanding: false,
    },
    // System
    {
      id: 'settings',
      name: 'Settings',
      path: '/settings',
      description: 'Configure application settings, jobs, and integrations.',
      icon: Settings,
      group: 'System',
      maturity: 'ga',
      showInLanding: false,
    },
    {
      id: 'about',
      name: 'About',
      path: '/about',
      description: 'Information about the application and its features.',
      icon: Info,
      group: 'System',
      maturity: 'ga',
      showInLanding: false,
    },
  ];
  
  // Helper function to get feature by path
  export const getFeatureByPath = (path: string): FeatureConfig | undefined =>
    features.find((feature) => feature.path === path);
  
  // Helper function to get feature name by path (for breadcrumbs)
  export const getFeatureNameByPath = (pathSegment: string): string => {
      // Find feature where the path ends with the segment (handling potential leading '/')
      const feature = features.find(f => f.path === `/${pathSegment}` || f.path === pathSegment);
      return feature?.name || pathSegment; // Return name or segment itself if not found
  };
  
  // Helper function to group features for navigation
  export const getNavigationGroups = (
      allowedMaturities: FeatureMaturity[] = ['ga'] // Default to GA only
    ): { name: FeatureGroup; items: FeatureConfig[] }[] => {
      const grouped: { [key in FeatureGroup]?: FeatureConfig[] } = {};
  
      features
        .filter((feature) => allowedMaturities.includes(feature.maturity))
        .forEach((feature) => {
          if (!grouped[feature.group]) {
            grouped[feature.group] = [];
          }
          grouped[feature.group]?.push(feature);
        });
  
      // Define the desired order of groups
      const groupOrder: FeatureGroup[] = ['Data Management', 'Security', 'Tools', 'System'];
  
      // Sort groups according to the defined order
      return groupOrder
          .map(groupName => ({
              name: groupName,
              items: grouped[groupName] || [] // Get items or empty array if group is missing
          }))
          .filter(group => group.items.length > 0); // Remove empty groups
    };
  
  // Helper function to get features for landing pages (Home, About)
  export const getLandingPageFeatures = (
      allowedMaturities: FeatureMaturity[] = ['ga'] // Default to GA only
  ): FeatureConfig[] => {
      return features.filter(
          (feature) =>
          feature.showInLanding && allowedMaturities.includes(feature.maturity)
      );
  };
  