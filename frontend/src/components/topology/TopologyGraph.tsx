import React, { useMemo, useRef, useState } from "react";
import { Box, IconButton, Paper, Stack, Tooltip, Typography } from "@mui/material";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import { TopologyGraph as TopologyGraphData, TopologyNode } from "@/types";

interface TopologyGraphProps {
  graph: TopologyGraphData;
  focusNodeId?: string;
  selectedNodeId?: string;
  onSelectNode?: (node: TopologyNode) => void;
  height?: number;
}

interface Position {
  x: number;
  y: number;
}

const WIDTH = 1000;
const HEIGHT = 620;

const NODE_COLORS: Record<string, string> = {
  Asset: "#1E3A5F",
  Identity: "#7B1FA2",
  Vulnerability: "#D32F2F",
  Risk: "#F57C00",
  Control: "#2FA6A6",
  Policy: "#5D6D7E",
  Framework: "#43A047",
};

const nodeColor = (type: string) => NODE_COLORS[type] ?? "#607D8B";

const layoutNodes = (nodes: TopologyNode[], focusNodeId?: string): Map<string, Position> => {
  const positions = new Map<string, Position>();
  if (nodes.length === 0) return positions;

  const center = { x: WIDTH / 2, y: HEIGHT / 2 };
  const focusIndex = focusNodeId
    ? nodes.findIndex((node) => node.id === focusNodeId || node.entity_id === focusNodeId)
    : -1;
  const ordered = [...nodes];
  if (focusIndex >= 0) {
    const [focus] = ordered.splice(focusIndex, 1);
    positions.set(focus.id, center);
  }

  const count = ordered.length;
  const ringSize = 12;
  ordered.forEach((node, index) => {
    const ring = Math.floor(index / ringSize);
    const ringStart = ring * ringSize;
    const nodesInRing = Math.min(ringSize, count - ringStart);
    const angle = ((index - ringStart) / Math.max(nodesInRing, 1)) * Math.PI * 2 - Math.PI / 2;
    const radius = (focusIndex >= 0 ? 205 : 145) + ring * 125;
    positions.set(node.id, {
      x: center.x + Math.cos(angle) * radius,
      y: center.y + Math.sin(angle) * radius,
    });
  });

  if (focusIndex < 0 && nodes.length === 1) positions.set(nodes[0].id, center);
  return positions;
};

export const TopologyGraph = ({
  graph,
  focusNodeId,
  selectedNodeId,
  onSelectNode,
  height = 620,
}: TopologyGraphProps) => {
  const positions = useMemo(() => layoutNodes(graph.nodes, focusNodeId), [graph.nodes, focusNodeId]);
  const [viewport, setViewport] = useState({ x: 0, y: 0, scale: 1 });
  const dragStart = useRef<{ pointerX: number; pointerY: number; x: number; y: number } | null>(null);

  const zoomBy = (factor: number) => {
    setViewport((current) => ({
      ...current,
      scale: Math.min(2.5, Math.max(0.45, current.scale * factor)),
    }));
  };

  const handlePointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStart.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      x: viewport.x,
      y: viewport.y,
    };
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!dragStart.current) return;
    setViewport((current) => ({
      ...current,
      x: dragStart.current!.x + (event.clientX - dragStart.current!.pointerX),
      y: dragStart.current!.y + (event.clientY - dragStart.current!.pointerY),
    }));
  };

  const endDrag = () => {
    dragStart.current = null;
  };

  if (graph.nodes.length === 0) {
    return (
      <Paper variant="outlined" sx={{ height, display: "grid", placeItems: "center", p: 3 }}>
        <Typography color="text.secondary">No connected entities match the current view.</Typography>
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ position: "relative", overflow: "hidden", height }}>
      <Stack direction="row" spacing={0.5} sx={{ position: "absolute", zIndex: 2, top: 8, right: 8 }}>
        <Tooltip title="Zoom in"><IconButton size="small" onClick={() => zoomBy(1.2)}><ZoomInIcon /></IconButton></Tooltip>
        <Tooltip title="Zoom out"><IconButton size="small" onClick={() => zoomBy(0.8)}><ZoomOutIcon /></IconButton></Tooltip>
        <Tooltip title="Reset view">
          <IconButton size="small" onClick={() => setViewport({ x: 0, y: 0, scale: 1 })}>
            <CenterFocusStrongIcon />
          </IconButton>
        </Tooltip>
      </Stack>
      <Box
        component="svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        sx={{ width: "100%", height: "100%", cursor: dragStart.current ? "grabbing" : "grab", bgcolor: "#F7F9FC" }}
        onWheel={(event: React.WheelEvent<SVGSVGElement>) => {
          event.preventDefault();
          zoomBy(event.deltaY < 0 ? 1.1 : 0.9);
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <defs>
          <marker id="topology-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#91A0B2" />
          </marker>
        </defs>
        <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
          {graph.edges.map((edge) => {
            const source = positions.get(edge.source);
            const target = positions.get(edge.target);
            if (!source || !target) return null;
            const midpoint = { x: (source.x + target.x) / 2, y: (source.y + target.y) / 2 };
            return (
              <g key={edge.id}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#91A0B2"
                  strokeWidth="2"
                  markerEnd="url(#topology-arrow)"
                />
                <text x={midpoint.x} y={midpoint.y - 6} textAnchor="middle" fontSize="10" fill="#526273">
                  {edge.type.replace(/_/g, " ")}
                </text>
              </g>
            );
          })}
          {graph.nodes.map((node) => {
            const position = positions.get(node.id);
            if (!position) return null;
            const selected = selectedNodeId === node.id;
            const focused = focusNodeId === node.id || focusNodeId === node.entity_id;
            return (
              <g
                key={node.id}
                transform={`translate(${position.x} ${position.y})`}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectNode?.(node);
                }}
                style={{ cursor: "pointer" }}
                role="button"
                aria-label={`${node.type}: ${node.label}`}
              >
                <circle
                  r={focused ? 44 : 37}
                  fill={nodeColor(node.type)}
                  stroke={selected || focused ? "#111827" : "#FFFFFF"}
                  strokeWidth={selected || focused ? 5 : 3}
                />
                <text y="-4" textAnchor="middle" fontSize="10" fontWeight="700" fill="#FFFFFF">
                  {node.type.toUpperCase()}
                </text>
                <text y="12" textAnchor="middle" fontSize="11" fill="#FFFFFF">
                  {node.label.length > 18 ? `${node.label.slice(0, 16)}…` : node.label}
                </text>
              </g>
            );
          })}
        </g>
      </Box>
    </Paper>
  );
};
