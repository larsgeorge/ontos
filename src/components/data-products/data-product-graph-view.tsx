import React, { useMemo } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Background,
    Controls,
    MarkerType,
    Position,
    useNodesState,
    useEdgesState,
    NodeProps,
    Handle,
} from 'reactflow';
import { DataProduct, InputPort, OutputPort } from '@/types/data-product';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, Workflow } from 'lucide-react';
import * as dagre from 'dagre';
import { type NavigateFunction } from 'react-router-dom';
import { DatabaseZap } from 'lucide-react';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

import 'reactflow/dist/style.css';

interface DataProductNodeData {
    label: string;
    productType?: string;
    version: string;
    status?: string;
    inputPorts: InputPort[];
    outputPorts: OutputPort[];
    nodeId: string;
    navigate: NavigateFunction;
}

const DataProductNode: React.FC<NodeProps<DataProductNodeData>> = ({ data }) => {
    const handleHeight = 10;
    const handleWidth = 10;
    const inputBaseTopOffset = 25;
    const outputBaseTopOffset = 25;

    return (
        <>
            {/* Input Port Handles (Left) - With Tooltips, NO Provider here */}
            {/* <TooltipProvider delayDuration={100}> */}
                 {Array.isArray(data.inputPorts) && data.inputPorts.map((port, index) => {
                    if (!port?.id) {
                        return null;
                    }
                    const calculatedTop = inputBaseTopOffset + index * (handleHeight + 10);
                    return (
                        // Use a wrapper fragment and separate trigger div
                        <React.Fragment key={`input-frag-${port.id}`}>
                             <Tooltip>
                                {/* Transparent div as trigger, positioned over the handle */}
                                <TooltipTrigger 
                                    style={{
                                        position: 'absolute',
                                        left: '-8px', // Position to cover handle area
                                        top: `${calculatedTop - 2}px`, // Adjust top slightly
                                        width: `${handleWidth + 6}px`, // Make slightly larger than handle
                                        height: `${handleHeight + 4}px`,
                                        zIndex: 10 // Ensure it's above the handle visually
                                    }}
                                    onClick={(e) => e.stopPropagation()} // Keep stopPropagation
                                />
                                <TooltipContent side="left">
                                    <p className="font-semibold">{port.name} (Input)</p>
                                    {port.description && <p className="text-xs text-muted-foreground">{port.description}</p>}
                                    <p className="text-xs"><span className="text-muted-foreground">ID:</span> {port.id}</p>
                                    <p className="text-xs"><span className="text-muted-foreground">Source:</span> {port.sourceSystemId}{port.sourceOutputPortId ? `:${port.sourceOutputPortId}`: ''}</p>
                                </TooltipContent>
                            </Tooltip>
                            {/* Render the Handle itself */}
                            <Handle
                                key={`input-${port.id}`} // Keep original key if needed, or remove if fragment key is enough
                                type="target"
                                position={Position.Left}
                                id={port.id}
                                isConnectable={false}
                                // No onClick needed here now
                                style={{ 
                                    top: `${calculatedTop}px`, 
                                    left: '-5px',
                                    width: `${handleWidth}px`, 
                                    height: `${handleHeight}px`,
                                    borderRadius: '2px',
                                    background: '#55aaff',
                                    zIndex: 5 // Lower z-index than trigger
                                }}
                            />
                         </React.Fragment>
                    );
                 })}
            {/* </TooltipProvider> */}
            
            {/* Output Port Handles (Right) - With Tooltips, NO Provider here */}
             {/* <TooltipProvider delayDuration={100}> */}
                {Array.isArray(data.outputPorts) && data.outputPorts.map((port, index) => {
                     if (!port?.id) {
                        return null;
                    }
                    const calculatedTop = outputBaseTopOffset + index * (handleHeight + 10); 
                    return (
                         // Use a wrapper fragment and separate trigger div
                        <React.Fragment key={`output-frag-${port.id}`}>
                             <Tooltip>
                                 {/* Transparent div as trigger, positioned over the handle */}
                                <TooltipTrigger 
                                    style={{
                                        position: 'absolute',
                                        right: '-8px', // Position to cover handle area
                                        top: `${calculatedTop - 2}px`, // Adjust top slightly
                                        width: `${handleWidth + 6}px`, // Make slightly larger than handle
                                        height: `${handleHeight + 4}px`,
                                        zIndex: 10 // Ensure it's above the handle visually
                                    }}
                                    onClick={(e) => e.stopPropagation()} // Keep stopPropagation
                                />
                                <TooltipContent side="right">
                                    <p className="font-semibold">{port.name} (Output)</p>
                                    {port.description && <p className="text-xs text-muted-foreground">{port.description}</p>}
                                    <p className="text-xs"><span className="text-muted-foreground">ID:</span> {port.id}</p>
                                </TooltipContent>
                            </Tooltip>
                             {/* Render the Handle itself */}
                            <Handle
                                key={`output-${port.id}`} // Keep original key if needed, or remove if fragment key is enough
                                type="source"
                                position={Position.Right}
                                id={port.id}
                                isConnectable={false}
                                 // No onClick needed here now
                                style={{ 
                                    top: `${calculatedTop}px`, 
                                    right: '-5px',
                                    width: `${handleWidth}px`, 
                                    height: `${handleHeight}px`, 
                                    borderRadius: '2px',
                                    background: '#ffaa55',
                                    zIndex: 5 // Lower z-index than trigger
                                }}
                            />
                        </React.Fragment>
                    );
                 })}
            {/* </TooltipProvider> */}

            <div 
                className="cursor-pointer" 
                onClick={(e) => {
                    e.stopPropagation();
                    data.navigate(`/data-products/${data.nodeId}`);
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                         data.navigate(`/data-products/${data.nodeId}`);
                    }
                }} 
            >
                <Card className="w-64 shadow-md border-2 border-primary/50 bg-card hover:border-primary transition-colors">
                    <CardContent className="p-3 text-center">
                        <div className="text-sm font-semibold mb-1">{data.label}</div>
                        <div className="flex justify-center items-center gap-1 text-xs">
                             {data.productType && <Badge variant="outline">{data.productType}</Badge>}
                             <Badge variant="secondary">{data.version}</Badge>
                             {data.status && <Badge variant="default">{data.status}</Badge>}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </>
    );
};

interface ExternalSourceNodeData {
    label: string; // sourceSystemId
}

const ExternalSourceNode: React.FC<NodeProps<ExternalSourceNodeData>> = ({ data }) => {
    return (
        <>
            <Card className="w-48 bg-muted/50 border-dashed border-muted-foreground/50">
                <CardContent className="p-2 text-center">
                    <div className="flex items-center justify-center gap-2">
                         <DatabaseZap className="h-4 w-4 text-muted-foreground" />
                         <span className="text-xs font-mono text-muted-foreground break-all">{data.label}</span>
                    </div>
                </CardContent>
            </Card>
             {/* Single Source Handle for external node */}
            <Handle 
                type="source" 
                position={Position.Right} 
                id="external-source-handle" // Specific ID for this handle
                isConnectable={false}
                style={{ top: '50%', background: '#aaaaaa' }} // Grey color
            />
        </>
    );
};

const nodeTypes = {
    dataProduct: DataProductNode,
    externalSource: ExternalSourceNode,
};

// --- Dagre Layout Helper ---
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 256; // Approx width of DataProductNode (w-64)
const nodeHeight = 80; // Approx height of DataProductNode
const externalNodeWidth = 192; // w-48
const externalNodeHeight = 50; // Smaller height

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, ranksep: 70, nodesep: 30 });

  nodes.forEach((node) => {
    const width = node.type === 'externalSource' ? externalNodeWidth : nodeWidth;
    const height = node.type === 'externalSource' ? externalNodeHeight : nodeHeight;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const width = node.type === 'externalSource' ? externalNodeWidth : nodeWidth;
    const height = node.type === 'externalSource' ? externalNodeHeight : nodeHeight;
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;
    node.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
    };
  });

  return { nodes, edges };
};

interface DataProductGraphViewProps {
    products: DataProduct[];
    viewMode: 'table' | 'graph';
    setViewMode: (mode: 'table' | 'graph') => void;
    navigate: NavigateFunction;
}

const DataProductGraphView: React.FC<DataProductGraphViewProps> = ({ products, viewMode, setViewMode, navigate }) => {
    const initialElements = useMemo(() => {
        const validProducts = products.filter(p => p.id);
        const productNodes: Node<DataProductNodeData>[] = validProducts.map((product) => ({
            id: product.id!,
            type: 'dataProduct',
            position: { x: 0, y: 0 }, 
            data: { 
                label: product.info.title, 
                productType: product.productType, 
                version: product.version, 
                status: product.info.status, 
                inputPorts: product.inputPorts || [], 
                outputPorts: product.outputPorts || [], 
                nodeId: product.id!, 
                navigate: navigate
            },
        }));

        const productNodeIds = new Set(productNodes.map(n => n.id));
        const externalSourceIds = new Map<string, Node>(); // Store unique external sources and their nodes
        const initialEdges: Edge[] = [];

        // Pass 1: Identify external sources and create edges
        validProducts.forEach((product) => {
            if (Array.isArray(product.inputPorts)) {
                product.inputPorts.forEach((port: InputPort) => {
                    if (port?.id && port.sourceSystemId) {
                        const sourceId = port.sourceSystemId;
                        if (sourceId.startsWith('data-product:')) {
                            const sourceProductId = sourceId.substring('data-product:'.length);
                            const sourceHandleId = port.sourceOutputPortId;
                            if (productNodeIds.has(sourceProductId) && sourceHandleId) {
                                const edgeToAdd = { 
                                    id: `e-${sourceProductId}-${port.sourceOutputPortId}-${product.id!}-${port.id}`, 
                                    source: sourceProductId, 
                                    target: product.id!, 
                                    sourceHandle: sourceHandleId, 
                                    targetHandle: port.id, 
                                    type: 'smoothstep', 
                                    markerEnd: { type: MarkerType.ArrowClosed }, 
                                    animated: true, 
                                };
                                initialEdges.push(edgeToAdd);
                            } else {
                                if (!sourceHandleId) {
                                }
                                if (!productNodeIds.has(sourceProductId)) {
                                }
                            }
                        } else {
                            // External Source Found
                            const externalNodeId = `external-${sourceId}`; // Create a unique node ID
                            // Check if we already created a node for this external source
                            if (!externalSourceIds.has(externalNodeId)) {
                                const externalNode: Node<ExternalSourceNodeData> = {
                                    id: externalNodeId,
                                    type: 'externalSource',
                                    position: { x: 0, y: 0 }, // Position set by layout
                                    data: { label: sourceId },
                                };
                                externalSourceIds.set(externalNodeId, externalNode);
                            }
                            // Create edge from external source node
                            const edgeToAdd = { id: `e-${externalNodeId}-${product.id!}-${port.id}`, source: externalNodeId, target: product.id!, sourceHandle: 'external-source-handle', targetHandle: port.id, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, animated: true, };
                            initialEdges.push(edgeToAdd);
                        }
                    }
                });
            }
        });

        // Combine product nodes and external nodes
        const allInitialNodes = [...productNodes, ...Array.from(externalSourceIds.values())];

        // Pass 2: Apply layout to ALL nodes and edges
        return getLayoutedElements(allInitialNodes, initialEdges);

    }, [products, navigate]);

    // Reinstate state hooks for controlled component
    const [nodes, setNodes, onNodesChange] = useNodesState(initialElements.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialElements.edges);

    const tableButtonVariant = viewMode === 'table' ? 'secondary' : 'ghost';
    const graphButtonVariant = viewMode === 'graph' ? 'secondary' : 'ghost';

    return (
        <div className="h-[calc(100vh-300px)] w-full border rounded-lg relative" style={{ minHeight: '600px' }}>
            <div className="absolute top-2 right-2 z-10 flex items-center gap-1 border rounded-md p-0.5 bg-background/80 backdrop-blur-sm">
                <Button
                    variant={tableButtonVariant}
                    size="sm"
                    onClick={() => setViewMode('table')}
                    className="h-8 px-2"
                    title="Switch to Table View"
                >
                    <Table className="h-4 w-4" />
                </Button>
                <Button
                    variant={graphButtonVariant}
                    size="sm"
                    onClick={() => setViewMode('graph')}
                    className="h-8 px-2"
                    title="Switch to Graph View"
                    disabled
                >
                    <Workflow className="h-4 w-4" />
                </Button>
            </div>
            <TooltipProvider delayDuration={100}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    attributionPosition="bottom-left"
                     defaultEdgeOptions={{
                        style: { strokeWidth: 1.5, stroke: '#888' },
                        markerEnd: { type: MarkerType.ArrowClosed, color: '#888' },
                    }}
                    nodesDraggable={true}
                    nodesConnectable={false}
                    elementsSelectable={false}
                >
                    <Controls />
                    <Background />
                </ReactFlow>
            </TooltipProvider>
        </div>
    );
};

export default DataProductGraphView; 