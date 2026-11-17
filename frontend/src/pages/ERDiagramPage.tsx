import React, { useEffect, useState, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useConnectionStore } from '../store/useConnectionStore';
import { apiRequest } from '../api/client';
import { TableNode } from '../components/er/TableNode';
import { Network, RefreshCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export const ERDiagramPage: React.FC = () => {
  const { activeConnectionId, connections } = useConnectionStore();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nodeTypes = useMemo(() => ({ tableNode: TableNode }), []);

  const loadERData = async () => {
    if (!activeConnectionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest(`/connections/${activeConnectionId}/schema/er`);
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load ER diagram');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadERData();
  }, [activeConnectionId]);

  const activeConn = connections.find(c => c.id === activeConnectionId);

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-accent-primary" />
            Entity-Relationship (ER) Diagram
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Interactive relational schema topology for {activeConn ? activeConn.name : 'connected database'}
          </p>
        </div>

        <button
          onClick={loadERData}
          disabled={isLoading || !activeConnectionId}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-accent-primary' : ''}`} />
          <span>Refresh Diagram</span>
        </button>
      </div>

      {/* Main Diagram Canvas */}
      <div className="flex-1 bg-background-card/50 rounded-2xl border border-border overflow-hidden relative shadow-2xl">
        {!activeConnectionId ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center">
            <Network className="w-12 h-12 text-typography-muted mb-3 opacity-40" />
            <h3 className="text-sm font-semibold text-typography-primary">No Active Database Selected</h3>
            <p className="text-xs text-typography-secondary max-w-sm mt-1">
              Select or connect a database from the top navigation bar to explore its ER schema topology.
            </p>
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center">
            <p className="text-sm text-status-error font-medium">{error}</p>
            <button
              onClick={loadERData}
              className="mt-3 px-3 py-1.5 rounded-lg bg-background-elevated text-xs border border-border"
            >
              Retry
            </button>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            minZoom={0.2}
            maxZoom={2.0}
            className="dark-flow"
          >
            <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#293041" />
            <Controls className="!bg-background-elevated !border-border !rounded-lg overflow-hidden [&>button]:!bg-background-elevated [&>button]:!border-border [&>button]:!fill-white [&>button:hover]:!bg-background-card" />
            <MiniMap
              nodeColor="#8B5CF6"
              maskColor="rgba(11, 13, 18, 0.75)"
              className="!bg-background-card !border-border !rounded-lg"
            />
          </ReactFlow>
        )}
      </div>
    </div>
  );
};
