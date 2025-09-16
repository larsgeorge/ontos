import { useCallback, useEffect, useMemo, useState } from 'react';

export type EntityKind = 'data_domain' | 'data_product' | 'data_contract';

export interface RichTextItem { id: string; entity_id: string; entity_type: EntityKind; title: string; short_description?: string | null; content_markdown: string; created_at?: string; updated_at?: string; }
export interface LinkItem { id: string; entity_id: string; entity_type: EntityKind; title: string; short_description?: string | null; url: string; created_at?: string; updated_at?: string; }
export interface DocumentItem { id: string; entity_id: string; entity_type: EntityKind; title: string; short_description?: string | null; original_filename: string; content_type?: string | null; size_bytes?: number | null; storage_path: string; created_at?: string; updated_at?: string; }

export interface UseEntityMetadataResult {
  richTexts: RichTextItem[];
  links: LinkItem[];
  documents: DocumentItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useEntityMetadata(entityType: EntityKind, entityId: string | null | undefined): UseEntityMetadataResult {
  const [richTexts, setRichTexts] = useState<RichTextItem[]>([]);
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!entityId) return;
    try {
      setLoading(true);
      setError(null);
      const [rt, li, docs] = await Promise.all([
        fetch(`/api/entities/${entityType}/${entityId}/rich-texts`).then(r => r.ok ? r.json() : Promise.reject(new Error(`rich-texts ${r.status}`))),
        fetch(`/api/entities/${entityType}/${entityId}/links`).then(r => r.ok ? r.json() : Promise.reject(new Error(`links ${r.status}`))),
        fetch(`/api/entities/${entityType}/${entityId}/documents`).then(r => r.ok ? r.json() : Promise.reject(new Error(`documents ${r.status}`))),
      ]);
      setRichTexts(Array.isArray(rt) ? rt : []);
      setLinks(Array.isArray(li) ? li : []);
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load metadata');
      setRichTexts([]);
      setLinks([]);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId]);

  useEffect(() => { refresh(); }, [refresh]);

  // Convenience sorted outputs
  const value = useMemo(() => ({
    richTexts: richTexts.slice().sort((a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime()),
    links: links.slice().sort((a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime()),
    documents: documents.slice().sort((a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime()),
    loading,
    error,
    refresh,
  }), [richTexts, links, documents, loading, error, refresh]);

  return value;
}


