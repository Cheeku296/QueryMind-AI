import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

interface ChartProps {
  chartSpec: {
    chart_type: string;
    title: string;
    x_axis: string;
    y_axis: string;
    data: any[];
  };
}

const COLORS = ['#8B5CF6', '#6366F1', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6'];

export const ChartRenderer: React.FC<ChartProps> = ({ chartSpec }) => {
  if (!chartSpec || !chartSpec.data || chartSpec.data.length === 0) {
    return null;
  }

  const { chart_type, title, x_axis, y_axis, data } = chartSpec;

  const renderChart = () => {
    switch (chart_type?.toLowerCase()) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#293041" opacity={0.6} />
              <XAxis dataKey={x_axis} stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }} />
              <Line type="monotone" dataKey={y_axis} stroke="#8B5CF6" strokeWidth={2.5} dot={{ r: 4, fill: '#8B5CF6' }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorY" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#293041" opacity={0.6} />
              <XAxis dataKey={x_axis} stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
              />
              <Area type="monotone" dataKey={y_axis} stroke="#8B5CF6" fillOpacity={1} fill="url(#colorY)" />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'pie':
      case 'donut':
        return (
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data}
                dataKey={y_axis}
                nameKey={x_axis}
                cx="50%"
                cy="50%"
                outerRadius={85}
                innerRadius={chart_type === 'donut' ? 45 : 0}
                paddingAngle={3}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'bar':
      default:
        return (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#293041" opacity={0.6} />
              <XAxis dataKey={x_axis} stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }} />
              <Bar dataKey={y_axis} fill="#8B5CF6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <div className="mt-3 p-4 rounded-xl bg-background-elevated/70 border border-border">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-typography-primary flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-accent-primary" />
          {title || 'Visualization'}
        </h4>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-background-card border border-border text-typography-secondary">
          {chart_type}
        </span>
      </div>
      {renderChart()}
    </div>
  );
};

