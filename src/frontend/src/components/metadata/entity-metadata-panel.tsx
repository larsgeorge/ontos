import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { RelativeDate } from '@/components/common/relative-date';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Plus, RefreshCcw, Eye, Trash2, FileText, LinkIcon, Paperclip, Pencil } from 'lucide-react';
import FilePreviewDialog from '@/components/preview/file-preview-dialog';
import { useToast } from '@/hooks/use-toast';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import MarkdownViewer from '@/components/ui/markdown-viewer';
import EntityInfoDialog from '@/components/metadata/entity-info-dialog';

export type EntityKind = 'data_domain' | 'data_product' | 'data_contract';

interface RichTextItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; content_markdown: string; created_at?: string; }
interface LinkItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; url: string; created_at?: string; }
interface DocumentItem { id: string; entity_id: string; entity_type: string; title: string; short_description?: string | null; original_filename: string; content_type?: string | null; size_bytes?: number | null; storage_path: string; created_at?: string; }

interface Props {
  entityId: string;
  entityType: EntityKind;
}

const EntityMetadataPanel: React.FC<Props> = ({ entityId, entityType }) => {
  const { toast } = useToast();

  const [richTexts, setRichTexts] = React.useState<RichTextItem[]>([]);
  const [links, setLinks] = React.useState<LinkItem[]>([]);
  const [documents, setDocuments] = React.useState<DocumentItem[]>([]);

  const [addingNote, setAddingNote] = React.useState(false);
  const [noteTitle, setNoteTitle] = React.useState('');
  const [noteDesc, setNoteDesc] = React.useState('');
  const [noteContent, setNoteContent] = React.useState('');

  const [addingLink, setAddingLink] = React.useState(false);
  const [linkTitle, setLinkTitle] = React.useState('');
  const [linkDesc, setLinkDesc] = React.useState('');
  const [linkUrl, setLinkUrl] = React.useState('');

  const [addingDoc, setAddingDoc] = React.useState(false);
  const [docTitle, setDocTitle] = React.useState('');
  const [docDesc, setDocDesc] = React.useState('');
  const [docFile, setDocFile] = React.useState<File | null>(null);
  const [uploadingDoc, setUploadingDoc] = React.useState(false);

  const [previewDoc, setPreviewDoc] = React.useState<DocumentItem | null>(null);
  const [previewNote, setPreviewNote] = React.useState<RichTextItem | null>(null);
  const [showPreview, setShowPreview] = React.useState(false);

  // Editing states for notes
  const [editingNote, setEditingNote] = React.useState<RichTextItem | null>(null);
  const [editNoteTitle, setEditNoteTitle] = React.useState('');
  const [editNoteDesc, setEditNoteDesc] = React.useState('');
  const [editNoteContent, setEditNoteContent] = React.useState('');
  
  // Editing states for links
  const [editingLink, setEditingLink] = React.useState<LinkItem | null>(null);
  const [editLinkTitle, setEditLinkTitle] = React.useState('');
  const [editLinkUrl, setEditLinkUrl] = React.useState('');
  const [editLinkDesc, setEditLinkDesc] = React.useState('');

  const fetchMetadata = React.useCallback(async () => {
    try {
      const [rt, li, docs] = await Promise.all([
        fetch(`/api/entities/${entityType}/${entityId}/rich-texts`).then(r => r.json()),
        fetch(`/api/entities/${entityType}/${entityId}/links`).then(r => r.json()),
        fetch(`/api/entities/${entityType}/${entityId}/documents`).then(r => r.json()),
      ]);
      setRichTexts(Array.isArray(rt) ? rt : []);
      setLinks(Array.isArray(li) ? li : []);
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (e: any) {
      toast({ title: 'Metadata load failed', description: e.message, variant: 'destructive' });
    }
  }, [entityId, entityType, toast]);

  React.useEffect(() => { fetchMetadata(); }, [fetchMetadata]);

  const truncate = (text?: string | null, maxLen: number = 80) => {
    if (!text) return '';
    return text.length > maxLen ? text.slice(0, maxLen - 1) + '…' : text;
  };

  return (
    <>
    <Card>
      <CardHeader>
        <CardTitle className="text-xl flex items-center gap-2">
          Metadata
          {entityType === 'data_product' && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={() => setShowPreview(true)}>
                    <Eye className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Preview rendered page</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </CardTitle>
        <CardDescription>Notes, links, and attachments.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Notes */}
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
                    <Button variant="ghost" size="icon" onClick={fetchMetadata}>
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
                      <TableHead className="w-24">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {richTexts.map(n => (
                      <TableRow key={n.id}>
                        <TableCell className="font-medium">{n.title}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{truncate(n.short_description, 80)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{n.created_at ? <RelativeDate date={n.created_at} /> : '—'}</TableCell>
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
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" onClick={() => { setEditingNote(n); setEditNoteTitle(n.title); setEditNoteDesc(n.short_description || ''); setEditNoteContent(n.content_markdown); }}>
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Edit</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                              try {
                                const resp = await fetch(`/api/rich-texts/${n.id}`, { method: 'DELETE' });
                                if (!resp.ok) throw new Error('Delete failed');
                                fetchMetadata();
                              } catch (e: any) { toast({ title: 'Delete failed', description: e.message, variant: 'destructive' }); }
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
              <div><Label htmlFor="note-title">Title</Label><Input id="note-title" value={noteTitle} onChange={e => setNoteTitle(e.target.value)} /></div>
              <div><Label htmlFor="note-desc">Short Description</Label><Input id="note-desc" value={noteDesc} onChange={e => setNoteDesc(e.target.value)} /></div>
              <div><Label htmlFor="note-content">Content (Markdown)</Label><Textarea id="note-content" rows={6} value={noteContent} onChange={e => setNoteContent(e.target.value)} /></div>
              <div className="flex gap-2">
                <Button size="sm" onClick={async () => {
                  try {
                    const payload = { entity_id: entityId, entity_type: entityType, title: noteTitle, short_description: noteDesc || undefined, content_markdown: noteContent };
                    const resp = await fetch(`/api/entities/${entityType}/${entityId}/rich-texts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                    if (!resp.ok) throw new Error(await resp.text());
                    setNoteTitle(''); setNoteDesc(''); setNoteContent(''); setAddingNote(false);
                    fetchMetadata();
                  } catch (e: any) { toast({ title: 'Add note failed', description: e.message, variant: 'destructive' }); }
                }}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => setAddingNote(false)}>Cancel</Button>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Links */}
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
                    <Button variant="ghost" size="icon" onClick={fetchMetadata}>
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
                                  <Button variant="ghost" size="icon" onClick={() => window.open(l.url, '_blank')}>
                                    <Eye className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Open</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" onClick={() => { setEditingLink(l); setEditLinkTitle(l.title); setEditLinkUrl(l.url); setEditLinkDesc(l.short_description || ''); }}>
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Edit</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                              try {
                                const resp = await fetch(`/api/links/${l.id}`, { method: 'DELETE' });
                                if (!resp.ok) throw new Error('Delete failed');
                                fetchMetadata();
                              } catch (e: any) { toast({ title: 'Delete failed', description: e.message, variant: 'destructive' }); }
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
              <div><Label htmlFor="link-title">Title</Label><Input id="link-title" value={linkTitle} onChange={e => setLinkTitle(e.target.value)} /></div>
              <div><Label htmlFor="link-url">URL</Label><Input id="link-url" value={linkUrl} onChange={e => setLinkUrl(e.target.value)} /></div>
              <div><Label htmlFor="link-desc">Short Description</Label><Input id="link-desc" value={linkDesc} onChange={e => setLinkDesc(e.target.value)} /></div>
              <div className="flex gap-2">
                <Button size="sm" onClick={async () => {
                  try {
                    const payload = { entity_id: entityId, entity_type: entityType, title: linkTitle, short_description: linkDesc || undefined, url: linkUrl };
                    const resp = await fetch(`/api/entities/${entityType}/${entityId}/links`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                    if (!resp.ok) throw new Error(await resp.text());
                    setLinkTitle(''); setLinkDesc(''); setLinkUrl(''); setAddingLink(false);
                    fetchMetadata();
                  } catch (e: any) { toast({ title: 'Add link failed', description: e.message, variant: 'destructive' }); }
                }}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => setAddingLink(false)}>Cancel</Button>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Documents */}
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
                    <Button variant="ghost" size="icon" onClick={fetchMetadata}>
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
              <div><Label htmlFor="doc-title">Title</Label><Input id="doc-title" value={docTitle} onChange={e => setDocTitle(e.target.value)} /></div>
              <div><Label htmlFor="doc-desc">Short Description</Label><Input id="doc-desc" value={docDesc} onChange={e => setDocDesc(e.target.value)} /></div>
              <div><Label htmlFor="doc-file">File</Label><Input id="doc-file" type="file" onChange={e => setDocFile(e.target.files?.[0] || null)} /></div>
              <div className="flex gap-2">
                <Button size="sm" disabled={uploadingDoc || !docFile || !docTitle} onClick={async () => {
                  try {
                    if (!docFile) return;
                    setUploadingDoc(true);
                    const form = new FormData();
                    form.append('title', docTitle);
                    if (docDesc) form.append('short_description', docDesc);
                    form.append('file', docFile);
                    const resp = await fetch(`/api/entities/${entityType}/${entityId}/documents`, { method: 'POST', body: form });
                    if (!resp.ok) throw new Error(await resp.text());
                    setDocTitle(''); setDocDesc(''); setDocFile(null); setUploadingDoc(false); setAddingDoc(false);
                    fetchMetadata();
                  } catch (e: any) { setUploadingDoc(false); toast({ title: 'Upload failed', description: e.message, variant: 'destructive' }); }
                }}>Upload</Button>
                <Button size="sm" variant="outline" onClick={() => setAddingDoc(false)}>Cancel</Button>
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
                              <Button variant="ghost" size="icon" onClick={() => setPreviewDoc(d)}>
                                <Eye className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Preview</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={async () => {
                          try { const resp = await fetch(`/api/documents/${d.id}`, { method: 'DELETE' }); if (!resp.ok) throw new Error('Delete failed'); fetchMetadata(); }
                          catch (e: any) { toast({ title: 'Delete failed', description: e.message, variant: 'destructive' }); }
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

        <FilePreviewDialog
          open={!!previewDoc}
          onOpenChange={(open) => { if (!open) setPreviewDoc(null); }}
          source={previewDoc ? {
            title: previewDoc.title,
            contentType: previewDoc.content_type,
            storagePath: previewDoc.storage_path,
            originalFilename: previewDoc.original_filename,
          } : null}
          fetchUrl={previewDoc ? (async () => {
            try {
              const resp = await fetch(`/api/documents/${previewDoc.id}/content`);
              if (!resp.ok) return undefined;
              const blob = await resp.blob();
              return URL.createObjectURL(blob);
            } catch { return undefined; }
          }) : null}
        />

        {/* Note Preview */}
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

        {/* Note Edit Dialog */}
        <Dialog open={!!editingNote} onOpenChange={(open) => { if (!open) setEditingNote(null); }}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit note</DialogTitle>
            </DialogHeader>
            {editingNote && (
              <div className="space-y-3">
                <div>
                  <Label htmlFor="edit-note-title">Title</Label>
                  <Input id="edit-note-title" value={editNoteTitle} onChange={(e) => setEditNoteTitle(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="edit-note-desc">Short Description</Label>
                  <Input id="edit-note-desc" value={editNoteDesc} onChange={(e) => setEditNoteDesc(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="edit-note-content">Content (Markdown)</Label>
                  <Textarea id="edit-note-content" rows={8} value={editNoteContent} onChange={(e) => setEditNoteContent(e.target.value)} />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" onClick={() => setEditingNote(null)}>Cancel</Button>
                  <Button
                    onClick={async () => {
                      try {
                        const payload = {
                          title: editNoteTitle || undefined,
                          short_description: editNoteDesc || undefined,
                          content_markdown: editNoteContent || undefined,
                        };
                        const resp = await fetch(`/api/rich-texts/${editingNote.id}`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(payload),
                        });
                        if (!resp.ok) throw new Error(await resp.text());
                        setEditingNote(null);
                        fetchMetadata();
                      } catch (e: any) {
                        toast({ title: 'Update failed', description: e.message, variant: 'destructive' });
                      }
                    }}
                    disabled={!editNoteTitle}
                  >Save</Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Link Edit Dialog */}
        <Dialog open={!!editingLink} onOpenChange={(open) => { if (!open) setEditingLink(null); }}>
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <DialogTitle>Edit link</DialogTitle>
            </DialogHeader>
            {editingLink && (
              <div className="space-y-3">
                <div>
                  <Label htmlFor="edit-link-title">Title</Label>
                  <Input id="edit-link-title" value={editLinkTitle} onChange={(e) => setEditLinkTitle(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="edit-link-url">URL</Label>
                  <Input id="edit-link-url" value={editLinkUrl} onChange={(e) => setEditLinkUrl(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="edit-link-desc">Short Description</Label>
                  <Input id="edit-link-desc" value={editLinkDesc} onChange={(e) => setEditLinkDesc(e.target.value)} />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" onClick={() => setEditingLink(null)}>Cancel</Button>
                  <Button
                    onClick={async () => {
                      try {
                        const payload = {
                          title: editLinkTitle || undefined,
                          url: editLinkUrl || undefined,
                          short_description: editLinkDesc || undefined,
                        };
                        const resp = await fetch(`/api/links/${editingLink.id}`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(payload),
                        });
                        if (!resp.ok) throw new Error(await resp.text());
                        setEditingLink(null);
                        fetchMetadata();
                      } catch (e: any) {
                        toast({ title: 'Update failed', description: e.message, variant: 'destructive' });
                      }
                    }}
                    disabled={!editLinkTitle || !editLinkUrl}
                  >Save</Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
    {entityType === 'data_product' && (
      <EntityInfoDialog
        entityType={'data_product'}
        entityId={entityId}
        title={undefined}
        open={showPreview}
        onOpenChange={setShowPreview}
      />
    )}
  </>
  );
};

export default EntityMetadataPanel;


