import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import FilePreviewDialog from '@/components/preview/file-preview-dialog';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import MarkdownViewer from '@/components/ui/markdown-viewer';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, Edit3, LinkIcon, Paperclip, FileText, Users, Tag, Hash, CalendarDays, UserCircle, ListTree, ChevronsUpDown, Plus, RefreshCcw, Eye, Trash2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DataDomain } from '@/types/data-domain';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { RelativeDate } from '@/components/common/relative-date';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, AlertCircle } from 'lucide-react';
import { DataDomainMiniGraph } from '@/components/data-domains/data-domain-mini-graph';

// Helper to check API response (can be moved to a shared util if used in many places)
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string | null | undefined }, name: string): T => {
    if (response.error) throw new Error(`${name} fetch failed: ${response.error}`);
    if (response.data && typeof response.data === 'object' && response.data !== null && 'detail' in response.data && typeof (response.data as { detail: string }).detail === 'string') {
        throw new Error(`${name} fetch failed: ${(response.data as { detail: string }).detail}`);
    }
    if (response.data === null || response.data === undefined) throw new Error(`${name} fetch returned null or undefined data.`);
    return response.data as T;
};

interface InfoItemProps {
  label: string;
  icon?: React.ReactNode;
  value?: string | React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

const InfoItem: React.FC<InfoItemProps> = ({ label, value, icon, children, className }) => (
  <div className={`mb-3 ${className}`}>
    <p className="text-sm font-medium text-muted-foreground flex items-center">
      {icon && React.cloneElement(icon as React.ReactElement, { className: 'mr-2 h-4 w-4' })}
      {label}
    </p>
    {value && <p className="text-md text-foreground mt-0.5">{value}</p>}
    {children && <div className="mt-0.5">{children}</div>}
  </div>
);

export default function DataDomainDetailsView() {
  const { domainId } = useParams<{ domainId: string }>();
  const navigate = useNavigate();
  const { get } = useApi();
  const { toast } = useToast();
  
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  const [domain, setDomain] = useState<DataDomain | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Metadata: Rich Texts, Links, Documents
  interface RichTextItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; content_markdown: string; created_at?: string; }
  interface LinkItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; url: string; created_at?: string; }
  interface DocumentItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; original_filename: string; content_type?: string | null; size_bytes?: number | null; storage_path: string; created_at?: string; }

  const [richTexts, setRichTexts] = useState<RichTextItem[]>([]);
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  const [addingNote, setAddingNote] = useState(false);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteDesc, setNoteDesc] = useState('');
  const [noteContent, setNoteContent] = useState('');

  const [addingLink, setAddingLink] = useState(false);
  const [linkTitle, setLinkTitle] = useState('');
  const [linkDesc, setLinkDesc] = useState('');
  const [linkUrl, setLinkUrl] = useState('');

  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [addingDoc, setAddingDoc] = useState(false);
  const [docTitle, setDocTitle] = useState('');
  const [docDesc, setDocDesc] = useState('');
  const [docFile, setDocFile] = useState<File | null>(null);

  const fetchDomainDetails = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    setDynamicTitle('Loading...');
    try {
      const response = await get<DataDomain>(`/api/data-domains/${id}`);
      const data = checkApiResponse(response, 'Data Domain Details');
      setDomain(data);
      setDynamicTitle(data.name);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch domain details.');
      toast({
        title: 'Error Fetching Domain',
        description: err.message || 'Could not load domain details.',
        variant: 'destructive',
      });
      setDomain(null);
      setDynamicTitle('Error');
    }
    setIsLoading(false);
  }, [get, toast, setDynamicTitle]);

  const entityType = 'data_domain';

  const truncate = (text?: string | null, maxLen: number = 80) => {
    if (!text) return '';
    return text.length > maxLen ? text.slice(0, maxLen - 1) + '…' : text;
  };

  // Preview dialogs
  const [previewNote, setPreviewNote] = useState<RichTextItem | null>(null);
  const [previewLink, setPreviewLink] = useState<LinkItem | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [docPreviewUrl, setDocPreviewUrl] = useState<string | undefined>(undefined);

  const fetchMetadata = useCallback(async (id: string) => {
    try {
      const [rtResp, liResp, docResp] = await Promise.all([
        get<RichTextItem[]>(`/api/entities/${entityType}/${id}/rich-texts`),
        get<LinkItem[]>(`/api/entities/${entityType}/${id}/links`),
        get<DocumentItem[]>(`/api/entities/${entityType}/${id}/documents`),
      ]);
      setRichTexts(checkApiResponse(rtResp, 'Rich Texts'));
      setLinks(checkApiResponse(liResp, 'Links'));
      setDocuments(checkApiResponse(docResp, 'Documents'));
    } catch (err: any) {
      toast({ title: 'Metadata load failed', description: err.message || 'Could not load metadata.', variant: 'destructive' });
    }
  }, [get, toast]);

  useEffect(() => {
    setStaticSegments([{ label: 'Data Domains', path: '/data-domains' }]);
    if (domainId) {
      fetchDomainDetails(domainId);
      fetchMetadata(domainId);
    } else {
      setError("No Domain ID provided.");
      setDynamicTitle("Invalid Domain");
      setIsLoading(false);
    }
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [domainId, fetchDomainDetails, fetchMetadata, setStaticSegments, setDynamicTitle]);

  useEffect(() => {
    if (domain) {
      setDynamicTitle(domain.name);
    }
  }, [domain, setDynamicTitle]);

  if (isLoading) {
    return (
        <div className="flex justify-center items-center h-[calc(100vh-200px)]">
            <Loader2 className="h-16 w-16 animate-spin text-primary" />
        </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-10">
        <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button variant="outline" onClick={() => navigate('/data-domains')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Data Domains
        </Button>
      </div>
    );
  }

  if (!domain) {
    return (
        <div className="container mx-auto py-10 text-center">
            <Alert className="mb-4">
                <AlertDescription>Data domain not found or could not be loaded.</AlertDescription>
            </Alert>
            <Button variant="outline" onClick={() => navigate('/data-domains')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back to Data Domains
            </Button>
        </div>
    );
  }

  return (
    <div className="py-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-domains')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <Button variant="outline" size="sm" onClick={() => alert('Edit Domain functionality to be implemented for this page')}>
            <Edit3 className="mr-2 h-4 w-4" /> Edit Domain
        </Button>
      </div>

      <Card>
        <CardHeader>
            <CardTitle className="text-2xl font-bold flex items-center">
                <ListTree className="mr-3 h-7 w-7 text-primary" />{domain.name}
            </CardTitle>
            {domain.description && <CardDescription className="pt-1">{domain.description}</CardDescription>}
        </CardHeader>
        <CardContent className="pt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
            <InfoItem label="ID" value={domain.id} icon={<Hash />} className="lg:col-span-1 md:col-span-2" />
            
            {domain.parent_info && (
              <InfoItem label="Parent Domain" icon={<ListTree />}>
                <Link to={`/data-domains/${domain.parent_info.id}`} className="text-primary hover:underline">
                  {domain.parent_info.name}
                </Link>
              </InfoItem>
            )}
             <InfoItem label="Children Count" value={domain.children_count?.toString() ?? '0'} icon={<ListTree />} />

            <InfoItem label="Owners" icon={<Users />}>
              {domain.owner && domain.owner.length > 0 ? (
                <div className="flex flex-wrap gap-1 mt-1">
                  {domain.owner.map((o, i) => <Badge key={i} variant="outline">{o}</Badge>)}
                </div>
              ) : 'N/A'}
            </InfoItem>

            <InfoItem label="Tags" icon={<Tag />}>
              {domain.tags && domain.tags.length > 0 ? (
                <div className="flex flex-wrap gap-1 mt-1">
                  {domain.tags.map((t, i) => <Badge key={i} variant="secondary">{t}</Badge>)}
                </div>
              ) : 'N/A'}
            </InfoItem>
           
            <InfoItem label="Created By" value={domain.created_by || 'N/A'} icon={<UserCircle />} />
            <InfoItem label="Created At" icon={<CalendarDays />}>
                {domain.created_at ? <RelativeDate date={domain.created_at} /> : 'N/A'}
            </InfoItem>
            <InfoItem label="Last Updated At" icon={<CalendarDays />}>
                {domain.updated_at ? <RelativeDate date={domain.updated_at} /> : 'N/A'}
            </InfoItem>
        </CardContent>
      </Card>

      <Separator />

      {/* Domain Hierarchy above metadata */}
      {(domain.parent_info || (domain.children_info && domain.children_info.length > 0)) && (
        <Card className="mb-6">
          <CardHeader className='pb-2'>
            <CardTitle className="text-lg font-semibold flex items-center">
              <ChevronsUpDown className="h-5 w-5 mr-2 text-primary" />
              Domain Hierarchy Context
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataDomainMiniGraph currentDomain={domain} />
          </CardContent>
        </Card>
      )}

      {/* Unified Metadata Card (full width) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Metadata</CardTitle>
          <CardDescription>Notes, links, and attachments related to this domain.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Notes Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="text-base font-medium flex items-center"><FileText className="mr-2 h-5 w-5 text-primary" />Additional Notes</div>
              <TooltipProvider>
                <div className="flex items-center gap-1 border rounded-md bg-muted/40 px-1 py-0.5">
                  {!addingNote && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" onClick={() => setAddingNote(true)}>
                          <Plus className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Add</TooltipContent>
                    </Tooltip>
                  )}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" onClick={() => domainId && fetchMetadata(domainId)}>
                        <RefreshCcw className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Refresh</TooltipContent>
                  </Tooltip>
                </div>
              </TooltipProvider>
            </div>
            {!addingNote ? (
              <div>
                {richTexts.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No notes yet.</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead>Updated</TableHead>
                        <TableHead className="w-24">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {richTexts.map(n => (
                        <TableRow key={n.id}>
                          <TableCell className="font-medium">{n.title}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{truncate(n.short_description, 80)}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{n.created_at ? <RelativeDate date={n.created_at} /> : '—'}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{'—'}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button variant="ghost" size="icon" onClick={() => setPreviewNote(n)}>
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Preview</TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                                try {
                                  const resp = await fetch(`/api/rich-texts/${n.id}`, { method: 'DELETE' });
                                  if (!resp.ok) throw new Error('Delete failed');
                                  if (domainId) fetchMetadata(domainId);
                                } catch (e: any) {
                                  toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
                                }
                              }}>
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div>
                  <Label htmlFor="note-title">Title</Label>
                  <Input id="note-title" value={noteTitle} onChange={e => setNoteTitle(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="note-desc">Short Description</Label>
                  <Input id="note-desc" value={noteDesc} onChange={e => setNoteDesc(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="note-content">Content (Markdown)</Label>
                  <Textarea id="note-content" rows={6} value={noteContent} onChange={e => setNoteContent(e.target.value)} />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={async () => {
                    try {
                      if (!domainId) return;
                      const payload = {
                        entity_id: domainId,
                        entity_type: entityType,
                        title: noteTitle,
                        short_description: noteDesc || undefined,
                        content_markdown: noteContent,
                      };
                      const resp = await fetch(`/api/entities/${entityType}/${domainId}/rich-texts`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                      });
                      if (!resp.ok) throw new Error(await resp.text());
                      setNoteTitle(''); setNoteDesc(''); setNoteContent(''); setAddingNote(false);
                      fetchMetadata(domainId);
                    } catch (e: any) {
                      toast({ title: 'Add note failed', description: e.message, variant: 'destructive' });
                    }
                  }}>Save</Button>
                  <Button size="sm" variant="outline" onClick={() => { setAddingNote(false); }}>Cancel</Button>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Links Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="text-base font-medium flex items-center"><LinkIcon className="mr-2 h-5 w-5 text-primary" />Related Links</div>
              <TooltipProvider>
                <div className="flex items-center gap-1 border rounded-md bg-muted/40 px-1 py-0.5">
                  {!addingLink && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" onClick={() => setAddingLink(true)}>
                          <Plus className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Add</TooltipContent>
                    </Tooltip>
                  )}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" onClick={() => domainId && fetchMetadata(domainId)}>
                        <RefreshCcw className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Refresh</TooltipContent>
                  </Tooltip>
                </div>
              </TooltipProvider>
            </div>
            {!addingLink ? (
              <div>
                {links.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No links yet.</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>URL</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="w-24">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {links.map(l => (
                        <TableRow key={l.id}>
                          <TableCell className="font-medium">{l.title}</TableCell>
                          <TableCell className="text-xs text-primary max-w-[240px] truncate"><a href={l.url} target="_blank" rel="noreferrer" className="hover:underline">{l.url}</a></TableCell>
                          <TableCell className="text-xs text-muted-foreground">{truncate(l.short_description, 80)}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{l.created_at ? <RelativeDate date={l.created_at} /> : '—'}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button variant="ghost" size="icon" onClick={() => setPreviewLink(l)}>
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Preview</TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                                try {
                                  const resp = await fetch(`/api/links/${l.id}`, { method: 'DELETE' });
                                  if (!resp.ok) throw new Error('Delete failed');
                                  if (domainId) fetchMetadata(domainId);
                                } catch (e: any) {
                                  toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
                                }
                              }}>
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div>
                  <Label htmlFor="link-title">Title</Label>
                  <Input id="link-title" value={linkTitle} onChange={e => setLinkTitle(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="link-url">URL</Label>
                  <Input id="link-url" value={linkUrl} onChange={e => setLinkUrl(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="link-desc">Short Description</Label>
                  <Input id="link-desc" value={linkDesc} onChange={e => setLinkDesc(e.target.value)} />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={async () => {
                    try {
                      if (!domainId) return;
                      const payload = {
                        entity_id: domainId,
                        entity_type: entityType,
                        title: linkTitle,
                        short_description: linkDesc || undefined,
                        url: linkUrl,
                      };
                      const resp = await fetch(`/api/entities/${entityType}/${domainId}/links`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                      });
                      if (!resp.ok) throw new Error(await resp.text());
                      setLinkTitle(''); setLinkDesc(''); setLinkUrl(''); setAddingLink(false);
                      fetchMetadata(domainId);
                    } catch (e: any) {
                      toast({ title: 'Add link failed', description: e.message, variant: 'destructive' });
                    }
                  }}>Save</Button>
                  <Button size="sm" variant="outline" onClick={() => { setAddingLink(false); }}>Cancel</Button>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Documents Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="text-base font-medium flex items-center"><Paperclip className="mr-2 h-5 w-5 text-primary" />Attached Documents</div>
              <TooltipProvider>
                <div className="flex items-center gap-1 border rounded-md bg-muted/40 px-1 py-0.5">
                  {!addingDoc && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" onClick={() => setAddingDoc(true)}>
                          <Plus className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Add</TooltipContent>
                    </Tooltip>
                  )}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" onClick={() => domainId && fetchMetadata(domainId)}>
                        <RefreshCcw className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Refresh</TooltipContent>
                  </Tooltip>
                </div>
              </TooltipProvider>
            </div>
            {addingDoc && (
              <div className="space-y-2 mb-3">
              <div>
                <Label htmlFor="doc-title">Title</Label>
                <Input id="doc-title" value={docTitle} onChange={e => setDocTitle(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="doc-desc">Short Description</Label>
                <Input id="doc-desc" value={docDesc} onChange={e => setDocDesc(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="doc-file">File</Label>
                <Input id="doc-file" type="file" onChange={e => setDocFile(e.target.files?.[0] || null)} />
              </div>
              <div className="flex gap-2">
              <Button size="sm" disabled={uploadingDoc || !docFile || !docTitle} onClick={async () => {
                try {
                  if (!domainId || !docFile) return;
                  setUploadingDoc(true);
                  const form = new FormData();
                  form.append('title', docTitle);
                  if (docDesc) form.append('short_description', docDesc);
                  form.append('file', docFile);
                  const resp = await fetch(`/api/entities/${entityType}/${domainId}/documents`, {
                    method: 'POST',
                    body: form,
                  });
                  if (!resp.ok) throw new Error(await resp.text());
                  setDocTitle(''); setDocDesc(''); setDocFile(null); setUploadingDoc(false);
                  setAddingDoc(false);
                  fetchMetadata(domainId);
                } catch (e: any) {
                  setUploadingDoc(false);
                  toast({ title: 'Upload failed', description: e.message, variant: 'destructive' });
                }
              }}>Upload</Button>
              <Button size="sm" variant="outline" onClick={() => { setAddingDoc(false); }}>Cancel</Button>
              </div>
              </div>
            )}
            {documents.length === 0 ? (
              <div className="text-sm text-muted-foreground">No documents uploaded.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Filename</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map(d => (
                    <TableRow key={d.id}>
                      <TableCell className="font-medium">{d.title}</TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[240px]">{d.original_filename}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{truncate(d.short_description, 80)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{d.size_bytes ? `${(d.size_bytes/1024).toFixed(1)} KB` : '—'}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{d.created_at ? <RelativeDate date={d.created_at} /> : '—'}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button variant="ghost" size="icon" onClick={() => { setDocPreviewUrl(undefined); setPreviewDoc(d); }}>
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Preview</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                            try {
                              const resp = await fetch(`/api/documents/${d.id}`, { method: 'DELETE' });
                              if (!resp.ok) throw new Error('Delete failed');
                              if (domainId) fetchMetadata(domainId);
                            } catch (e: any) {
                              toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
                            }
                          }}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Preview Dialogs */}
      <Dialog open={!!previewNote} onOpenChange={() => setPreviewNote(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{previewNote?.title}</DialogTitle>
          </DialogHeader>
          {previewNote && (
            <div className="space-y-2">
              {previewNote.short_description && <div className="text-sm text-muted-foreground">{previewNote.short_description}</div>}
              <MarkdownViewer markdown={previewNote.content_markdown} />
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!previewLink} onOpenChange={() => setPreviewLink(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{previewLink?.title}</DialogTitle>
          </DialogHeader>
          {previewLink && (
            <div className="space-y-2">
              <a className="text-primary underline" href={previewLink.url} target="_blank" rel="noreferrer">{previewLink.url}</a>
              {previewLink.short_description && <div className="text-sm text-muted-foreground">{previewLink.short_description}</div>}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <FilePreviewDialog
        open={!!previewDoc}
        onOpenChange={(open) => { if (!open) setPreviewDoc(null); }}
        source={previewDoc ? {
          title: previewDoc.title,
          contentType: previewDoc.content_type,
          storagePath: previewDoc.storage_path,
          originalFilename: previewDoc.original_filename,
          downloadUrl: docPreviewUrl,
        } : null}
        fetchUrl={previewDoc ? (async () => {
          try {
            const resp = await fetch(`/api/documents/${previewDoc.id}/content`);
            if (!resp.ok) return undefined;
            // Create a blob URL for the streamed content
            const blob = await resp.blob();
            return URL.createObjectURL(blob);
          } catch {
            return undefined;
          }
        }) : null}
      />

      {/* Mini Graph Display (removed duplicate; displayed above in a single instance) */}

      {domain.children_count !== undefined && domain.children_count > 0 && (
        <>
            <Separator />
            <Card>
                <CardHeader>
                    <CardTitle className="text-xl flex items-center"><ListTree className="mr-2 h-5 w-5 text-primary"/>Child Data Domains ({domain.children_count})</CardTitle>
                    <CardDescription>Directly nested data domains.</CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">Listing child domains with links to their details pages will be implemented here. This might require fetching child details or having them partially included in the parent's API response.</p>
                    {/* Placeholder: Fetch and list child domains here */}
                    {/* Example: 
                        <ul>
                            {childDomains.map(child => (
                                <li key={child.id}><Link to={`/data-domains/${child.id}`}>{child.name}</Link></li>
                            ))}
                        </ul>
                    */}
                </CardContent>
            </Card>
        </>
      )}

    </div>
  );
} 