"use client";

import { v4 as uuid4 } from "uuid";
import { NodeObject, LinkObject } from "react-force-graph-2d";
import { ChangeEvent, useEffect, useImperativeHandle, useRef, useState } from "react";

import { DeleteIcon } from "@/ui/icons";
import { CTAButton, Input, NeutralButton, Select } from "@/ui/elements";

interface GraphControlsProps {
  data?: {
    nodes: NodeObject[];
    links: LinkObject[];
  };
  isAddNodeFormOpen: boolean;
  ref: React.RefObject<GraphControlsAPI | null>;
  onFitIntoView: () => void;
  onGraphShapeChange: (shape: string) => void;
  autoRotateShapes?: boolean;
  floating?: boolean;
}

export interface GraphControlsAPI {
  setSelectedNode: (node: NodeObject | null) => void;
  getSelectedNode: () => NodeObject | null;
  setSelectedEdge: (edge: LinkObject | null) => void;
  getSelectedEdge: () => LinkObject | null;
}

type NodeProperty = {
  id: string;
  name: string;
  value: string;
};

const DEFAULT_GRAPH_SHAPE = "lr";

const GRAPH_SHAPES = [{
  value: "none",
  label: "None",
}, {
  value: "td",
  label: "Top-down",
}, {
  value: "bu",
  label: "Bottom-up",
}, {
  value: "lr",
  label: "Left-right",
}, {
  value: "rl",
  label: "Right-left",
}, {
  value: "radialin",
  label: "Radial-in",
}, {
  value: "radialout",
  label: "Radial-out",
}];

function formatValue(value: any, depth = 0): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map(v => "  ".repeat(depth) + "• " + formatValue(v, depth + 1)).join("\n");
  }
  if (typeof value === "object") {
    return Object.entries(value).map(([k, v]) =>
      "  ".repeat(depth) + `${k}: ${formatValue(v, depth + 1)}`
    ).join("\n");
  }
  return String(value);
}

function truncateText(text: string, maxLength = 200): string {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

export default function GraphControls({ data, isAddNodeFormOpen, onGraphShapeChange, onFitIntoView, ref, autoRotateShapes = false, floating = false }: GraphControlsProps) {
  const [selectedNode, setSelectedNode] = useState<NodeObject | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<LinkObject | null>(null);
  const [nodeProperties, setNodeProperties] = useState<NodeProperty[]>([]);
  const [newProperty, setNewProperty] = useState<NodeProperty>({
    id: uuid4(),
    name: "",
    value: "",
  });
  const [edgeExpanded, setEdgeExpanded] = useState(false);

  const handlePropertyChange = (property: NodeProperty, property_key: string, event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setNodeProperties(nodeProperties.map((nodeProperty) => (nodeProperty.id === property.id ? {...nodeProperty, [property_key]: value } : nodeProperty)));
  };

  const handlePropertyAdd = () => {
    if (newProperty.name && newProperty.value) {
      setNodeProperties([...nodeProperties, newProperty]);
      setNewProperty({ id: uuid4(), name: "", value: "" });
    } else {
      alert("Please fill in both name and value fields for the new property.");
    }
  };

  const handlePropertyDelete = (property: NodeProperty) => {
    setNodeProperties(nodeProperties.filter((nodeProperty) => nodeProperty.id !== property.id));
  };

  const handleNewPropertyChange = (property: NodeProperty, property_key: string, event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setNewProperty({...property, [property_key]: value });
  };

  useImperativeHandle(ref, () => ({
    setSelectedNode,
    getSelectedNode: () => selectedNode,
    setSelectedEdge,
    getSelectedEdge: () => selectedEdge,
  }));

  const handleGraphShapeControl = (event: ChangeEvent<HTMLSelectElement>) => {
    setIsAuthShapeChangeEnabled(false);
    onGraphShapeChange(event.target.value);
  };

  const [isAuthShapeChangeEnabled, setIsAuthShapeChangeEnabled] = useState(true);
  const shapeChangeTimeout = useRef<number | null>(null);

  useEffect(() => {
    onGraphShapeChange(DEFAULT_GRAPH_SHAPE);

    if (!autoRotateShapes) {
      setTimeout(() => {
        onFitIntoView();
      }, 400);
      return () => {};
    }

    const graphShapesNum = GRAPH_SHAPES.length;

    function switchShape(shapeIndex: number) {
      if (!isAuthShapeChangeEnabled || !data) {
        if (shapeChangeTimeout.current) {
          clearTimeout(shapeChangeTimeout.current);
          shapeChangeTimeout.current = null;
        }
        return;
      }

      shapeChangeTimeout.current = setTimeout(() => {
        const newValue = GRAPH_SHAPES[shapeIndex].value;
        onGraphShapeChange(newValue);
        const el = document.getElementById("graph-shape-select") as HTMLSelectElement | null;
        if (el) el.value = newValue;
        switchShape((shapeIndex + 1) % graphShapesNum);
      }, 5000) as unknown as number;
    }

    switchShape(0);

    setTimeout(() => {
      onFitIntoView();
    }, 500);

    return () => {
      if (shapeChangeTimeout.current) {
        clearTimeout(shapeChangeTimeout.current);
        shapeChangeTimeout.current = null;
      }
    };
  }, [data, isAuthShapeChangeEnabled, onFitIntoView, onGraphShapeChange, autoRotateShapes]);

  const renderNodeDetails = () => {
    if (!selectedNode) return <span className="text-gray-500">No node selected.</span>;

    const props = (selectedNode.properties || {}) as Record<string, any>;

    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">ID:</span>
            <span className="text-white text-xs break-all">{String(selectedNode.id)}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Label:</span>
            <span className="text-white text-xs">{selectedNode.label as string}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Type:</span>
            <span className="text-white text-xs">{(selectedNode as any).type as string}</span>
          </div>
        </div>

        {Object.keys(props).length > 0 && (
          <>
            <div style={{ height: 1, background: "rgba(255,255,255,0.08)" }} />
            <div className="flex flex-col gap-1">
              <span className="text-gray-400 text-xs uppercase tracking-wide mb-1">Properties</span>
              {Object.entries(props).map(([key, value]) => {
                const formatted = formatValue(value);
                const isLong = typeof value === "string" && value.length > 200;
                const displayValue = isLong && !edgeExpanded ? truncateText(value, 200) : formatted;

                return (
                  <div key={key} className="flex gap-2 items-start">
                    <span className="text-gray-400 text-xs whitespace-pre-wrap break-all">{key}:</span>
                    <span className="text-white text-xs whitespace-pre-wrap break-all flex-1">
                      {displayValue}
                      {isLong && (
                        <button
                          onClick={() => setEdgeExpanded(!edgeExpanded)}
                          className="ml-2 text-indigo-400 hover:text-indigo-300 underline text-xs"
                        >
                          {edgeExpanded ? "Collapse" : "Expand"}
                        </button>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    );
  };

  const renderEdgeDetails = () => {
    if (!selectedEdge) return null;

    const sourceId = typeof selectedEdge.source === "object" ? (selectedEdge.source as any)?.id : selectedEdge.source;
    const targetId = typeof selectedEdge.target === "object" ? (selectedEdge.target as any)?.id : selectedEdge.target;
    const truncateId = (id: any) => String(id).slice(0, 12);

    const props = (selectedEdge as any).properties || {};
    const edgeText = (selectedEdge as any).edge_text || "";
    const isLongText = edgeText.length > 200;

    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Source:</span>
            <span className="text-white text-xs break-all">{truncateId(sourceId)}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Target:</span>
            <span className="text-white text-xs break-all">{truncateId(targetId)}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Relationship:</span>
            <span className="text-white text-xs">{selectedEdge.label as string}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Type:</span>
            <span className="text-white text-xs">{(selectedEdge as any).relationship_type as string || selectedEdge.label as string}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Layer:</span>
            <span className="text-white text-xs">{(selectedEdge as any).inference_layer as string || "chunk"}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Implicit:</span>
            <span className="text-white text-xs">{(selectedEdge as any).implicit ? "Yes" : "No"}</span>
          </div>
          <div className="flex gap-2 items-top">
            <span className="text-gray-400 text-xs uppercase tracking-wide">Ontology:</span>
            <span className="text-white text-xs">{(selectedEdge as any).ontology_valid ? "Valid" : "Unknown"}</span>
          </div>
        </div>

        {edgeText && (
          <>
            <div style={{ height: 1, background: "rgba(255,255,255,0.08)" }} />
            <div className="flex flex-col gap-1">
              <span className="text-gray-400 text-xs uppercase tracking-wide mb-1">Edge Text</span>
              <span className="text-white text-xs whitespace-pre-wrap break-all">
                {isLongText && !edgeExpanded ? truncateText(edgeText, 200) : edgeText}
                {isLongText && (
                  <button
                    onClick={() => setEdgeExpanded(!edgeExpanded)}
                    className="ml-2 text-indigo-400 hover:text-indigo-300 underline text-xs"
                  >
                    {edgeExpanded ? "Collapse" : "Expand"}
                  </button>
                )}
              </span>
            </div>
          </>
        )}

        {Object.keys(props).length > 0 && (
          <>
            <div style={{ height: 1, background: "rgba(255,255,255,0.08)" }} />
            <div className="flex flex-col gap-1">
              <span className="text-gray-400 text-xs uppercase tracking-wide mb-1">Properties</span>
              <span className="text-white text-xs whitespace-pre-wrap break-all font-mono leading-relaxed">
                {formatValue(props)}
              </span>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="flex w-full">
        <span className="whitespace-nowrap text-white text-xs uppercase tracking-wide">
          {selectedEdge ? "Edge Details" : "Node Details"}
        </span>
      </div>

      <div className="pt-4">
        <>
          {!floating && (
            <div className="w-full flex flex-row gap-2 items-center mb-4">
              <label className="text-gray-300 whitespace-nowrap flex-1/5 text-xs">Graph Shape:</label>
              <Select defaultValue={DEFAULT_GRAPH_SHAPE} onChange={handleGraphShapeControl} id="graph-shape-select" className="flex-2/5">
                {GRAPH_SHAPES.map((shape) => (
                  <option key={shape.value} value={shape.value}>{shape.label}</option>
                ))}
              </Select>
              <NeutralButton onClick={onFitIntoView} className="flex-2/5 whitespace-nowrap text-xs">Fit Graph into View</NeutralButton>
            </div>
          )}

          {isAddNodeFormOpen ? (
            <form className="flex flex-col gap-4" onSubmit={() => {}}>
              <div className="flex flex-row gap-4 items-center">
                <span className="text-gray-300 whitespace-nowrap">Source Node ID:</span>
                <Input readOnly type="text" defaultValue={selectedNode!.id as any} />
              </div>
              <div className="flex flex-col gap-4 items-end">
                {nodeProperties.map((property) => (
                  <div key={property.id} className="w-full flex flex-row gap-2 items-center">
                    <Input className="flex-1/3" type="text" placeholder="Property name" required value={property.name} onChange={handlePropertyChange.bind(null, property, "name")} />
                    <Input className="flex-2/3" type="text" placeholder="Property value" required value={property.value} onChange={handlePropertyChange.bind(null, property, "value")} />
                    <button className="border-1 border-white p-2 rounded-sm" onClick={handlePropertyDelete.bind(null, property)}>
                      <DeleteIcon width={16} height={18} color="white" />
                    </button>
                  </div>
                ))}
                <div className="w-full flex flex-row gap-2 items-center">
                  <Input className="flex-1/3" type="text" placeholder="Property name" required value={newProperty.name} onChange={handleNewPropertyChange.bind(null, newProperty, "name")} />
                  <Input className="flex-2/3" type="text" placeholder="Property value" required value={newProperty.value} onChange={handleNewPropertyChange.bind(null, newProperty, "value")} />
                  <NeutralButton type="button" className="" onClick={handlePropertyAdd}>Add</NeutralButton>
                </div>
              </div>
              <CTAButton type="submit">Add Node</CTAButton>
            </form>
          ) : (
            selectedNode ? renderNodeDetails() : selectedEdge ? renderEdgeDetails() : (
              <span className="text-gray-500">No node or edge selected.</span>
            )
          )}
        </>
      </div>
    </>
  );
}
