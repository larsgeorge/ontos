import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Database, FileText as FileTextIcon, BookOpen, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DataCurationSection() {
  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">Data Curation</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Database className="h-6 w-6 text-primary" /><CardTitle>Create Data Product</CardTitle></div>
            <CardDescription>Use the wizard to define a new data product.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild><Link to="/data-products">Open</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><FileTextIcon className="h-6 w-6 text-primary" /><CardTitle>Define Data Contract</CardTitle></div>
            <CardDescription>Create or update a technical contract.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild><Link to="/data-contracts">Open</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><BookOpen className="h-6 w-6 text-primary" /><CardTitle>Create Dataset</CardTitle></div>
            <CardDescription>Manage datasets for matching and mastering.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline"><Link to="/master-data">Open</Link></Button>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>Create Schema</CardTitle></div>
            <CardDescription>Create or manage schemas and permissions.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button asChild variant="outline"><Link to="/catalog-commander">Open</Link></Button>
              <Button asChild><Link to="/create-uc">Create</Link></Button>
            </div>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center gap-3"><Globe className="h-6 w-6 text-primary" /><CardTitle>Create Catalog</CardTitle></div>
            <CardDescription>Provision catalogs and manage access.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button asChild variant="outline"><Link to="/catalog-commander">Open</Link></Button>
              <Button asChild><Link to="/create-uc">Create</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}


