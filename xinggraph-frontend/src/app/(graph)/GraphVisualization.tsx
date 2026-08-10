"use client";

import dynamic from "next/dynamic";
import classNames from "classnames";
import { MutableRefObject, useEffect, useImperativeHandle, useRef, useState, useCallback } from "react";
import { ForceGraphMethods, GraphData, LinkObject, NodeObject } from "react-force-graph-2d";
import { GraphControlsAPI } from "./GraphControls";
import getColorForNodeType from "./getColorForNodeType";


const ForceGraph = dynamic(() => import("react-force-graph-2d"), {
  ssr: false, // disables SSR (important if the lib touches `window`)
});

const ARROW_LENGTH = 4;

interface GraphVisuzaliationProps {
  ref: MutableRefObject<GraphVisualizationAPI | null>;
  data?: GraphData<NodeObject, LinkObject>;
  graphControls: MutableRefObject<GraphControlsAPI | null>;
  className?: string;
}

export interface GraphVisualizationAPI {
  zoomToFit: ForceGraphMethods["zoomToFit"];
  setGraphShape: (shape: string) => void;
}

export default function GraphVisualization({ ref, data, graphControls, className }: GraphVisuzaliationProps) {
  const textSize = 6;
  const nodeSize = 15;
  // const addNodeDistanceFromSourceNode = 15;

  // State for tracking container dimensions
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const hoveredEdgeRef = useRef<LinkObject | null>(null);
  const selectedEdgeRef = useRef<LinkObject | null>(null);

  const handleResize = useCallback(() => {
    if (containerRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      setDimensions({ width: clientWidth, height: clientHeight });

      // Trigger graph refresh after resize
      if (graphRef.current) {
        // Small delay to ensure DOM has updated
        setTimeout(() => {
          graphRef.current?.zoomToFit(1000,50);
        }, 100);
      }
    }
  }, []);

  // Set up resize observer
  useEffect(() => {
    // Initial size calculation
    handleResize();

    // ResizeObserver
    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, [handleResize]);

  const handleNodeClick = (node: NodeObject) => {
    graphControls.current?.setSelectedNode(node);
    // ref.current?.d3ReheatSimulation()
  }

  const handleBackgroundClick = () => {
    const selectedNode = graphControls.current?.getSelectedNode();
    if (!selectedNode) return;
    graphControls.current?.setSelectedNode(null);
    selectedEdgeRef.current = null;
    graphControls.current?.setSelectedEdge(null);
  };

  const handleLinkClick = (link: LinkObject) => {
    selectedEdgeRef.current = link;
    graphControls.current?.setSelectedEdge(link);
    graphControls.current?.setSelectedNode(null);
  };

  const handleLinkHover = (link: LinkObject | null) => {
    hoveredEdgeRef.current = link;
  };

  function renderNode(node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number, renderType: string = "replace") {
    ctx.save();

    if (renderType === "replace") {
      ctx.fillStyle = getColorForNodeType(node.type);
      drawNodeShape(ctx, node);
    }

    const textPos = {
      x: node.x!,
      y: node.y!,
    };

    ctx.translate(textPos.x, textPos.y);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#333333";
    ctx.font = `${textSize}px Sans-Serif`;
    ctx.fillText(node.label, 0, 0);

    ctx.restore();
  }

  function drawNodeShape(ctx: CanvasRenderingContext2D, node: NodeObject) {
    const x = node.x!;
    const y = node.y!;
    const size = nodeSize;
    const nodeType = node.type || "";

    ctx.beginPath();

    if (nodeType === "EntityType") {
      drawDiamond(ctx, x, y, size);
    } else if (nodeType === "DocumentChunk") {
      drawRoundedRect(ctx, x, y, size * 1.6, size * 1.2, 4);
    } else if (nodeType === "ChunkWiki") {
      drawHexagon(ctx, x, y, size);
    } else {
      ctx.arc(x, y, size, 0, 2 * Math.PI);
    }

    ctx.fill();
  }

  function drawDiamond(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
    ctx.moveTo(x, y - size);
    ctx.lineTo(x + size, y);
    ctx.lineTo(x, y + size);
    ctx.lineTo(x - size, y);
    ctx.closePath();
  }

  function drawRoundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
    ctx.roundRect(x - w / 2, y - h / 2, w, h, r);
  }

  function drawHexagon(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      const hx = x + size * Math.cos(angle);
      const hy = y + size * Math.sin(angle);
      if (i === 0) ctx.moveTo(hx, hy);
      else ctx.lineTo(hx, hy);
    }
    ctx.closePath();
  }

  function getEdgeStyle(link: LinkObject): { color: string; dasharray: number[]; width: number; showArrow: boolean } {
    const inferenceLayer = (link as any).inference_layer || "chunk";
    const relationshipType = link.label || "";

    if (relationshipType === "has_wiki") {
      return { color: "#22d3ee", dasharray: [], width: 1.5, showArrow: true };
    }
    if (relationshipType === "is_a") {
      return { color: "#f97316", dasharray: [], width: 1.5, showArrow: true };
    }
    if (relationshipType === "co_occurs_with") {
      return { color: "#9ca3af", dasharray: [6, 4], width: 1, showArrow: false };
    }

    switch (inferenceLayer) {
      case "propagation":
        return { color: "#4ade80", dasharray: [3, 3], width: 1.2, showArrow: false };
      case "co-occurrence":
        return { color: "#9ca3af", dasharray: [8, 5], width: 1, showArrow: false };
      case "llm":
        return { color: "#a78bfa", dasharray: [10, 2, 2, 2], width: 1.5, showArrow: false };
      case "chunk":
      default:
        return { color: "#60a5fa", dasharray: [], width: 1.5, showArrow: true };
    }
  }

  function drawArrowhead(ctx: CanvasRenderingContext2D, fromX: number, fromY: number, toX: number, toY: number, color: string) {
    const angle = Math.atan2(toY - fromY, toX - fromX);
    const tipX = toX - Math.cos(angle) * nodeSize;
    const tipY = toY - Math.sin(angle) * nodeSize;
    ctx.save();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(tipX, tipY);
    ctx.lineTo(tipX - ARROW_LENGTH * Math.cos(angle - Math.PI / 6), tipY - ARROW_LENGTH * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(tipX - ARROW_LENGTH * Math.cos(angle + Math.PI / 6), tipY - ARROW_LENGTH * Math.sin(angle + Math.PI / 6));
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function renderLink(link: LinkObject, ctx: CanvasRenderingContext2D) {
    const MAX_FONT_SIZE = 4;
    const LABEL_NODE_MARGIN = nodeSize * 1.5;

    const start = link.source;
    const end = link.target;

    if (typeof start !== "object" || typeof end !== "object") return;

    const isHovered = hoveredEdgeRef.current === link;
    const isSelected = selectedEdgeRef.current === link;
    const hasActiveEdge = hoveredEdgeRef.current !== null || selectedEdgeRef.current !== null;

    let alpha = 1;
    let edgeStyle = getEdgeStyle(link);

    if (isHovered || isSelected) {
      alpha = 1;
      edgeStyle = { color: "#ffffff", dasharray: [], width: 2.5, showArrow: true };
    } else if (hasActiveEdge) {
      alpha = 0.15;
    }

    const textPos = {
      x: start.x! + (end.x! - start.x!) / 2,
      y: start.y! + (end.y! - start.y!) / 2,
    };

    const relLink = { x: end.x! - start.x!, y: end.y! - start.y! };

    const maxTextLength = Math.sqrt(Math.pow(relLink.x, 2) + Math.pow(relLink.y, 2)) - LABEL_NODE_MARGIN * 2;

    let textAngle = Math.atan2(relLink.y, relLink.x);
    if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
    if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);

    const label = link.label;

    ctx.font = "1px Sans-Serif";
    const fontSize = Math.min(MAX_FONT_SIZE, maxTextLength / ctx.measureText(label).width);
    ctx.font = `${fontSize}px Sans-Serif`;
    const textWidth = ctx.measureText(label).width;
    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = edgeStyle.color;
    ctx.lineWidth = edgeStyle.width;
    ctx.setLineDash(edgeStyle.dasharray);
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(start.x!, start.y!);
    ctx.lineTo(end.x!, end.y!);
    ctx.stroke();
    ctx.setLineDash([]);

    if (edgeStyle.showArrow) {
      drawArrowhead(ctx, start.x!, start.y!, end.x!, end.y!, edgeStyle.color);
    }
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(textPos.x, textPos.y);
    ctx.rotate(textAngle);
    ctx.fillStyle = `rgba(255, 255, 255, ${alpha * 0.85})`;
    ctx.fillRect(- bckgDimensions[0] / 2, - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = `rgba(51, 51, 51, ${alpha})`;
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }

  function renderInitialNode(node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) {
    renderNode(node, ctx, globalScale, "after");
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  function handleDagError(loopNodeIds: (string | number)[]) {}

  // @ts-expect-error nothing to define
  const graphRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    async function startAnimation() {
      const { forceCollide, forceManyBody } = await import("d3-force-3d");

      if (typeof window !== "undefined" && data && graphRef.current) {
        // add collision force
        graphRef.current.d3Force("collision", forceCollide(nodeSize * 1.5));
        graphRef.current.d3Force("charge", forceManyBody().strength(-10).distanceMin(10).distanceMax(50));
      }
    }
    startAnimation();
  }, [data, graphRef]);

  const [graphShape, setGraphShape] = useState<string>();

  useImperativeHandle(ref, () => ({
    zoomToFit: graphRef.current?.zoomToFit,
    setGraphShape: setGraphShape,
  }));

  return (
    <div ref={containerRef} className={classNames("w-full h-full", className)} id="graph-container">
      {(data && typeof window !== "undefined") ? (
        <ForceGraph
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          dagMode={graphShape as unknown as undefined}
          dagLevelDistance={300}
          onDagError={handleDagError}
          graphData={data}

          nodeLabel="label"
          nodeRelSize={nodeSize}
          nodeCanvasObject={renderNode}
          nodeCanvasObjectMode={() => "replace"}

          linkLabel="label"
          linkCanvasObject={renderLink}
          linkCanvasObjectMode={() => "replace"}
          linkDirectionalArrowLength={ARROW_LENGTH}
          linkDirectionalArrowRelPos={1}

          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          onLinkClick={handleLinkClick}
          onLinkHover={handleLinkHover}
          onNodeDragEnd={(node) => { node.fx = node.x; node.fy = node.y; }}
          d3VelocityDecay={0.5}
        />
      ) : (
        <ForceGraph
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          dagMode={graphShape as unknown as undefined}
          dagLevelDistance={100}
          graphData={{
            nodes: [{ id: 1, label: "Add" }, { id: 2, label: "Cognify" }, { id: 3, label: "Search" }],
            links: [{ source: 1, target: 2, label: "but don't forget to" }, { source: 2, target: 3, label: "and after that you can" }],
          }}

          nodeLabel="label"
          nodeRelSize={20}
          nodeCanvasObject={renderInitialNode}
          nodeCanvasObjectMode={() => "replace"}
          nodeAutoColorBy="type"

          linkLabel="label"
          linkCanvasObject={renderLink}
          linkCanvasObjectMode={() => "replace"}
          linkDirectionalArrowLength={ARROW_LENGTH}
          linkDirectionalArrowRelPos={1}
        />
      )}
    </div>
  );
}
