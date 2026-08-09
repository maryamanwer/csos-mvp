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

interface ZoneLayout {
  id: string;
  label: string;
  x: number;
  width: number;
  fill: string;
  stroke: string;
  virtual?: boolean;
}

export interface TopologyLayout {
  positions: Map<string, Position>;
  zones: ZoneLayout[];
  width: number;
  height: number;
  securityStartY: number;
}

type RiskLevel = "high" | "medium" | "low" | "unknown";

export const RISK_COLORS: Record<RiskLevel, string> = {
  high: "#D92D20",
  medium: "#F79009",
  low: "#12B76A",
  unknown: "#667085",
};

const EDGE_STYLES: Record<string, { color: string; dash?: string; width: number }> = {
  network: { color: "#344054", width: 3 },
  vulnerability: { color: "#D92D20", dash: "8 5", width: 2.5 },
  risk: { color: "#F79009", dash: "5 4", width: 2.5 },
  identity: { color: "#7A5AF8", dash: "2 5", width: 2.5 },
  control: { color: "#0E9384", dash: "10 4", width: 2.5 },
  other: { color: "#98A2B3", width: 2 },
};

const ZONE_TONES = [
  { fill: "#FFF7ED", stroke: "#FB923C" },
  { fill: "#EFF8FF", stroke: "#2E90FA" },
  { fill: "#F0FDF9", stroke: "#12B76A" },
  { fill: "#F4F3FF", stroke: "#7A5AF8" },
  { fill: "#FDF2FA", stroke: "#EE46BC" },
  { fill: "#F8FAFC", stroke: "#667085" },
];

const INFRASTRUCTURE_TYPES = new Set(["firewall", "router", "switch", "network_device"]);
const PRIMARY_NETWORK_RELATIONSHIPS = new Set([
  "CONNECTS_TO", "CONNECTED_TO", "COMMUNICATES_WITH", "DEPENDS_ON", "HOSTS",
  "PROTECTED_BY", "PROTECTS", "CONNECTED_THROUGH",
]);
const LABELLED_RELATIONSHIPS = new Set([
  "CONNECTS_TO", "CONNECTED_TO", "COMMUNICATES_WITH", "DEPENDS_ON", "HOSTS", "PROTECTS",
]);

const normalized = (value: unknown) => String(value ?? "").trim().toLowerCase();

export const resolveNodeRiskLevel = (node: TopologyNode): RiskLevel => {
  if (node.risk_level && ["high", "medium", "low"].includes(node.risk_level)) {
    return node.risk_level;
  }
  const score = Number(node.properties.risk_score);
  if (Number.isFinite(score) && score > 0) {
    if (score >= 70) return "high";
    if (score >= 40) return "medium";
    return "low";
  }
  const criticality = normalized(node.criticality ?? node.properties.criticality);
  if (criticality === "critical" || criticality === "high") return "high";
  if (criticality === "medium") return "medium";
  if (criticality === "low") return "low";
  return "unknown";
};

const segmentRank = (node: TopologyNode) => {
  const label = normalized(node.label);
  if (label.includes("internet") || label.includes("external")) return 0;
  if (label.includes("dmz")) return 1;
  if (label.includes("application") || label.includes("app")) return 2;
  if (label.includes("data") || label.includes("database")) return 3;
  if (label.includes("user") || label.includes("lan") || label.includes("endpoint")) return 4;
  return 10;
};

const nodeSize = (node: TopologyNode) => {
  if (node.type === "Asset") return { width: 206, height: 82 };
  if (node.type === "NetworkSegment") return { width: 214, height: 58 };
  if (node.type === "NetworkInterface") return { width: 154, height: 54 };
  return { width: 170, height: 66 };
};

const chooseZone = (
  asset: TopologyNode,
  candidates: string[],
  zoneIndex: Map<string, number>,
) => {
  const ordered = candidates
    .filter((id, index) => candidates.indexOf(id) === index)
    .sort((a, b) => (zoneIndex.get(a) ?? 999) - (zoneIndex.get(b) ?? 999));
  if (!ordered.length) return undefined;
  if (INFRASTRUCTURE_TYPES.has(normalized(asset.asset_type))) return ordered[0];
  return ordered[Math.floor((ordered.length - 1) / 2)];
};

const spreadSecurityRow = (
  nodes: TopologyNode[],
  positions: Map<string, Position>,
  graph: TopologyGraphData,
  width: number,
  y: number,
) => {
  const preferred = nodes.map((node) => {
    const connectedX = graph.edges
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .map((edge) => positions.get(edge.source === node.id ? edge.target : edge.source)?.x)
      .filter((value): value is number => value !== undefined);
    return { node, x: connectedX.length ? connectedX.reduce((sum, value) => sum + value, 0) / connectedX.length : width / 2 };
  }).sort((a, b) => a.x - b.x || a.node.label.localeCompare(b.node.label));

  if (!preferred.length) return;
  const usable = width - 180;
  const step = Math.min(230, usable / Math.max(preferred.length - 1, 1));
  const total = step * Math.max(preferred.length - 1, 0);
  const start = width / 2 - total / 2;
  preferred.forEach(({ node }, index) => positions.set(node.id, { x: start + index * step, y }));
};

export const layoutTopologyGraph = (graph: TopologyGraphData): TopologyLayout => {
  const positions = new Map<string, Position>();
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const segments = graph.nodes
    .filter((node) => node.type === "NetworkSegment")
    .sort((a, b) => segmentRank(a) - segmentRank(b) || a.label.localeCompare(b.label));
  const interfaces = graph.nodes.filter((node) => node.type === "NetworkInterface");
  const assets = graph.nodes.filter((node) => node.type === "Asset");

  const segmentByInterface = new Map<string, string>();
  graph.edges.forEach((edge) => {
    if (edge.type !== "LOCATED_IN") return;
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (source?.type === "NetworkInterface" && target?.type === "NetworkSegment") segmentByInterface.set(source.id, target.id);
    if (target?.type === "NetworkInterface" && source?.type === "NetworkSegment") segmentByInterface.set(target.id, source.id);
  });

  const interfacesByAsset = new Map<string, string[]>();
  graph.edges.forEach((edge) => {
    if (edge.type !== "HAS_INTERFACE") return;
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    const assetId = source?.type === "Asset" ? source.id : target?.type === "Asset" ? target.id : undefined;
    const interfaceId = source?.type === "NetworkInterface" ? source.id : target?.type === "NetworkInterface" ? target.id : undefined;
    if (assetId && interfaceId) interfacesByAsset.set(assetId, [...(interfacesByAsset.get(assetId) ?? []), interfaceId]);
  });

  const zoneByAsset = new Map<string, string>();
  assets.forEach((asset) => {
    const direct = (interfacesByAsset.get(asset.id) ?? []).map((id) => segmentByInterface.get(id)).filter((id): id is string => Boolean(id));
    if (direct.length) zoneByAsset.set(asset.id, direct[0]);
  });

  const zoneIndex = new Map(segments.map((segment, index) => [segment.id, index]));
  for (let pass = 0; pass < assets.length; pass += 1) {
    let changed = false;
    assets.filter((asset) => !zoneByAsset.has(asset.id)).forEach((asset) => {
      const candidates = graph.edges
        .filter((edge) => PRIMARY_NETWORK_RELATIONSHIPS.has(edge.type) && (edge.source === asset.id || edge.target === asset.id))
        .map((edge) => edge.source === asset.id ? edge.target : edge.source)
        .map((id) => zoneByAsset.get(id))
        .filter((id): id is string => Boolean(id));
      const zone = chooseZone(asset, candidates, zoneIndex);
      if (zone) {
        zoneByAsset.set(asset.id, zone);
        changed = true;
      }
    });
    if (!changed) break;
  }

  const needsSharedZone = assets.some((asset) => !zoneByAsset.has(asset.id));
  const zoneCount = Math.max(1, segments.length + (needsSharedZone ? 1 : 0));
  const width = Math.max(1720, zoneCount * 310 + 120);
  const gap = 24;
  const side = 42;
  const zoneWidth = (width - side * 2 - gap * (zoneCount - 1)) / zoneCount;
  const zones: ZoneLayout[] = segments.map((segment, index) => ({
    id: segment.id,
    label: segment.label,
    x: side + index * (zoneWidth + gap),
    width: zoneWidth,
    fill: ZONE_TONES[index % ZONE_TONES.length].fill,
    stroke: ZONE_TONES[index % ZONE_TONES.length].stroke,
  }));
  if (needsSharedZone) {
    const index = zones.length;
    zones.push({
      id: "__shared__",
      label: "Core & Shared Services",
      x: side + index * (zoneWidth + gap),
      width: zoneWidth,
      fill: ZONE_TONES[index % ZONE_TONES.length].fill,
      stroke: ZONE_TONES[index % ZONE_TONES.length].stroke,
      virtual: true,
    });
    assets.filter((asset) => !zoneByAsset.has(asset.id)).forEach((asset) => zoneByAsset.set(asset.id, "__shared__"));
  }

  const zoneById = new Map(zones.map((zone) => [zone.id, zone]));
  segments.forEach((segment) => {
    const zone = zoneById.get(segment.id);
    if (zone) positions.set(segment.id, { x: zone.x + zone.width / 2, y: 76 });
  });

  let maximumZoneBottom = 600;
  zones.forEach((zone) => {
    const centerX = zone.x + zone.width / 2;
    const zoneAssets = assets.filter((asset) => zoneByAsset.get(asset.id) === zone.id);
    const infrastructure = zoneAssets.filter((asset) => INFRASTRUCTURE_TYPES.has(normalized(asset.asset_type))).sort((a, b) => a.label.localeCompare(b.label));
    const workloads = zoneAssets.filter((asset) => !INFRASTRUCTURE_TYPES.has(normalized(asset.asset_type))).sort((a, b) => a.label.localeCompare(b.label));
    infrastructure.forEach((asset, index) => positions.set(asset.id, { x: centerX, y: 185 + index * 104 }));

    const zoneInterfaces = interfaces
      .filter((networkInterface) => segmentByInterface.get(networkInterface.id) === zone.id)
      .sort((a, b) => a.label.localeCompare(b.label));
    const interfaceStart = Math.max(350, 185 + infrastructure.length * 104 + 35);
    zoneInterfaces.forEach((networkInterface, index) => {
      const column = index % 2;
      positions.set(networkInterface.id, {
        x: centerX + (zoneInterfaces.length > 1 ? (column === 0 ? -zone.width * 0.24 : zone.width * 0.24) : 0),
        y: interfaceStart + Math.floor(index / 2) * 76,
      });
    });
    const interfaceRows = Math.ceil(zoneInterfaces.length / 2);
    const workloadStart = interfaceStart + (interfaceRows ? interfaceRows * 76 : 0) + 105;
    workloads.forEach((asset, index) => positions.set(asset.id, { x: centerX, y: workloadStart + index * 108 }));
    maximumZoneBottom = Math.max(maximumZoneBottom, workloadStart + Math.max(workloads.length - 1, 0) * 108 + 65, interfaceStart + interfaceRows * 76 + 35);
  });

  const unplacedInterfaces = interfaces.filter((node) => !positions.has(node.id));
  unplacedInterfaces.forEach((networkInterface, index) => {
    const owner = graph.edges.find((edge) => edge.type === "HAS_INTERFACE" && (edge.source === networkInterface.id || edge.target === networkInterface.id));
    const ownerPosition = owner ? positions.get(owner.source === networkInterface.id ? owner.target : owner.source) : undefined;
    positions.set(networkInterface.id, { x: ownerPosition?.x ?? 130 + index * 180, y: (ownerPosition?.y ?? maximumZoneBottom) + 92 });
  });

  const securityStartY = Math.max(800, maximumZoneBottom + 120);
  spreadSecurityRow(graph.nodes.filter((node) => node.type === "Identity" || node.type === "Vulnerability"), positions, graph, width, securityStartY);
  spreadSecurityRow(graph.nodes.filter((node) => node.type === "Risk" || node.type === "Control"), positions, graph, width, securityStartY + 125);
  spreadSecurityRow(graph.nodes.filter((node) => !["NetworkSegment", "NetworkInterface", "Asset", "Identity", "Vulnerability", "Risk", "Control"].includes(node.type)), positions, graph, width, securityStartY + 250);

  return { positions, zones, width, height: securityStartY + 340, securityStartY };
};

// Retained for lightweight consumers and tests that only need semantic positioning.
export const layoutNodes = (nodes: TopologyNode[]): Map<string, Position> => layoutTopologyGraph({ nodes, edges: [] }).positions;

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

const truncate = (value: string, max: number) => value.length > max ? `${value.slice(0, max - 1)}…` : value;

const edgeGeometry = (source: Position, target: Position, sourceNode: TopologyNode, targetNode: TopologyNode) => {
  const sourceSize = nodeSize(sourceNode);
  const targetSize = nodeSize(targetNode);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  if (Math.abs(dx) > Math.abs(dy) * 0.85) {
    const direction = dx >= 0 ? 1 : -1;
    const start = { x: source.x + direction * sourceSize.width / 2, y: source.y };
    const end = { x: target.x - direction * targetSize.width / 2, y: target.y };
    const midX = (start.x + end.x) / 2;
    return { path: `M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`, label: { x: midX, y: (start.y + end.y) / 2 } };
  }
  const direction = dy >= 0 ? 1 : -1;
  const start = { x: source.x, y: source.y + direction * sourceSize.height / 2 };
  const end = { x: target.x, y: target.y - direction * targetSize.height / 2 };
  const midY = (start.y + end.y) / 2;
  return { path: `M ${start.x} ${start.y} C ${start.x} ${midY}, ${end.x} ${midY}, ${end.x} ${end.y}`, label: { x: (start.x + end.x) / 2, y: midY } };
};

export const TopologyGraph = ({
  graph,
  focusNodeId,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  height = 820,
}: TopologyGraphProps) => {
  const layout = useMemo(() => layoutTopologyGraph(graph), [graph]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
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
    scale: Math.min(2.8, Math.max(0.42, current.scale * factor)),
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
        component="svg" viewBox={`0 0 ${layout.width} ${layout.height}`} sx={{ width: "100%", height: "100%", cursor: dragStart.current ? "grabbing" : "grab" }}
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
          {layout.zones.map((zone) => (
            <g key={zone.id} pointerEvents="none">
              <rect x={zone.x} y="24" width={zone.width} height={layout.securityStartY - 92} rx="18" fill={zone.fill} fillOpacity="0.72" stroke={zone.stroke} strokeWidth="2" strokeDasharray={zone.virtual ? "9 6" : undefined} />
              {zone.virtual && <text x={zone.x + zone.width / 2} y="78" textAnchor="middle" fontSize="16" fontWeight="800" fill="#344054">{zone.label}</text>}
            </g>
          ))}
          <rect x="42" y={layout.securityStartY - 46} width={layout.width - 84} height="302" rx="18" fill="#FFFFFF" stroke="#D0D5DD" strokeWidth="2" />
          <text x="68" y={layout.securityStartY - 14} fontSize="17" fontWeight="800" fill="#344054">Security context from the Cyber Knowledge Graph</text>

          {graph.edges.map((edge) => {
            const source = layout.positions.get(edge.source);
            const target = layout.positions.get(edge.target);
            const sourceNode = nodeById.get(edge.source);
            const targetNode = nodeById.get(edge.target);
            if (!source || !target || !sourceNode || !targetNode) return null;
            const style = EDGE_STYLES[edge.category] ?? EDGE_STYLES.other;
            const active = !selection.active || selection.edgeIds.has(edge.id);
            const geometry = edgeGeometry(source, target, sourceNode, targetNode);
            const interfaceLabel = [edge.source_interface, edge.target_interface].filter(Boolean).join(" ↔ ");
            const protocol = [edge.properties.protocol, edge.properties.port].filter(Boolean).join("/");
            const detail = [interfaceLabel, protocol].filter(Boolean).join(" · ");
            const showLabel = selectedEdgeId === edge.id || LABELLED_RELATIONSHIPS.has(edge.type);
            return (
              <g key={edge.id} opacity={active ? 1 : 0.1} onClick={(event) => { event.stopPropagation(); onSelectEdge?.(edge); }} style={{ cursor: "pointer" }}>
                <title>{`${edge.type.replace(/_/g, " ")}${detail ? ` — ${detail}` : ""}`}</title>
                <path d={geometry.path} fill="none" stroke="transparent" strokeWidth="14" />
                <path d={geometry.path} fill="none" stroke={style.color} strokeWidth={selectedEdgeId === edge.id ? style.width + 2 : style.width} strokeDasharray={style.dash} markerEnd={`url(#arrow-${edge.category in EDGE_STYLES ? edge.category : "other"})`} />
                {showLabel && <>
                  <rect x={geometry.label.x - 78} y={geometry.label.y - (detail ? 18 : 11)} width="156" height={detail ? 34 : 22} rx="8" fill="#FFFFFF" fillOpacity="0.96" stroke="#D0D5DD" />
                  <text x={geometry.label.x} y={geometry.label.y - (detail ? 4 : -4)} textAnchor="middle" fontSize="10" fontWeight="800" fill={style.color}>{truncate(edge.type.replace(/_/g, " "), 23)}</text>
                  {detail && <text x={geometry.label.x} y={geometry.label.y + 10} textAnchor="middle" fontSize="9" fill="#475467">{truncate(detail, 29)}</text>}
                </>}
              </g>
            );
          })}

          {graph.nodes.map((node) => {
            const position = layout.positions.get(node.id);
            if (!position) return null;
            const size = nodeSize(node);
            const selected = selectedNodeId === node.id || focusNodeId === node.id || focusNodeId === node.entity_id;
            const active = !selection.active || selection.nodeIds.has(node.id);
            const riskLevel = resolveNodeRiskLevel(node);
            const riskColor = RISK_COLORS[riskLevel];
            const asset = node.type === "Asset";
            const colors: Record<string, { fill: string; stroke: string }> = {
              Vulnerability: { fill: "#FFF1F3", stroke: "#D92D20" }, Risk: { fill: "#FFF6ED", stroke: "#F79009" },
              Identity: { fill: "#F4F3FF", stroke: "#7A5AF8" }, Control: { fill: "#F0FDF9", stroke: "#0E9384" },
              NetworkInterface: { fill: "#EFF8FF", stroke: "#1570EF" }, NetworkSegment: { fill: "#FFFFFF", stroke: "#667085" },
            };
            const tone = asset ? { fill: "#FFFFFF", stroke: riskColor } : (colors[node.type] ?? { fill: "#FFFFFF", stroke: "#667085" });
            return (
              <g key={node.id} transform={`translate(${position.x} ${position.y})`} opacity={active ? 1 : 0.14} onClick={(event) => { event.stopPropagation(); onSelectNode?.(node); }} style={{ cursor: "pointer" }} role="button" aria-label={`${node.type}: ${node.label}`}>
                <title>{`${node.label}${node.ip_address ? ` — ${node.ip_address}` : ""}`}</title>
                <rect x={-size.width / 2} y={-size.height / 2} width={size.width} height={size.height} rx={node.type === "Identity" ? 28 : 11} fill={tone.fill} stroke={selected ? "#101828" : tone.stroke} strokeWidth={selected ? 5 : asset ? 4 : 2.5} strokeDasharray={node.type === "NetworkSegment" ? "8 4" : undefined} filter="url(#node-shadow)" />
                <rect x={-size.width / 2 + 9} y={-size.height / 2 + 9} width="42" height={size.height - 18} rx="8" fill={tone.stroke} />
                <text x={-size.width / 2 + 30} y="5" textAnchor="middle" fontSize="11" fontWeight="800" fill="#FFFFFF">{nodeCode(node)}</text>
                <text x={-size.width / 2 + 60} y="-15" fontSize="12" fontWeight="800" fill="#101828">{truncate(node.label, asset ? 21 : 17)}</text>
                <text x={-size.width / 2 + 60} y="4" fontSize="10" fill="#475467">{asset ? truncate(node.ip_address ?? "IP not reported", 23) : truncate(node.type.replace(/_/g, " "), 19)}</text>
                <text x={-size.width / 2 + 60} y="23" fontSize="9.5" fill="#667085">{asset ? `${(node.asset_type ?? "asset").replace(/_/g, " ")} · ${node.criticality ?? "unknown"}` : truncate(String(node.properties.status ?? node.properties.zone ?? ""), 22)}</text>
                {asset && <circle cx={size.width / 2 - 13} cy={-size.height / 2 + 13} r="8" fill={riskColor}><title>{`${riskLevel} risk`}</title></circle>}
              </g>
            );
          })}
        </g>
      </Box>
    </Paper>
  );
};
