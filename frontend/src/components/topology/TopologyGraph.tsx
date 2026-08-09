import React, { useMemo, useRef, useState } from "react";
import { Box, IconButton, Paper, Stack, Tooltip, Typography } from "@mui/material";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import { TopologyEdge, TopologyGraph as TopologyGraphData, TopologyNode } from "@/types";

interface TopologyGraphProps {
  graph: TopologyGraphData;
  focusNodeId?: string;
  selectedNodeId?: string;
  selectedEdgeId?: string;
  onSelectNode?: (node: TopologyNode) => void;
  onSelectEdge?: (edge: TopologyEdge) => void;
  height?: number;
}

interface Position {
  x: number;
  y: number;
}

const WIDTH = 1280;
const HEIGHT = 820;

export const RISK_COLORS: Record<string, string> = {
  high: "#D92D20",
  medium: "#F79009",
  low: "#12B76A",
};

const EDGE_STYLES: Record<string, { color: string; dash?: string; width: number }> = {
  network: { color: "#344054", width: 3 },
  vulnerability: { color: "#D92D20", dash: "8 5", width: 2.5 },
  risk: { color: "#F79009", dash: "5 4", width: 2.5 },
  identity: { color: "#7A5AF8", dash: "2 5", width: 2.5 },
  control: { color: "#0E9384", dash: "10 4", width: 2.5 },
  other: { color: "#98A2B3", width: 2 },
};

const nodeLayer = (node: TopologyNode) => {
  if (node.type === "NetworkSegment") return 0;
  if (node.type === "Asset") {
    if (["firewall", "router"].includes(node.asset_type ?? "")) return 1;
    if (["switch", "network_device"].includes(node.asset_type ?? "")) return 2;
    return 4;
  }
  if (node.type === "NetworkInterface") return 3;
  if (node.type === "Identity") return 5;
  if (node.type === "Vulnerability") return 5;
  if (node.type === "Risk") return 6;
  if (node.type === "Control") return 6;
  return 7;
};

export const layoutNodes = (nodes: TopologyNode[]): Map<string, Position> => {
  const positions = new Map<string, Position>();
  const layers = new Map<number, TopologyNode[]>();
  nodes.forEach((node) => {
    const layer = nodeLayer(node);
    layers.set(layer, [...(layers.get(layer) ?? []), node]);
  });

  Array.from(layers.entries()).forEach(([layer, layerNodes]) => {
    const ordered = [...layerNodes].sort((a, b) => a.label.localeCompare(b.label));
    const available = WIDTH - 140;
    const spacing = Math.min(210, available / Math.max(ordered.length, 1));
    const totalWidth = spacing * Math.max(ordered.length - 1, 0);
    const startX = WIDTH / 2 - totalWidth / 2;
    ordered.forEach((node, index) => positions.set(node.id, {
      x: startX + index * spacing,
      y: 72 + layer * 96,
    }));
  });
  return positions;
};

const nodeCode = (node: TopologyNode) => {
  if (node.type === "Vulnerability") return "CVE";
  if (node.type === "Risk") return "RISK";
  if (node.type === "Identity") return "USR";
  if (node.type === "Control") return "CTRL";
  if (node.type === "NetworkInterface") return "IF";
  if (node.type === "NetworkSegment") return "NET";
  const codes: Record<string, string> = {
    firewall: "FW", router: "RTR", switch: "SW", server: "SRV",
    database: "DB", application: "APP", endpoint: "PC", workstation: "PC",
    cloud: "CLD", cloud_resource: "CLD", network_device: "NET",
  };
  return codes[node.asset_type ?? ""] ?? "AST";
};

const nodeSize = (node: TopologyNode) => {
  if (node.type === "Asset") return { width: 176, height: 76 };
  if (node.type === "NetworkSegment") return { width: 170, height: 54 };
  if (node.type === "NetworkInterface") return { width: 132, height: 52 };
  return { width: 148, height: 62 };
};

const truncate = (value: string, max: number) => value.length > max ? `${value.slice(0, max - 1)}…` : value;

export const TopologyGraph = ({
  graph,
  focusNodeId,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  height = 760,
}: TopologyGraphProps) => {
  const positions = useMemo(() => layoutNodes(graph.nodes), [graph.nodes]);
  const [viewport, setViewport] = useState({ x: 0, y: 0, scale: 1 });
  const dragStart = useRef<{ pointerX: number; pointerY: number; x: number; y: number } | null>(null);

  const selection = useMemo(() => {
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();
    const activeNode = selectedNodeId || focusNodeId;
    if (activeNode) {
      nodeIds.add(activeNode);
      graph.edges.forEach((edge) => {
        if (edge.source === activeNode || edge.target === activeNode) {
          edgeIds.add(edge.id);
          nodeIds.add(edge.source);
          nodeIds.add(edge.target);
        }
      });
    }
    if (selectedEdgeId) {
      const edge = graph.edges.find((item) => item.id === selectedEdgeId);
      if (edge) {
        edgeIds.add(edge.id);
        nodeIds.add(edge.source);
        nodeIds.add(edge.target);
      }
    }
    return { nodeIds, edgeIds, active: Boolean(activeNode || selectedEdgeId) };
  }, [focusNodeId, graph.edges, selectedEdgeId, selectedNodeId]);

  const zoomBy = (factor: number) => setViewport((current) => ({
    ...current,
    scale: Math.min(2.5, Math.max(0.42, current.scale * factor)),
  }));

  if (graph.nodes.length === 0) {
    return <Paper variant="outlined" sx={{ height, display: "grid", placeItems: "center", p: 3 }}><Typography color="text.secondary">No topology entities match the current view.</Typography></Paper>;
  }

  return (
    <Paper variant="outlined" sx={{ position: "relative", overflow: "hidden", height, bgcolor: "#F8FAFC" }}>
      <Stack direction="row" spacing={0.5} sx={{ position: "absolute", zIndex: 2, top: 10, right: 10, bgcolor: "white", borderRadius: 1, boxShadow: 1 }}>
        <Tooltip title="Zoom in"><IconButton size="small" onClick={() => zoomBy(1.2)}><ZoomInIcon /></IconButton></Tooltip>
        <Tooltip title="Zoom out"><IconButton size="small" onClick={() => zoomBy(0.8)}><ZoomOutIcon /></IconButton></Tooltip>
        <Tooltip title="Fit topology"><IconButton size="small" onClick={() => setViewport({ x: 0, y: 0, scale: 1 })}><CenterFocusStrongIcon /></IconButton></Tooltip>
      </Stack>
      <Box
        component="svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} sx={{ width: "100%", height: "100%", cursor: dragStart.current ? "grabbing" : "grab" }}
        onWheel={(event: React.WheelEvent<SVGSVGElement>) => { event.preventDefault(); zoomBy(event.deltaY < 0 ? 1.1 : 0.9); }}
        onPointerDown={(event: React.PointerEvent<SVGSVGElement>) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          dragStart.current = { pointerX: event.clientX, pointerY: event.clientY, x: viewport.x, y: viewport.y };
        }}
        onPointerMove={(event: React.PointerEvent<SVGSVGElement>) => {
          if (!dragStart.current) return;
          setViewport((current) => ({ ...current, x: dragStart.current!.x + event.clientX - dragStart.current!.pointerX, y: dragStart.current!.y + event.clientY - dragStart.current!.pointerY }));
        }}
        onPointerUp={() => { dragStart.current = null; }} onPointerCancel={() => { dragStart.current = null; }}
      >
        <defs>
          {Object.entries(EDGE_STYLES).map(([category, style]) => (
            <marker key={category} id={`arrow-${category}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill={style.color} />
            </marker>
          ))}
          <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.16" /></filter>
        </defs>
        <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
          {graph.edges.map((edge) => {
            const source = positions.get(edge.source);
            const target = positions.get(edge.target);
            if (!source || !target) return null;
            const style = EDGE_STYLES[edge.category] ?? EDGE_STYLES.other;
            const active = !selection.active || selection.edgeIds.has(edge.id);
            const midpoint = { x: (source.x + target.x) / 2, y: (source.y + target.y) / 2 };
            const interfaceLabel = [edge.source_interface, edge.target_interface].filter(Boolean).join(" ↔ ");
            const protocol = [edge.properties.protocol, edge.properties.port].filter(Boolean).join("/");
            const detail = [interfaceLabel, protocol].filter(Boolean).join(" · ");
            return (
              <g key={edge.id} opacity={active ? 1 : 0.12} onClick={(event) => { event.stopPropagation(); onSelectEdge?.(edge); }} style={{ cursor: "pointer" }}>
                <title>{`${edge.type.replace(/_/g, " ")}${detail ? ` — ${detail}` : ""}`}</title>
                <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke={style.color} strokeWidth={selectedEdgeId === edge.id ? style.width + 2 : style.width} strokeDasharray={style.dash} markerEnd={`url(#arrow-${edge.category in EDGE_STYLES ? edge.category : "other"})`} />
                <rect x={midpoint.x - 82} y={midpoint.y - 17} width="164" height={detail ? 31 : 20} rx="7" fill="#FFFFFF" stroke="#D0D5DD" />
                <text x={midpoint.x} y={midpoint.y - 4} textAnchor="middle" fontSize="10" fontWeight="700" fill={style.color}>{truncate(edge.type.replace(/_/g, " "), 24)}</text>
                {detail && <text x={midpoint.x} y={midpoint.y + 9} textAnchor="middle" fontSize="9" fill="#475467">{truncate(detail, 31)}</text>}
              </g>
            );
          })}

          {graph.nodes.map((node) => {
            const position = positions.get(node.id);
            if (!position) return null;
            const size = nodeSize(node);
            const selected = selectedNodeId === node.id || focusNodeId === node.id || focusNodeId === node.entity_id;
            const active = !selection.active || selection.nodeIds.has(node.id);
            const riskColor = RISK_COLORS[node.risk_level ?? "low"];
            const asset = node.type === "Asset";
            const colors: Record<string, { fill: string; stroke: string }> = {
              Vulnerability: { fill: "#FFF1F3", stroke: "#D92D20" }, Risk: { fill: "#FFF6ED", stroke: "#F79009" },
              Identity: { fill: "#F4F3FF", stroke: "#7A5AF8" }, Control: { fill: "#F0FDF9", stroke: "#0E9384" },
              NetworkInterface: { fill: "#EFF8FF", stroke: "#1570EF" }, NetworkSegment: { fill: "#F2F4F7", stroke: "#667085" },
            };
            const tone = asset ? { fill: "#FFFFFF", stroke: riskColor } : (colors[node.type] ?? { fill: "#FFFFFF", stroke: "#667085" });
            return (
              <g key={node.id} transform={`translate(${position.x} ${position.y})`} opacity={active ? 1 : 0.16} onClick={(event) => { event.stopPropagation(); onSelectNode?.(node); }} style={{ cursor: "pointer" }} role="button" aria-label={`${node.type}: ${node.label}`}>
                <title>{`${node.label}${node.ip_address ? ` — ${node.ip_address}` : ""}`}</title>
                <rect x={-size.width / 2} y={-size.height / 2} width={size.width} height={size.height} rx={node.type === "Identity" ? 28 : 10} fill={tone.fill} stroke={selected ? "#101828" : tone.stroke} strokeWidth={selected ? 5 : asset ? 4 : 2.5} strokeDasharray={node.type === "NetworkSegment" ? "8 4" : undefined} filter="url(#node-shadow)" />
                <rect x={-size.width / 2 + 8} y={-size.height / 2 + 9} width="40" height={size.height - 18} rx="8" fill={tone.stroke} />
                <text x={-size.width / 2 + 28} y="5" textAnchor="middle" fontSize="11" fontWeight="800" fill="#FFFFFF">{nodeCode(node)}</text>
                <text x={-size.width / 2 + 56} y="-14" fontSize="11" fontWeight="800" fill="#101828">{truncate(node.label, asset ? 20 : 16)}</text>
                <text x={-size.width / 2 + 56} y="3" fontSize="9.5" fill="#475467">{asset ? truncate(node.ip_address ?? "IP not reported", 21) : truncate(node.type.replace(/_/g, " "), 18)}</text>
                <text x={-size.width / 2 + 56} y="20" fontSize="9" fill="#667085">{asset ? `${(node.asset_type ?? "asset").replace(/_/g, " ")} · ${node.criticality ?? "unknown"}` : truncate(String(node.properties.status ?? node.properties.zone ?? ""), 20)}</text>
                {asset && <circle cx={size.width / 2 - 12} cy={-size.height / 2 + 12} r="7" fill={riskColor}><title>{`${node.risk_level ?? "low"} risk`}</title></circle>}
              </g>
            );
          })}
        </g>
      </Box>
    </Paper>
  );
};
