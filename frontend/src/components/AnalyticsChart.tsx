import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { TooltipContentProps } from "recharts";
import { ExtractedStudent } from "./types";

interface AnalyticsChartProps {
  students: ExtractedStudent[];
}

interface ChartDatum {
  name: string;
  value: number;
  color: string;
}

export const AnalyticsChart: React.FC<AnalyticsChartProps> = ({ students }) => {
  // Compute counts
  let passCount = 0;
  let failCount = 0;
  let pendingCount = 0;

  students.forEach((student) => {
    if (student.calculated_average === null) {
      pendingCount++;
    } else if (student.calculated_average >= 50.0) {
      passCount++;
    } else {
      failCount++;
    }
  });

  const total = students.length || 1;

  const data: ChartDatum[] = [
    { name: "Geçti (Ort >= 50)", value: passCount, color: "#10b981" }, // Emerald 500
    { name: "Kaldı (Ort < 50)", value: failCount, color: "#f43f5e" },   // Rose 500
    { name: "Hesaplanmadı / Belirsiz", value: pendingCount, color: "#94a3b8" } // Slate 400
  ].filter(item => item.value > 0); // Only display non-zero slices

  const customTooltip = ({ active, payload }: TooltipContentProps) => {
    if (active && payload && payload.length) {
      const dataInfo = payload[0].payload as ChartDatum;
      const pct = ((dataInfo.value / total) * 100).toFixed(1);
      return (
        <div className="bg-white border border-slate-200 p-3 rounded-lg shadow-md text-xs font-semibold">
          <p className="text-slate-800 font-bold mb-1">{dataInfo.name}</p>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: dataInfo.color }} />
            <span className="text-slate-600">Öğrenci Sayısı: <b className="text-slate-950">{dataInfo.value}</b> ({pct}%)</span>
          </div>
        </div>
      );
    }
    return null;
  };

  if (students.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[260px] bg-slate-50 border border-slate-100 rounded-lg text-slate-400 select-none">
        <span className="text-sm font-medium">Veri bulunamadı. Grafiği görüntülemek için görsel yükleyin.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[280px] bg-white border border-slate-200 rounded-lg p-4 shadow-sm select-none">
      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
        Sınıf Başarı Dağılımı (Geçti / Kaldı Analizi)
      </h3>
      <div className="flex-1 w-full min-h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={75}
              paddingAngle={4}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={customTooltip} />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle"
              iconSize={8}
              formatter={(value) => <span className="text-xs font-semibold text-slate-600">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
