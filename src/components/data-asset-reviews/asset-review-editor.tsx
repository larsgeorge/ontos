import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, Eye, Code } from 'lucide-react';
import { useApi } from '@/hooks/use-api';
import { useToast } from "@/hooks/use-toast";
import { ReviewedAsset, ReviewedAssetStatus, AssetType, AssetDefinition, TablePreview, ReviewedAssetUpdate } from '@/types/data-asset-review';
import { DataTable } from "@/components/ui/data-table"; // For table preview
import { Alert, AlertDescription } from '@/components/ui/alert';
// Import SyntaxHighlighter
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'; // Choose a style (e.g., oneLight)

interface AssetReviewEditorProps {
    requestId: string;
    asset: ReviewedAsset;
    api: ReturnType<typeof useApi>;
    onReviewSave: (updatedAsset: ReviewedAsset) => void; // Callback after saving
}

// Helper function to check API response
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string }, name: string): T => {
    if (response.error) throw new Error(`${name} fetch failed: ${response.error}`);
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    // Allow null/undefined for content fetching (e.g., definition might be null)
    // if (response.data === null || response.data === undefined) {
    //     throw new Error(`${name} fetch returned null or undefined data.`);
    // }
    return response.data as T;
};

export default function AssetReviewEditor({ requestId, asset, api, onReviewSave }: AssetReviewEditorProps) {
    const { get, put } = api;
    const { toast } = useToast();

    // Content State
    const [definition, setDefinition] = useState<AssetDefinition | null>(null);
    const [preview, setPreview] = useState<TablePreview | null>(null);
    const [isLoadingContent, setIsLoadingContent] = useState(false);
    const [contentError, setContentError] = useState<string | null>(null);

    // Form State
    const [currentStatus, setCurrentStatus] = useState<ReviewedAssetStatus>(asset.status);
    const [comments, setComments] = useState<string>(asset.comments || '');
    const [isSaving, setIsSaving] = useState(false);

    // Fetch content based on asset type
    useEffect(() => {
        const fetchContent = async () => {
            setIsLoadingContent(true);
            setContentError(null);
            setDefinition(null);
            setPreview(null);

            try {
                if (asset.asset_type === AssetType.VIEW || asset.asset_type === AssetType.FUNCTION) {
                    // Fetch definition (returns plain text)
                    const response = await fetch(`/api/data-asset-reviews/${requestId}/assets/${asset.id}/definition`);
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(errorText || `Failed to fetch definition (${response.status})`);
                    }
                    const textDefinition = await response.text();
                    setDefinition(textDefinition);
                } else if (asset.asset_type === AssetType.TABLE) {
                    // Fetch table preview
                    const response = await get<TablePreview>(`/api/data-asset-reviews/${requestId}/assets/${asset.id}/preview?limit=50`);
                    const previewData = checkApiResponse(response, 'Table Preview');
                    setPreview(previewData);
                }
            } catch (err: any) {
                console.error('Error fetching asset content:', err);
                setContentError(err.message || 'Failed to load asset content');
            } finally {
                setIsLoadingContent(false);
            }
        };

        fetchContent();
    }, [requestId, asset.id, asset.asset_type, get]); // Re-fetch if asset changes

    const handleSaveReview = async () => {
        setIsSaving(true);
        setContentError(null);
        const payload: ReviewedAssetUpdate = {
            status: currentStatus,
            comments: comments || null,
        };

        try {
            const response = await put<ReviewedAsset>(`/api/data-asset-reviews/${requestId}/assets/${asset.id}/status`, payload);
            const updatedAsset = checkApiResponse(response, 'Update Asset Status');
            toast({ title: 'Success', description: `Review for ${asset.asset_fqn} saved.` });
            onReviewSave(updatedAsset); // Notify parent component
        } catch (err: any) {
            setContentError(err.message || 'Failed to save review.');
            toast({ title: 'Error', description: `Failed to save review: ${err.message}`, variant: 'destructive' });
        } finally {
            setIsSaving(false);
        }
    };

    // --- Render Content --- //
    const renderAssetContent = () => {
        if (isLoadingContent) {
            return <div className="flex justify-center items-center h-40"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
        }
        if (contentError) {
             return <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{contentError}</AlertDescription></Alert>;
        }

        if (definition !== null) {
            // Determine language based on asset type (simple heuristic)
            const language = asset.asset_type === AssetType.FUNCTION ? 'python' : 'sql';
            return (
                <div className="border rounded max-h-96 overflow-auto text-sm">
                    {/* Use SyntaxHighlighter */}
                    <SyntaxHighlighter
                        language={language}
                        style={oneLight} // Use the imported style
                        showLineNumbers // Optional: Show line numbers
                        wrapLines={true}
                        customStyle={{
                            margin: 0, // Remove default margins
                            padding: '0.5rem', // Add some padding
                            fontSize: '0.75rem', // Match text-xs roughly
                            maxHeight: '24rem', // Ensure it fits within max-h-96
                        }}
                    >
                        {definition || ''} 
                    </SyntaxHighlighter>
                </div>
            );
        }

        if (preview !== null) {
            const columns = preview.schema.map(col => ({
                accessorKey: col.name,
                header: col.name,
                // Basic cell rendering, consider type formatting
                cell: ({ row }: { row: any }) => <span className="text-xs font-mono truncate" title={String(row.getValue(col.name))}>{String(row.getValue(col.name))}</span>,
            }));
            return (
                 <div className="border rounded max-h-96 overflow-auto">
                    <DataTable
                        columns={columns}
                        data={preview.data}
                        // Enable pagination if desired, might need adjustments
                    />
                </div>
            );
        }

        if (asset.asset_type === AssetType.MODEL) {
            return <p className="text-sm text-muted-foreground">Model review details not yet implemented.</p>;
        }

        return <p className="text-sm text-muted-foreground">No preview or definition available for this asset type.</p>;
    };

    return (
        <div className="space-y-4">
             {/* Asset Details */}
             <div>
                 <h4 className="font-medium text-lg mb-2">Asset Details</h4>
                 <p className="text-sm"><span className="font-semibold">FQN:</span> <span className="font-mono text-xs">{asset.asset_fqn}</span></p>
                 <p className="text-sm"><span className="font-semibold">Type:</span> <Badge variant="secondary">{asset.asset_type}</Badge></p>
             </div>

            {/* Content Viewer */}
            <div className="space-y-2">
                 <h4 className="font-medium text-lg">Content Preview / Definition</h4>
                {renderAssetContent()}
            </div>

            {/* Review Form */}
            <div className="space-y-3 pt-4 border-t">
                <h4 className="font-medium text-lg">Your Review</h4>
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="asset-status" className="text-right">Status *</Label>
                     <Select
                        value={currentStatus}
                        onValueChange={(value) => setCurrentStatus(value as ReviewedAssetStatus)}
                    >
                        <SelectTrigger id="asset-status" className="col-span-3">
                            <SelectValue placeholder="Set status" />
                        </SelectTrigger>
                        <SelectContent>
                            {Object.values(ReviewedAssetStatus).map((status) => (
                                <SelectItem key={status} value={status}>{status}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                 <div className="grid grid-cols-4 items-start gap-4">
                    <Label htmlFor="comments" className="text-right pt-2">Comments</Label>
                    <Textarea
                        id="comments"
                        value={comments}
                        onChange={(e) => setComments(e.target.value)}
                        placeholder="Add your review comments here..."
                        className="col-span-3 min-h-[80px]"
                    />
                </div>
                 {contentError && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{contentError}</AlertDescription>
                        </Alert>
                    )}
                 {/* Save button is added here, within the form section */}
                 <div className="flex justify-end pt-2">
                     <Button onClick={handleSaveReview} disabled={isSaving}>
                        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Save Review
                     </Button>
                 </div>
            </div>
            {/* Button for automated checks (placeholder) */}
             {asset.asset_type === AssetType.TABLE && (
                 <div className="pt-4 border-t">
                    <Button variant="outline" disabled>Run Automated Checks (Not Implemented)</Button>
                </div>
             )}
        </div>
    );
} 