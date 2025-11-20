import React, { useMemo, useEffect } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Position,
    MarkerType,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    MiniMap,
    NodeProps,
    Handle
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useNavigate } from 'react-router-dom';
import { DataDomain } from '@/types/data-domain';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ListTree } from 'lucide-react';
import dagre from 'dagre'; // Import dagre

interface DomainNodeData {
    label: string;
    id: string;
    parentId?: string | null;
    childrenCount?: number;
}

const DomainNode: React.FC<NodeProps<DomainNodeData>> = ({ data, id }) => {
    const navigate = useNavigate();
    const handleNodeClick = () => {
        navigate(`/data-domains/${id}`);
    };

    return (
        <>
            {/* Explicit handles - adjust position based on layout direction if needed later */}
            {/* For LR layout, target is Left, source is Right */}
            <Handle type="target" position={Position.Left} id="target" style={{ visibility: 'hidden' }} />
            <Card 
                onClick={handleNodeClick} 
                className="w-60 shadow-md hover:shadow-lg transition-shadow rounded-lg cursor-pointer bg-card border-primary/30 react-flow__node-default"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && handleNodeClick()}
            >
                <CardHeader className="p-2 flex flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-sm font-medium flex items-center">
                        <ListTree className="w-4 h-4 mr-2 text-primary" />
                        {data.label}
                    </CardTitle>
                    {typeof data.childrenCount === 'number' && data.childrenCount > 0 && (
                        <Badge variant="secondary" className="text-xs">{data.childrenCount} {data.childrenCount === 1 ? 'child' : 'children'}</Badge>
                    )}
                </CardHeader>
                {/* Optionally, add more details to CardContent if needed */}
                {/* <CardContent className="p-2 text-xs text-muted-foreground">
                    ID: {data.id}
                </CardContent> */}
            </Card>
            <Handle type="source" position={Position.Right} id="source" style={{ visibility: 'hidden' }} />
        </>
    );
};

const nodeTypes = { domainNode: DomainNode };

interface DataDomainGraphViewProps {
    domains: DataDomain[];
}

// Helper to arrange nodes in a basic tree layout (can be improved)
const getLayoutedElements = (domains: DataDomain[], direction = 'LR') => {
    const nodes: Node<DomainNodeData>[] = [];
    const edges: Edge[] = [];
    if (!domains || domains.length === 0) return { nodes, edges };

    // Detect dark mode
    const isDarkMode = document.documentElement.classList.contains('dark');

    const domainMap = new Map(domains.map(d => [d.id, d]));

    const nodeHeight = 80;
    const nodeWidth = 240; 

    // Create all nodes first
    domains.forEach(domain => {
        nodes.push({
            id: domain.id,
            type: 'domainNode',
            data: { 
                label: domain.name,
                id: domain.id, 
                parentId: domain.parent_id,
                childrenCount: domain.children_count
            },
            position: { x: 0, y: 0 }, // Initial position, Dagre will override
            // Adjust source/target positions based on LR direction
            sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
            targetPosition: direction === 'LR' ? Position.Left : Position.Top,
        });
    });

    // Create edges
    domains.forEach(domain => {
        if (domain.parent_id && domainMap.has(domain.parent_id)) {
            edges.push({
                id: `e-${domain.parent_id}-${domain.id}`,
                source: domain.parent_id,
                target: domain.id,
                type: 'smoothstep',
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: isDarkMode ? '#94a3b8' : '#333333'
                },
                style: {
                    stroke: isDarkMode ? '#94a3b8' : '#666666',
                    strokeWidth: 1.5
                }
            });
        }
    });
    
    if (nodes.length > 0 && typeof window !== 'undefined') { 
        const dagreGraph = new dagre.graphlib.Graph();
        dagreGraph.setDefaultEdgeLabel(() => ({}));
        dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 70 });

        nodes.forEach((node) => {
            dagreGraph.setNode(node.id, { label: node.data.label, width: nodeWidth, height: nodeHeight });
        });

        edges.forEach((edge) => {
            dagreGraph.setEdge(edge.source, edge.target);
        });

        dagre.layout(dagreGraph);

        const layoutedNodes = nodes.map((node) => {
            const nodeWithPosition = dagreGraph.node(node.id);
            return {
                ...node,
                targetPosition: direction === 'LR' ? Position.Left : Position.Top, // Ensure this is consistent
                sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom, // Ensure this is consistent
                position: { x: nodeWithPosition.x - nodeWidth / 2, y: nodeWithPosition.y - nodeHeight / 2 },
            };
        });
        return { nodes: layoutedNodes, edges };
    }
    
    return { nodes, edges };
};

const DataDomainGraphView: React.FC<DataDomainGraphViewProps> = ({ domains }) => {
    // Use useMemo for initial calculation, then useEffect to update when domains change
    const memoizedElements = useMemo(() => getLayoutedElements(domains, 'LR'), [domains]);
    const [nodes, setNodes, onNodesChange] = useNodesState(memoizedElements.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(memoizedElements.edges);

    // Detect dark mode
    const isDarkMode = document.documentElement.classList.contains('dark');

    useEffect(() => {
        // Pass 'LR' explicitly to ensure horizontal layout
        const { nodes: newNodes, edges: newEdges } = getLayoutedElements(domains, 'LR');
        setNodes(newNodes);
        setEdges(newEdges);
    }, [domains, setNodes, setEdges]);

    return (
        <div className="h-[calc(100vh-280px)] w-full border rounded-lg" data-testid="data-domain-graph-view">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-right"
                className="bg-background"
            >
                <Controls />
                <MiniMap nodeStrokeWidth={3} zoomable pannable />
                <Background color={isDarkMode ? '#334155' : '#e2e8f0'} gap={16} />
            </ReactFlow>
        </div>
    );
};

export default DataDomainGraphView; 