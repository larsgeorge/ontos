import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Loader2 } from 'lucide-react';

type FilePreviewSource = {
  title?: string;
  contentType?: string | null;
  storagePath?: string; // UC Volumes path if applicable
  originalFilename?: string;
  downloadUrl?: string; // optional signed URL if available
};

interface FilePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source: FilePreviewSource | null;
  fetchUrl?: (() => Promise<string | undefined>) | null;
}

const isImage = (ct?: string | null) => !!ct && ct.startsWith('image/');
const isPdf = (ct?: string | null) => ct === 'application/pdf';
const isText = (ct?: string | null) => !!ct && (ct.startsWith('text/') || ct.includes('json') || ct.includes('csv'));

export const FilePreviewDialog: React.FC<FilePreviewDialogProps> = ({ open, onOpenChange, source, fetchUrl }) => {
  const title = source?.title || source?.originalFilename || 'Preview';
  const ct = source?.contentType;
  const [url, setUrl] = React.useState<string | undefined>(source?.downloadUrl);
  const [fetching, setFetching] = React.useState<boolean>(false);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    setUrl(source?.downloadUrl);
    setLoading(!!source);
    setErrorMsg(null);
  }, [source?.downloadUrl, source?.storagePath]);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!url && fetchUrl) {
        try {
          setFetching(true);
          setLoading(true);
          const u = await fetchUrl();
          if (!cancelled) {
            if (u) {
              setUrl(u);
              setErrorMsg(null);
            } else {
              setErrorMsg('Preview not available for this file.');
            }
          }
        } catch {
          if (!cancelled) setErrorMsg('Failed to fetch preview content.');
        } finally {
          if (!cancelled) setFetching(false);
        }
      }
    })();
    return () => { cancelled = true };
  }, [url, fetchUrl]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="relative min-h-[320px] flex items-center justify-center">
          {url ? (
            isImage(ct) ? (
              <img
                src={url}
                alt={title}
                className="max-h-[70vh] max-w-full rounded"
                onLoad={() => { setLoading(false); setErrorMsg(null); }}
                onError={() => { setLoading(false); setErrorMsg('Failed to load image'); }}
              />
            ) : isPdf(ct) ? (
              <object
                data={url}
                type="application/pdf"
                className="w-full h-[70vh] rounded"
                onLoad={() => { setLoading(false); setErrorMsg(null); }}
              >
                <p className="text-sm text-muted-foreground">PDF preview not supported. <a className="underline" href={url} target="_blank" rel="noreferrer">Open</a></p>
              </object>
            ) : isText(ct) ? (
              <iframe
                src={url}
                title="text-preview"
                className="w-full h-[70vh] rounded bg-background"
                onLoad={() => { setLoading(false); setErrorMsg(null); }}
              />
            ) : (
              <div className="text-sm text-muted-foreground">No inline preview for this file type. {url && (<a className="underline ml-1" href={url} target="_blank" rel="noreferrer">Download</a>)}
              </div>
            )
          ) : (!fetching && !loading && !fetchUrl) ? (
            <div className="text-sm text-muted-foreground">
              No preview URL available. Filename: {source?.originalFilename} • Path: {source?.storagePath}
            </div>
          ) : null}
          {(fetching || loading) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
          )}
          {!fetching && !loading && errorMsg && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-sm text-destructive bg-background/80 p-2 rounded">{errorMsg}</div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default FilePreviewDialog;


