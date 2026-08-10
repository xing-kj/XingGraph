import { NodeObject } from "react-force-graph-2d";
import getColorForNodeType from "./getColorForNodeType";

interface GraphLegendProps {
  data?: NodeObject[];
}

export default function GraphLegend({ data }: GraphLegendProps) {
  const legend: Map<string, string> = new Map();

  for (let i = 0; i < Math.min(data?.length || 0, 100); i++) {
    const type = data![i].type as string;
    if (!legend.has(type)) {
      legend.set(type, getColorForNodeType(type));
    }
  }

  return (
    <div className="flex flex-col gap-1">
      {Array.from(legend.entries()).map(([type, color]) => (
        <div key={type} className="flex flex-row items-center gap-2">
          <span
            className="inline-block"
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: color,
            }}
          />
          <span className="text-white text-xs">{type}</span>
        </div>
      ))}
    </div>
  );
}
