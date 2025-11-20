import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  Handle,
  Position,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Download } from 'lucide-react';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

// Types for our schema data
interface Column {
  name: string;
  type: string;
  primary_key: boolean;
  nullable: boolean;
  foreign_key?: {
    target_table: string;
    target_column: string;
  } | null;
}

interface Table {
  id: string;
  name: string;
  columns: Column[];
}

interface Relationship {
  id: string;
  source: string;
  target: string;
  columns: string[];
}

interface SchemaData {
  tables: Table[];
  relationships: Relationship[];
}

// Custom Table Node Component
function TableNode({ data }: { data: Table }) {
  const handleWheel = (e: React.WheelEvent) => {
    // Stop propagation to prevent React Flow from capturing the wheel event for zooming
    e.stopPropagation();
    // Don't prevent default - we want normal scrolling to work
  };

  return (
    <>
      <Handle type="target" position={Position.Left} style={{ visibility: 'hidden' }} />
      <Card className="min-w-[250px] max-w-[300px] shadow-lg">
        {/* Only the header is draggable via drag-handle class */}
        <CardHeader className="drag-handle bg-primary text-primary-foreground py-2 px-3 cursor-move">
          <CardTitle className="text-sm font-bold">{data.name}</CardTitle>
          <div className="text-[10px] opacity-75 mt-0.5">{data.columns.length} columns</div>
        </CardHeader>
        {/* Content is scrollable but not draggable */}
        <CardContent className="p-0">
          <div
            className="max-h-[500px] overflow-y-auto overflow-x-hidden nodrag cursor-default"
            onWheel={handleWheel}
          >
            <table className="w-full text-xs">
              <tbody>
                {data.columns.map((col, idx) => (
                  <tr
                    key={idx}
                    className={`border-b last:border-b-0 ${
                      col.primary_key
                        ? 'bg-yellow-50 dark:bg-yellow-950'
                        : col.foreign_key
                        ? 'bg-blue-50 dark:bg-blue-950'
                        : ''
                    }`}
                  >
                    <td className="py-1 px-2 font-mono">
                      <div className="flex items-center gap-1">
                        {col.primary_key && (
                          <span className="text-yellow-600 dark:text-yellow-400" title="Primary Key">
                            🔑
                          </span>
                        )}
                        {col.foreign_key && (
                          <span className="text-blue-600 dark:text-blue-400" title="Foreign Key">
                            🔗
                          </span>
                        )}
                        <span className="font-semibold truncate">{col.name}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5 truncate">
                        {col.type}
                        {!col.nullable && (
                          <span className="text-red-500 ml-1" title="NOT NULL">
                            *
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <Handle type="source" position={Position.Right} style={{ visibility: 'hidden' }} />
    </>
  );
}

// Custom node types
const nodeTypes = {
  tableNode: TableNode,
};

// Layout configuration using dagre
const getLayoutedElements = (
  tables: Table[],
  relationships: Relationship[],
  direction = 'LR'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 150, ranksep: 200 });

  // Create nodes
  const nodes: Node[] = tables.map((table) => {
    const node: Node = {
      id: table.id,
      type: 'tableNode',
      data: table,
      position: { x: 0, y: 0 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
    
    // Estimate node dimensions based on content
    const width = 280;
    const height = Math.min(80 + table.columns.length * 35, 560);
    dagreGraph.setNode(table.id, { width, height });
    
    return node;
  });

  // Create edges
  const edges: Edge[] = relationships.map((rel) => ({
    id: rel.id,
    source: rel.source,
    target: rel.target,
    type: 'smoothstep',
    animated: false,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 20,
      height: 20,
      color: '#94a3b8',
    },
    style: {
      strokeWidth: 2,
      stroke: '#94a3b8',
    },
    label: rel.columns.join(', '),
    labelStyle: { fill: '#666', fontSize: 10 },
  }));

  // Add edges to dagre
  relationships.forEach((rel) => {
    dagreGraph.setEdge(rel.source, rel.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Apply calculated positions
  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWithPosition.width / 2,
      y: nodeWithPosition.y - nodeWithPosition.height / 2,
    };
  });

  return { nodes, edges };
};

export default function DatabaseSchema() {
  const [schemaData, setSchemaData] = useState<SchemaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Detect dark mode
  const isDarkMode = document.documentElement.classList.contains('dark');

  const setStaticSegments = useBreadcrumbStore((state: any) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state: any) => state.setDynamicTitle);

  // Set breadcrumb
  useEffect(() => {
    setStaticSegments([]);
    setDynamicTitle('Database Schema');
    return () => {
      setStaticSegments([]);
      setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  // Fetch schema data
  useEffect(() => {
    const fetchSchema = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/database-schema');
        if (!response.ok) {
          throw new Error(`Failed to load schema: ${response.statusText}`);
        }
        const data = await response.json();
        setSchemaData(data);
      } catch (err) {
        console.error('Error loading database schema:', err);
        setError(err instanceof Error ? err.message : 'Failed to load schema');
      } finally {
        setLoading(false);
      }
    };

    fetchSchema();
  }, []);

  // Filter and layout nodes/edges when schema or search changes
  useEffect(() => {
    if (!schemaData) return;

    // Filter tables based on search
    const filteredTables = schemaData.tables.filter((table) =>
      table.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Filter relationships to only include those between visible tables
    const visibleTableIds = new Set(filteredTables.map((t) => t.id));
    const filteredRelationships = schemaData.relationships.filter(
      (rel) => visibleTableIds.has(rel.source) && visibleTableIds.has(rel.target)
    );

    // Layout the filtered elements
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      filteredTables,
      filteredRelationships
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [schemaData, searchTerm, setNodes, setEdges]);

  const handleDownload = useCallback(() => {
    // Create a simple text representation for download
    if (!schemaData) return;

    const content = schemaData.tables
      .map((table) => {
        const cols = table.columns
          .map(
            (col) =>
              `  - ${col.name}: ${col.type}${col.primary_key ? ' [PK]' : ''}${
                col.foreign_key ? ` [FK -> ${col.foreign_key.target_table}]` : ''
              }`
          )
          .join('\n');
        return `${table.name}\n${cols}`;
      })
      .join('\n\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'database-schema.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [schemaData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading database schema...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error Loading Schema</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4" style={{ height: 'calc(100vh - 80px)' }}>
      {/* Header with search and controls */}
      <div className="flex items-center gap-4 bg-background p-4 rounded-lg border">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search tables..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button onClick={handleDownload} variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
        <div className="text-sm text-muted-foreground">
          {schemaData?.tables.length || 0} tables, {schemaData?.relationships.length || 0}{' '}
          relationships
        </div>
      </div>

      {/* React Flow Diagram */}
      <div className="flex-1 border rounded-lg overflow-hidden bg-background" style={{ minHeight: 0 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.1}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
          noWheelClassName="nodrag"
          defaultEdgeOptions={{
            markerEnd: { type: MarkerType.ArrowClosed },
          }}
        >
          <Background color={isDarkMode ? '#334155' : '#e2e8f0'} gap={16} />
          <Controls />
          <MiniMap
            nodeColor={() => '#3b82f6'}
            nodeStrokeWidth={3}
            zoomable
            pannable
          />
          <Panel position="top-left" className="bg-background/95 p-3 rounded-lg border shadow-sm text-xs m-2">
            <div className="font-semibold mb-2">Legend</div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="text-yellow-600 dark:text-yellow-400">🔑</span>
                <span>Primary Key</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-blue-600 dark:text-blue-400">🔗</span>
                <span>Foreign Key</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-red-500">*</span>
                <span>NOT NULL</span>
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
}

