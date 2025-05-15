import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, GitCompare, Plus } from 'lucide-react';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

interface Dataset {
  id: string;
  name: string;
  catalog: string;
  schema: string;
  table: string;
  entityColumn: string;
  type: 'customer' | 'product' | 'supplier' | 'location';
  totalRecords: number;
}

interface ComparisonResult {
  datasetA: string;
  datasetB: string;
  matchingEntities: number;
  uniqueToA: number;
  uniqueToB: number;
  matchScore: number;
  commonColumns: string[];
  sampleMatches: Array<{
    entityA: string;
    entityB: string;
    confidence: number;
  }>;
  columnStats: Array<{
    column: string;
    matchRate: number;
    nullRate: number;
  }>;
}

export default function MasterDataManagement() {
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [entityType, setEntityType] = useState<string>('');
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<ComparisonResult[]>([]);
  const [detailedResults, setDetailedResults] = useState<ComparisonResult[]>([]);
  const [selectedComparison, setSelectedComparison] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const [datasets] = useState<Dataset[]>([
    {
      id: '1',
      name: 'CRM Customers',
      catalog: 'sales',
      schema: 'crm',
      table: 'customers',
      entityColumn: 'customer_id',
      type: 'customer',
      totalRecords: 50000
    },
    {
      id: '2',
      name: 'ERP Customers',
      catalog: 'finance',
      schema: 'erp',
      table: 'customers',
      entityColumn: 'cust_id',
      type: 'customer',
      totalRecords: 45000
    },
    {
      id: '3',
      name: 'Marketing Contacts',
      catalog: 'marketing',
      schema: 'campaigns',
      table: 'contacts',
      entityColumn: 'contact_id',
      type: 'customer',
      totalRecords: 75000
    },
    {
      id: '4',
      name: 'Product Catalog',
      catalog: 'products',
      schema: 'master',
      table: 'products',
      entityColumn: 'product_id',
      type: 'product',
      totalRecords: 25000
    },
    {
      id: '5',
      name: 'ERP Products',
      catalog: 'finance',
      schema: 'erp',
      table: 'products',
      entityColumn: 'sku',
      type: 'product',
      totalRecords: 22000
    },
    {
      id: '6',
      name: 'Supplier Directory',
      catalog: 'procurement',
      schema: 'master',
      table: 'suppliers',
      entityColumn: 'supplier_id',
      type: 'supplier',
      totalRecords: 5000
    },
    {
      id: '7',
      name: 'Store Locations',
      catalog: 'retail',
      schema: 'master',
      table: 'locations',
      entityColumn: 'location_id',
      type: 'location',
      totalRecords: 1200
    },
    {
      id: '8',
      name: 'Warehouse Locations',
      catalog: 'logistics',
      schema: 'master',
      table: 'warehouses',
      entityColumn: 'warehouse_id',
      type: 'location',
      totalRecords: 150
    }
  ]);

  useEffect(() => {
    // Set breadcrumbs
    setStaticSegments([]);
    setDynamicTitle('Master Data Management');

    // Cleanup breadcrumbs on unmount
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const handleAnalyze = async () => {
    if (selectedDatasets.length < 2) {
      setError('Please select at least two datasets to compare');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      // Mock API call with delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Generate mock results
      const mockResults: ComparisonResult[] = [];
      for (let i = 0; i < selectedDatasets.length; i++) {
        for (let j = i + 1; j < selectedDatasets.length; j++) {
          const datasetA = datasets.find(d => d.id === selectedDatasets[i]);
          const datasetB = datasets.find(d => d.id === selectedDatasets[j]);
          
          if (!datasetA || !datasetB) continue;

          mockResults.push({
            datasetA: datasetA.name,
            datasetB: datasetB.name,
            matchingEntities: Math.floor(Math.random() * 40000),
            uniqueToA: Math.floor(Math.random() * 10000),
            uniqueToB: Math.floor(Math.random() * 10000),
            matchScore: Math.random() * 100,
            commonColumns: ['id', 'name', 'email', 'phone', 'address'],
            sampleMatches: [
              { entityA: "CUST001", entityB: "C-001", confidence: 0.95 },
              { entityA: "CUST002", entityB: "C-002", confidence: 0.88 },
              { entityA: "CUST003", entityB: "C-003", confidence: 0.92 }
            ],
            columnStats: [
              { column: 'id', matchRate: 0.95, nullRate: 0.01 },
              { column: 'name', matchRate: 0.85, nullRate: 0.05 },
              { column: 'email', matchRate: 0.75, nullRate: 0.15 },
              { column: 'phone', matchRate: 0.65, nullRate: 0.25 }
            ]
          });
        }
      }
      
      setDetailedResults(mockResults);
      setResults(mockResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze datasets');
    } finally {
      setAnalyzing(false);
    }
  };

  const renderDetailedResults = () => {
    if (!selectedComparison) return null;
    
    const detail = detailedResults.find(r => 
      `${r.datasetA}-${r.datasetB}` === selectedComparison
    );
    
    if (!detail) return null;

    return (
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Detailed Analysis: {detail.datasetA} vs {detail.datasetB}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Common Columns */}
          <div>
            <h4 className="text-sm font-medium mb-2">Common Columns</h4>
            <div className="flex flex-wrap gap-1">
              {detail.commonColumns.map(col => (
                <Badge key={col} variant="secondary">{col}</Badge>
              ))}
            </div>
          </div>

          {/* Column Statistics */}
          <div>
            <h4 className="text-sm font-medium mb-2">Column Statistics</h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead className="text-right">Match Rate</TableHead>
                  <TableHead className="text-right">Null Rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.columnStats.map(stat => (
                  <TableRow key={stat.column}>
                    <TableCell>{stat.column}</TableCell>
                    <TableCell className="text-right">{(stat.matchRate * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{(stat.nullRate * 100).toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Sample Matches */}
          <div>
            <h4 className="text-sm font-medium mb-2">Sample Matches</h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Entity A</TableHead>
                  <TableHead>Entity B</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.sampleMatches.map((match, idx) => (
                  <TableRow key={idx}>
                    <TableCell>{match.entityA}</TableCell>
                    <TableCell>{match.entityB}</TableCell>
                    <TableCell className="text-right">{(match.confidence * 100).toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <GitCompare className="w-8 h-8" />
        Master Data Management
      </h1>

      <div className="flex justify-between items-center mb-6">
        <div>
          <p className="text-muted-foreground mt-1">
            Analyze and manage entity overlaps across your data estate
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Entity
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Dataset Selection */}
        <div className="col-span-8">
          <Card>
            <CardHeader>
              <CardTitle>Dataset Selection</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Entity Type</Label>
                  <Select value={entityType} onValueChange={setEntityType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select entity type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="customer">Customer</SelectItem>
                      <SelectItem value="product">Product</SelectItem>
                      <SelectItem value="supplier">Supplier</SelectItem>
                      <SelectItem value="location">Location</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Datasets to Compare</Label>
                  <Select
                    value={selectedDatasets[0] || ''}
                    onValueChange={(value) => {
                      if (!selectedDatasets.includes(value)) {
                        setSelectedDatasets([...selectedDatasets, value]);
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select datasets" />
                    </SelectTrigger>
                    <SelectContent>
                      {datasets
                        .filter(dataset => !selectedDatasets.includes(dataset.id))
                        .map((dataset) => (
                          <SelectItem key={dataset.id} value={dataset.id}>
                            {dataset.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  {selectedDatasets.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedDatasets.map(id => {
                        const dataset = datasets.find(d => d.id === id);
                        return dataset ? (
                          <Badge 
                            key={id} 
                            variant="secondary"
                            className="flex items-center gap-1"
                          >
                            {dataset.name}
                            <button
                              onClick={() => {
                                setSelectedDatasets(selectedDatasets.filter(d => d !== id));
                              }}
                              className="ml-1 hover:text-destructive"
                            >
                              ×
                            </button>
                          </Badge>
                        ) : null;
                      })}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleAnalyze}
                  disabled={analyzing || selectedDatasets.length < 2}
                >
                  <GitCompare className="h-4 w-4 mr-2" />
                  Analyze Overlaps
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Selected Datasets Info */}
        <div className="col-span-4">
          <Card>
            <CardHeader>
              <CardTitle>Selected Datasets</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[300px]">
                {selectedDatasets.map(id => {
                  const dataset = datasets.find(d => d.id === id);
                  return dataset ? (
                    <div key={id} className="mb-4">
                      <h4 className="font-medium">{dataset.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Path: {dataset.catalog}.{dataset.schema}.{dataset.table}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Records: {dataset.totalRecords.toLocaleString()}
                      </p>
                    </div>
                  ) : null;
                })}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Analysis Results */}
        <div className="col-span-12">
          <Card>
            <CardHeader>
              <CardTitle>Analysis Results</CardTitle>
            </CardHeader>
            <CardContent>
              {analyzing && (
                <div className="mb-4">
                  <Progress value={33} className="w-full" />
                </div>
              )}

              {results.length > 0 && (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Dataset A</TableHead>
                        <TableHead>Dataset B</TableHead>
                        <TableHead className="text-right">Matching Entities</TableHead>
                        <TableHead className="text-right">Unique to A</TableHead>
                        <TableHead className="text-right">Unique to B</TableHead>
                        <TableHead className="text-right">Match Score</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((result, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{result.datasetA}</TableCell>
                          <TableCell>{result.datasetB}</TableCell>
                          <TableCell className="text-right">
                            {result.matchingEntities.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right">
                            {result.uniqueToA.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right">
                            {result.uniqueToB.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right">
                            {result.matchScore.toFixed(1)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="mt-4">
                    <Label>View Detailed Analysis</Label>
                    <Select
                      value={selectedComparison || ''}
                      onValueChange={setSelectedComparison}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select comparison" />
                      </SelectTrigger>
                      <SelectContent>
                        {results.map((result, idx) => (
                          <SelectItem key={idx} value={`${result.datasetA}-${result.datasetB}`}>
                            {result.datasetA} vs {result.datasetB}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {renderDetailedResults()}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 