import { Github, BookOpenCheck } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from '@/components/ui/button';
import { getLandingPageFeatures, FeatureConfig } from '@/config/features';
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';
import { cn } from '@/lib/utils';

export default function About() {
  const allowedMaturities = useFeatureVisibilityStore((state) => state.allowedMaturities);

  const features = getLandingPageFeatures(allowedMaturities);

  const detailedDescriptions: { [key: string]: string[] } = {
    'data-domains': [
      '• Define and manage data domains, subdomains, and ownership structures.',
      '• Visualize relationships between domains and dependent data products.',
      '• Assign assets and products to domains for clearer accountability.',
      '• Follows the BITOL Open Data Domain Standard (ODDS).',
    ],
    'data-contracts': [
      '• Instrument Data Products with technical metadata based on the Open Data Contract Standard (ODCS).',
      '• Schema validation, quality checks, access control verification, sample data display.',
      '• Contracts can be text-based (e.g., JSON/YAML); supports BITOL ODCS JSON schema.',
    ],
    'data-products': [
      '• Group Databricks assets (tables, views, functions, models, dashboards, jobs, notebooks).',
      '• Use tags (e.g., data-product-name, data-product-domain).',
    ],
    'business-glossary': [
      '• Hierarchical glossaries per org unit (company, LOB, department, team, project).',
      '• Merged bottom-up for users, allowing overrides.',
      '• Terms have tags, markdown descriptions, lifecycle status, assigned assets.',
    ],
    'master-data': [
      '• Integrates with Zingg.ai for MDM capabilities.',
    ],
    'compliance': [
      '• Define and verify compliance rules.',
      '• Calculate an overall compliance score.',
    ],
    'estate-manager': [
      '• Central view of multiple workspaces.',
      '• Monitor resource usage and costs.',
      '• Manage configurations across estates.',
    ],
    'security': [
      '• Enable advanced security features (e.g., differential privacy) on assets.',
    ],
    'entitlements': [
      '• Define reusable personas (e.g., Analyst, Engineer).',
      '• Assign personas to Databricks groups.',
      '• Simplify privilege management at scale.',
    ],
    'entitlements-sync': [
      '• Keep entitlements aligned with external systems (e.g., IDP).',
      '• Detect and resolve synchronization conflicts.',
      '• Maintain audit logs of all changes.',
    ],
    'catalog-commander': [
      '• Norton Commander-inspired dual-pane explorer for managing catalog assets.',
      '• Copy/move tables and schemas easily.',
    ],
    'data-asset-reviews': [
      '• Workflow for reviewing and approving assets (tables, views, functions).',
      '• Includes notifications for reviewers and requesters.',
    ],
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">About Ontos</h1>
      <p className="text-lg text-muted-foreground mb-10">
        This application runs as a Databricks App and provides Unity Catalog and related
        services focused on metadata management, governance, and operational tools.
      </p>

      <h2 className="text-3xl font-semibold mb-8">Core Features</h2>

      {features.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {features.map((feature: FeatureConfig) => (
            <Card key={feature.id} className="flex flex-col relative">
              {feature.maturity !== 'ga' && (
                <span className={cn(
                  "absolute top-2 right-2 text-xs font-semibold px-2 py-0.5 rounded-full z-10",
                  feature.maturity === 'beta' ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300" : "",
                  feature.maturity === 'alpha' ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300" : ""
                )}>
                  {feature.maturity.toUpperCase()}
                </span>
              )}
              <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                  <feature.icon className="w-6 h-6 text-primary" />
                  <CardTitle>{feature.name}</CardTitle>
                </div>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-grow">
                {detailedDescriptions[feature.id] && (
                  <ul className="space-y-1.5 text-sm text-muted-foreground mt-2">
                    {detailedDescriptions[feature.id].map((point, index) => (
                      <li key={index}>{point}</li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground text-center mb-12">No features available for the selected feature previews.</p>
      )}

      <h2 className="text-3xl font-semibold mb-6">Technology Stack</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12 text-center">
        <div className="p-4 border rounded-lg bg-card text-card-foreground">
          <p className="font-semibold">Frontend</p>
          <p className="text-sm text-muted-foreground">React, TypeScript, Shadcn UI, Tailwind CSS, Vite</p>
        </div>
        <div className="p-4 border rounded-lg bg-card text-card-foreground">
          <p className="font-semibold">Backend</p>
          <p className="text-sm text-muted-foreground">Python, FastAPI</p>
        </div>
        <div className="p-4 border rounded-lg bg-card text-card-foreground">
          <p className="font-semibold">Database</p>
          <p className="text-sm text-muted-foreground">PostgreSQL</p>
        </div>
        <div className="p-4 border rounded-lg bg-card text-card-foreground">
          <p className="font-semibold">Platform</p>
          <p className="text-sm text-muted-foreground">Databricks Apps</p>
        </div>
      </div>

      <h2 className="text-3xl font-semibold mb-6">Contribute & Learn More</h2>
      <div className="flex flex-col md:flex-row gap-4">
        <Button asChild size="lg">
          <a href="https://github.com/larsgeorge/ucsak-app" target="_blank" rel="noopener noreferrer">
            <Github className="mr-2 h-5 w-5" /> View on GitHub
          </a>
        </Button>
        <Button variant="outline" asChild size="lg" disabled>
          <a href="#" target="_blank" rel="noopener noreferrer" aria-disabled="true" onClick={(e) => e.preventDefault()}>
            <BookOpenCheck className="mr-2 h-5 w-5" /> Read Documentation (Coming Soon)
          </a>
        </Button>
      </div>
    </div>
  );
} 