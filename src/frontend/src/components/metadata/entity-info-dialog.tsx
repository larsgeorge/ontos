import React, { useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import MarkdownViewer from '@/components/ui/markdown-viewer';
import { useEntityMetadata, DocumentItem, LinkItem, EntityKind } from '@/hooks/use-entity-metadata';

interface Props {
  entityType: EntityKind;
  entityId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
}

// Replace image references in markdown to target our document content endpoint.
// Supports: ![alt](doc:ID) or ![alt](file:filename.ext)
function rewriteImageLinks(markdown: string, documents: DocumentItem[]): string {
  if (!markdown) return markdown;

  const byId = new Map(documents.map(d => [String(d.id), d]));
  const byName = new Map(documents.map(d => [d.original_filename, d]));

  const replaceUrl = (url: string): string => {
    if (url.startsWith('doc:')) {
      const id = url.slice(4);
      if (byId.has(id)) return `/api/documents/${id}/content`;
    }
    if (url.startsWith('file:')) {
      const name = url.slice(5);
      const doc = byName.get(name);
      if (doc) return `/api/documents/${doc.id}/content`;
    }
    return url;
  };

  let out = markdown.replace(/!\[[^\]]*\]\(([^)]+)\)/g, (m, p1) => m.replace(p1, replaceUrl(p1)));
  out = out.replace(/\[[^\]]*\]\(([^)]+)\)/g, (m, p1) => m.replace(p1, replaceUrl(p1)));
  return out;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

function buildToc(markdown: string) {
  const lines = markdown.split(/\r?\n/);
  const headings: { level: number; text: string; id: string }[] = [];
  for (const line of lines) {
    const m = /^(#{1,6})\s+(.*)$/.exec(line);
    if (m) {
      const level = m[1].length;
      const text = m[2].trim();
      const id = slugify(text);
      headings.push({ level, text, id });
    }
  }
  return headings;
}

export default function EntityInfoDialog({ entityType, entityId, open, onOpenChange, title }: Props) {
  const { richTexts, documents, links, loading, error } = useEntityMetadata(entityType, entityId || undefined);

  const concatenatedMarkdown = useMemo(() => {
    const divider = '\n\n---\n\n';
    const raw = richTexts.map(rt => `# ${rt.title}\n\n${rt.short_description ? `_${rt.short_description}_\n\n` : ''}${rt.content_markdown}`).join(divider);
    const withImages = rewriteImageLinks(raw, documents);
    return withImages;
  }, [richTexts, documents]);

  const toc = useMemo(() => buildToc(concatenatedMarkdown), [concatenatedMarkdown]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl h-[80vh] overflow-y-auto sm:top-10 sm:-translate-y-0">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-xl">
            <span className="font-semibold">{title || 'Entity Information'}</span>
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="text-muted-foreground">Loading...</div>
        ) : error ? (
          <div className="text-destructive">{error}</div>
        ) : (
          <div className="space-y-6">
            {toc.length > 0 && (
              <div className="rounded-lg border bg-muted/20 p-4">
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Table of contents</div>
                <ul className="text-sm space-y-1">
                  {toc.map((h, idx) => (
                    <li key={idx}>
                      <a href={`#${h.id}`} className="hover:underline inline-block" style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>{h.text}</a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {concatenatedMarkdown ? (
              <div className="prose dark:prose-invert max-w-none">
                <MarkdownViewer markdown={concatenatedMarkdown} />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No notes available.</div>
            )}

            <Separator />

            <div>
              <div className="text-base font-medium mb-2">Related Links</div>
              {links.length === 0 ? (
                <div className="text-sm text-muted-foreground">No links.</div>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr className="text-left">
                        <th className="py-2 px-3">Title</th>
                        <th className="py-2 px-3">URL</th>
                        <th className="py-2 px-3">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {links.map((l: LinkItem) => (
                        <tr key={l.id} className="border-t">
                          <td className="py-2 px-3 whitespace-nowrap">{l.title}</td>
                          <td className="py-2 px-3 max-w-[420px] truncate"><a className="text-primary hover:underline" href={l.url} target="_blank" rel="noreferrer">{l.url}</a></td>
                          <td className="py-2 px-3 text-muted-foreground">{l.short_description || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}


