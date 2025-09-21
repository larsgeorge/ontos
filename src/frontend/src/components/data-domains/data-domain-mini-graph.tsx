import React, { useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useNavigate } from 'react-router-dom';
import { DataDomain, DataDomainBasicInfo } from '@/types/data-domain';
import { Card } from '@/components/ui/card'; // Simple card for node

interface DataDomainMiniGraphProps {
  currentDomain: DataDomain; // Full current domain for its details
  onNodeClick?: (domainId: string) => void; // Optional override for click handling
}

const nodeWidth = 150;
const nodeHeight = 60;
const horizontalNodeSpacing = 50; // General horizontal spacing for simple layout
const horizontalChildSpacing = 20; // Spacing between horizontal children in Christmas tree
const verticalLevelSpacing = 50;   // Spacing between parent/current/children levels
const fixedPadding = 20;   // Overall padding for the graph canvas (renamed from fixedVerticalPadding)

const CustomNode = ({ data }: { data: { label: string; domainId: string; onClick: (id: string) => void, isCurrent?: boolean } }) => (
  <Card 
    className={`p-2 w-[${nodeWidth}px] h-[${nodeHeight}px] flex items-center justify-center text-center text-sm shadow-md hover:shadow-lg cursor-pointer ${data.isCurrent ? 'bg-primary/10 border-primary' : 'bg-card'}`}
    onClick={() => data.onClick(data.domainId)}
  >
    <Handle type="target" position={Position.Top} id="target-top" style={{ background: 'transparent', border: 'none' }} />
    <Handle type="target" position={Position.Left} id="target-left" style={{ background: 'transparent', border: 'none' }} />
    {data.label}
    <Handle type="source" position={Position.Bottom} id="source-bottom" style={{ background: 'transparent', border: 'none' }} />
    <Handle type="source" position={Position.Right} id="source-right" style={{ background: 'transparent', border: 'none' }} />
  </Card>
);

const nodeTypes = { custom: CustomNode };

export const DataDomainMiniGraph: React.FC<DataDomainMiniGraphProps> = ({ currentDomain, onNodeClick }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const navigate = useNavigate();

  const handleNodeClick = (domainId: string) => {
    if (onNodeClick) {
      onNodeClick(domainId);
    } else {
      navigate(`/data-domains/${domainId}`);
    }
  };

  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    
    const parentInfo = currentDomain.parent_info;
    const childrenInfo = currentDomain.children_info || [];
    const numChildren = childrenInfo.length;

    // Layout decision
    const isSimpleHorizontalLayout = 
      (parentInfo && numChildren === 0) ||      // P-C
      (!parentInfo && numChildren <= 1) ||     // C or C-S
      (parentInfo && numChildren === 1);       // P-C-S

    if (isSimpleHorizontalLayout) {
      // --- Simple Horizontal Layout ---
      let currentX = fixedPadding;
      const yPos = fixedPadding;

      // Parent Node (if exists)
      if (parentInfo) {
        newNodes.push({
          id: parentInfo.id,
          type: 'custom',
          data: { label: parentInfo.name, domainId: parentInfo.id, onClick: handleNodeClick },
          position: { x: currentX, y: yPos },
        });
        currentX += nodeWidth + horizontalNodeSpacing;
      }

      // Current Domain Node
      newNodes.push({
        id: currentDomain.id,
        type: 'custom',
        data: { label: currentDomain.name, domainId: currentDomain.id, onClick: handleNodeClick, isCurrent: true },
        position: { x: currentX, y: yPos },
      });
      
      if (parentInfo) {
        newEdges.push({
          id: `e-${parentInfo.id}-${currentDomain.id}`,
          source: parentInfo.id,
          target: currentDomain.id,
          sourceHandle: 'source-right',
          targetHandle: 'target-left',
        });
      }
      currentX += nodeWidth + horizontalNodeSpacing;

      // Single Child Node (if exists)
      if (numChildren === 1) {
        const child = childrenInfo[0];
        newNodes.push({
          id: child.id,
          type: 'custom',
          data: { label: child.name, domainId: child.id, onClick: handleNodeClick },
          position: { x: currentX, y: yPos },
        });
        newEdges.push({
          id: `e-${currentDomain.id}-${child.id}`,
          source: currentDomain.id,
          target: child.id,
          sourceHandle: 'source-right',
          targetHandle: 'target-left',
        });
      }
    } else {
      // --- Christmas Tree Layout (Parent top-center, Current mid-center, Children bottom-row) ---
      let currentY = fixedPadding;

      const childrenRowActualWidth = numChildren > 0 ? (numChildren * nodeWidth) + Math.max(0, (numChildren - 1)) * horizontalChildSpacing : 0;
      const parentCurrentRowActualWidth = nodeWidth; // Parent and current are vertically aligned
      const maxContentWidth = Math.max(parentCurrentRowActualWidth, childrenRowActualWidth, nodeWidth); // Ensure current node width is considered

      const centralX = (maxContentWidth - nodeWidth) / 2; // For parent and current
      const childrenRowStartX = (maxContentWidth - childrenRowActualWidth) / 2;
      
      // Parent Node (Top Center)
      if (parentInfo) {
        newNodes.push({
          id: parentInfo.id,
          type: 'custom',
          data: { label: parentInfo.name, domainId: parentInfo.id, onClick: handleNodeClick },
          position: { x: centralX, y: currentY },
        });
        currentY += nodeHeight + verticalLevelSpacing;
      }

      // Current Domain Node (Middle Center)
      const actualCurrentY = currentY;
      newNodes.push({
        id: currentDomain.id,
        type: 'custom',
        data: { label: currentDomain.name, domainId: currentDomain.id, onClick: handleNodeClick, isCurrent: true },
        position: { x: centralX, y: actualCurrentY },
      });
      
      if (parentInfo) {
        newEdges.push({
          id: `e-${parentInfo.id}-${currentDomain.id}`,
          source: parentInfo.id,
          target: currentDomain.id,
          sourceHandle: 'source-bottom',
          targetHandle: 'target-top',
        });
      }

      // Children Nodes (Bottom Row, Horizontal, Centered)
      if (numChildren > 0) { // This block implies numChildren > 1 for Christmas tree based on prior logic
        const childrenDisplayY = actualCurrentY + nodeHeight + verticalLevelSpacing;
        childrenInfo.forEach((child, index) => {
          newNodes.push({
            id: child.id,
            type: 'custom',
            data: { label: child.name, domainId: child.id, onClick: handleNodeClick },
            position: { 
              x: childrenRowStartX + index * (nodeWidth + horizontalChildSpacing), 
              y: childrenDisplayY 
            }, 
          });
          newEdges.push({
            id: `e-${currentDomain.id}-${child.id}`,
            source: currentDomain.id,
            target: child.id,
            sourceHandle: 'source-bottom', // Current node's bottom to child's top
            targetHandle: 'target-top',
          });
        });
      }
    }
    
    setNodes(newNodes);
    setEdges(newEdges);
  }, [currentDomain, navigate, setNodes, setEdges]);
  
  // Fixed height for consistent layout; rely on fitView to include all nodes
  const graphHeight = 220;
  
  // Conditional rendering based on whether there's anything to show beyond the current node
  // If only the current node exists (no parent, no children), don't render the graph.
  // This was the previous logic, keeping it for now.
  // if (!currentDomain || (!currentDomain.parent_info && (!currentDomain.children_info || currentDomain.children_info.length === 0))) {
    // return null; // Let's allow rendering just the current node for now, handled by simple layout.
    // The simple layout logic above should handle a single "Current" node correctly if this condition is removed.
    // For now, let's keep the early return if the user doesn't want to see a graph with just one node.
    // To test the C-only case, this line might need to be commented out temporarily.
    // Or, the isSimpleHorizontalLayout condition for C-only implicitly means it will render a single node.
  // }

  const defaultEdgeOptions = {
    // animated: false, // No longer animated
    markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15 }, // Removed color, default size
  };

  return (
    <div style={{ height: graphHeight, margin: 'auto' }} className="border rounded-lg overflow-hidden bg-muted/20 w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        selectNodesOnDrag={false}
        minZoom={0.1} // Allow more aggressive zoom out if needed
        maxZoom={1.5}
      >
        {/* Ensure viewport fits nodes on first render and when layout changes */}
        {/* reactflow will auto fit with fitView on mount and when size changes; to enforce on data change, we can key the flow */}
      </ReactFlow>
    </div>
  );
}; 