import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { AuditLog, PaginatedAuditLogResponse, AuditLogFilters } from '@/types/audit-log';
import { Search, Download, ChevronLeft, ChevronRight } from 'lucide-react';

const ITEMS_PER_PAGE = 50;

export default function AuditTrail() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const { toast } = useToast();

  // Filters
  const [filters, setFilters] = useState<AuditLogFilters>({
    skip: 0,
    limit: ITEMS_PER_PAGE,
  });
  const [searchUsername, setSearchUsername] = useState('');
  const [searchFeature, setSearchFeature] = useState('');
  const [searchAction, setSearchAction] = useState('');
  const [successFilter, setSuccessFilter] = useState<string>('all');

  const currentPage = Math.floor((filters.skip || 0) / ITEMS_PER_PAGE) + 1;
  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);

  useEffect(() => {
    fetchAuditLogs();
  }, [filters]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();

      if (filters.skip) params.append('skip', filters.skip.toString());
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.username) params.append('username', filters.username);
      if (filters.feature) params.append('feature', filters.feature);
      if (filters.action) params.append('action', filters.action);
      if (filters.success !== undefined) params.append('success', filters.success.toString());
      if (filters.start_time) params.append('start_time', filters.start_time);
      if (filters.end_time) params.append('end_time', filters.end_time);

      const response = await fetch(`/api/audit?${params.toString()}`);

      if (!response.ok) {
        throw new Error('Failed to fetch audit logs');
      }

      const data: PaginatedAuditLogResponse = await response.json();
      setLogs(data.items);
      setTotal(data.total);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load audit logs',
        variant: 'destructive',
      });
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    setFilters({
      ...filters,
      skip: 0, // Reset to first page when filters change
      username: searchUsername || undefined,
      feature: searchFeature || undefined,
      action: searchAction || undefined,
      success: successFilter === 'all' ? undefined : successFilter === 'true',
    });
  };

  const handleClearFilters = () => {
    setSearchUsername('');
    setSearchFeature('');
    setSearchAction('');
    setSuccessFilter('all');
    setFilters({
      skip: 0,
      limit: ITEMS_PER_PAGE,
    });
  };

  const handlePageChange = (newPage: number) => {
    setFilters({
      ...filters,
      skip: (newPage - 1) * ITEMS_PER_PAGE,
    });
  };

  const handleViewDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailsOpen(true);
  };

  const handleExportCSV = () => {
    // Create CSV content
    const headers = ['Timestamp', 'Username', 'IP Address', 'Feature', 'Action', 'Success', 'Details'];
    const rows = logs.map(log => [
      log.timestamp,
      log.username,
      log.ip_address || 'N/A',
      log.feature,
      log.action,
      log.success ? 'Yes' : 'No',
      log.details ? JSON.stringify(log.details) : '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);

    toast({
      title: 'Success',
      description: 'Audit logs exported to CSV',
    });
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Trail</h1>
        <p className="text-muted-foreground mt-2">
          View and filter application audit logs
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Filter audit logs by criteria</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Username</label>
              <Input
                placeholder="Filter by username"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Feature</label>
              <Input
                placeholder="Filter by feature"
                value={searchFeature}
                onChange={(e) => setSearchFeature(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Action</label>
              <Input
                placeholder="Filter by action"
                value={searchAction}
                onChange={(e) => setSearchAction(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Success</label>
              <Select value={successFilter} onValueChange={setSuccessFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="true">Success Only</SelectItem>
                  <SelectItem value="false">Failures Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleApplyFilters} className="gap-2">
              <Search className="h-4 w-4" />
              Apply Filters
            </Button>
            <Button onClick={handleClearFilters} variant="outline">
              Clear Filters
            </Button>
            <Button onClick={handleExportCSV} variant="outline" className="ml-auto gap-2">
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Logs</CardTitle>
          <CardDescription>
            Showing {logs.length} of {total} log entries
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No audit logs found</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Username</TableHead>
                    <TableHead>IP Address</TableHead>
                    <TableHead>Feature</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-xs">
                        {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                      </TableCell>
                      <TableCell>{log.username}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {log.ip_address || 'N/A'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{log.feature}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{log.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={log.success ? 'default' : 'destructive'}>
                          {log.success ? 'Success' : 'Failed'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetails(log)}
                          >
                            View
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit Log Details</DialogTitle>
            <DialogDescription>
              {selectedLog && format(new Date(selectedLog.timestamp), 'PPpp')}
            </DialogDescription>
          </DialogHeader>
          {selectedLog && selectedLog.details && (
            <div className="space-y-2">
              <pre className="bg-muted p-4 rounded-md overflow-auto max-h-96 text-xs">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
