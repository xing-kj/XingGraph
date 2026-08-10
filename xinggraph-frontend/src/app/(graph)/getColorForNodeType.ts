const NODE_COLORS: Record<string, string> = {
  TextDocument: "#A550FF",
  DocumentChunk: "#0DFF00",
  ChunkWiki: "#FF5CA8",
  TextSummary: "#FFB454",
  Entity: "#6510F4",
  EntityType: "#D5C2FF",
  NodeSet: "#94A3B8",
  TableRow: "#A550FF",
  TableType: "#6510F4",
  ColumnValue: "#747470",
  SchemaTable: "#A550FF",
  DatabaseSchema: "#6510F4",
  SchemaRelationship: "#323332",
  default: "#7c3aed",
};

export default function getColorForNodeType(type: string) {
  return NODE_COLORS[type] || "#DBD8D8";
}
