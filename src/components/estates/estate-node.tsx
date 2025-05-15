import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Globe, Share2, Database, Zap, ZapOff } from 'lucide-react';
import { Estate } from '@/views/estate-details'; // Re-using the exported Estate type from details view for now

// Define a structure for dynamic handles
export interface DynamicHandle {
  id: string;
  position?: Position; // Default to Position.Right if not specified
  // style?: React.CSSProperties; // Optional style per handle
}

// Update the data structure expected by this node
export interface EstateNodeData {
  estate: Estate;
  onClick: (estateId: string) => void;
  dynamicSourceHandles?: DynamicHandle[]; // For multiple source handles
  isLocalInstance?: boolean; // To identify the local instance for specific styling/logic if needed
}

const EstateNode: React.FC<NodeProps<EstateNodeData>> = ({ data }) => {
  const { estate, onClick, dynamicSourceHandles, isLocalInstance } = data;

  // Calculate approximate vertical offset for multiple handles if needed
  // This is a simple example; more sophisticated logic might be required for many handles
  const getHandleStyle = (index: number, totalHandles: number): React.CSSProperties => {
    if (totalHandles <= 1) return { top: '50%' }; // Default center for single handle
    const spacing = 100 / (totalHandles + 1); // Percentage-based spacing
    return {
      top: `${(index + 1) * spacing}%`,
      // background: '#555', // For visibility during debugging
    };
  };

  return (
    <>
      {/* Default target handle (can be hidden if not used by this node type as a target) */}
      <Handle type="target" position={Position.Left} style={{ visibility: 'hidden' }} id="default-target" />

      <Card 
        className={`w-72 shadow-md hover:shadow-lg transition-shadow rounded-lg cursor-pointer bg-card ${isLocalInstance ? 'border-2 border-foreground' : 'border border-primary/20'}`}
        onClick={() => onClick(estate.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            onClick(estate.id);
          }
        }}
      >
        <CardHeader className="p-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary" />
            {estate.name}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3 text-xs space-y-1.5">
          <p className="text-muted-foreground truncate h-8" title={estate.description}>{estate.description}</p>
          <div className="flex items-center justify-between pt-1">
            <Badge 
                variant={
                    estate.cloud_type === 'aws' ? 'secondary' :
                    estate.cloud_type === 'azure' ? 'default' :
                    'outline'
                } 
                className="capitalize text-[10px] px-1.5 py-0.5"
            >
              {estate.cloud_type}
            </Badge>
            <Badge 
                variant={estate.connection_type === 'delta_share' ? 'default' : 'secondary'} 
                className="capitalize text-[10px] px-1.5 py-0.5"
            >
              {estate.connection_type === 'delta_share' ? 
                <Share2 className="h-3 w-3 mr-1" /> : 
                <Database className="h-3 w-3 mr-1" />}
              {estate.connection_type.replace('_', ' ')}
            </Badge>
            <Badge variant={estate.is_enabled ? 'default' : 'secondary'} className="capitalize text-[10px] px-1.5 py-0.5">
                {estate.is_enabled ? <Zap className="h-3 w-3 mr-0.5"/> : <ZapOff className="h-3 w-3 mr-0.5"/>}
                {estate.is_enabled ? 'On' : 'Off'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Default source handle (can be hidden or removed if dynamic handles are always used) */}
      {!dynamicSourceHandles && (
         <Handle type="source" position={Position.Right} style={{ visibility: 'hidden' }} id="default-source" />
      )}

      {/* Dynamically rendered source handles */} 
      {dynamicSourceHandles && dynamicSourceHandles.map((handleProps, index) => (
        <Handle 
          key={handleProps.id}
          type="source" 
          position={handleProps.position || Position.Right} 
          id={handleProps.id}
          style={getHandleStyle(index, dynamicSourceHandles.length)}
          // isConnectable={true} // Default is true
        />
      ))}
    </>
  );
};

export default EstateNode; 