import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel';
// Preview handled in EntityMetadataPanel
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, Edit3, Users, Tag, Hash, CalendarDays, UserCircle, ListTree, ChevronsUpDown } from 'lucide-react';
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

      <EntityMetadataPanel entityId={domainId!} entityType={entityType} />

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