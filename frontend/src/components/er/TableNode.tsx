import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Key, Database } from 'lucide-react';

export const TableNode: React.FC<{ data: any }> = ({ data }) => {
  const { label, row_count, columns = [] } = data;

  return (
    <div className="min-w-[240px] max-w-[320px] rounded-xl bg-background-card border-2 border-border shadow-xl shadow-black/40 overflow-hidden font-sans">
      <Handle type="target" position={Position.Left} className="w-2.5 h-2.5 bg-accent-primary border-2 border-background" />
      <Handle type="source" position={Position.Right} className="w-2.5 h-2.5 bg-accent-secondary border-2 border-background" />

      {/* Header */}
      <div className="bg-background-elevated px-3 py-2 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-accent-primary shrink-0" />
          <span className="font-semibold text-xs text-white truncate">{label}</span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-background/60 text-typography-muted border border-border/60">
          {row_count} rows
        </span>
      </div>

      {/* Columns list */}
      <div className="max-h-56 overflow-y-auto divide-y divide-border/30 text-[11px]">
        {columns.map((col: any) => (
          <div
            key={col.name}
            className={`px-3 py-1.5 flex items-center justify-between hover:bg-background-elevated/40 ${
              col.is_primary ? 'bg-accent-primary/10 font-medium' : ''
            }`}
          >
            <div className="flex items-center gap-1.5 truncate">
              {col.is_primary ? (
                <Key className="w-3 h-3 text-status-warning shrink-0" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-border shrink-0 ml-1" />
              )}
              <span className={`truncate ${col.is_primary ? 'text-accent-primary font-semibold' : 'text-typography-primary'}`}>
                {col.name}
              </span>
            </div>
            <span className="font-mono text-[10px] text-typography-muted shrink-0 ml-2">
              {col.data_type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

