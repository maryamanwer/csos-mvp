import React, { useMemo, useRef, useState } from "react";
import { Box, Button, IconButton, Paper, Stack, Tooltip, Typography } from "@mui/material";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
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
  subtitle: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fill: string;
  stroke: string;
  kind: "perimeter" | "network" | "shared";
}

export interface TopologyLayout {
  positions: Map<string, Position>;
  zones: ZoneLayout[];
  width: number;
  height: number;
  securityStartY: number;
}

type RiskLevel = "high" | "medium" | "low" | "unknown";
export type TopologyGlyph = "firewall" | "router" | "switch" | "database" | "application" | "endpoint" | "cloud" | "server" | "asset";

export const RISK_COLORS: Record<RiskLevel, string> = {
  high: "#D92D20",
  medium: "#F79009",
  low: "#12B76A",
  unknown: "#667085",
};

const EDGE_STYLES: Record<string, { color: string; dash?: string; width: number }> = {
  network: { color: "#24486B", width: 3 },
  vulnerability: { color: "#D92D20", dash: "8 5", width: 2.25 },
  risk: { color: "#F79009", dash: "5 4", width: 2.25 },
  identity: { color: "#7A5AF8", dash: "2 5", width: 2.25 },
  control: { color: "#0E9384", dash: "10 4", width: 2.25 },
  other: { color: "#98A2B3", width: 2 },
};

const ZONE_TONES = [
  { fill: "#EFF8FF", stroke: "#2E90FA" },
  { fill: "#F0FDF9", stroke: "#12B76A" },
  { fill: "#F4F3FF", stroke: "#7A5AF8" },
  { fill: "#FDF2FA", stroke: "#EE46BC" },
  { fill: "#FFF7ED", stroke: "#FB923C" },
];

const INFRASTRUCTURE_TYPES = new Set(["firewall", "router", "switch", "network_device"]);
const MAIN_PATH_RELATIONSHIPS = new Set(["CONNECTS_TO", "CONNECTED_TO", "COMMUNICATES_WITH", "DEPENDS_ON", "HOSTS", "PROTECTS"]);

const normalized = (value: unknown) => String(value ?? "").trim().toLowerCase();

export const resolveNodeRiskLevel = (node: TopologyNode): RiskLevel => {
  if (node.risk_level && ["high", "medium", "low"].includes(node.risk_level)) return node.risk_level;
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

export const topologyGlyph = (node: TopologyNode): TopologyGlyph => {
  const assetType = normalized(node.asset_type);
  if (assetType === "firewall") return "firewall";
  if (assetType === "router") return "router";
  if (assetType === "switch" || assetType === "network_device") return "switch";
  if (assetType === "database") return "database";
  if (assetType === "application") return "application";
  if (assetType === "endpoint" || assetType === "workstation") return "endpoint";
  if (assetType === "cloud" || assetType === "cloud_resource") return "cloud";
  if (assetType === "server") return "server";
  return "asset";
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
  if (node.type === "Asset") return { width: 218, height: 100 };
  if (node.type === "NetworkSegment") return { width: 224, height: 66 };
  if (node.type === "NetworkInterface") return { width: 144, height: 48 };
  return { width: 174, height: 66 };
};

const segmentSubtitle = (node: TopologyNode) => {
  const cidr = String(node.properties.cidr ?? "");
  const vlan = String(node.properties.vlan ?? "");
  return [cidr, vlan ? `VLAN ${vlan}` : ""].filter(Boolean).join("  |  ") || String(node.properties.zone ?? "Network segment");
};

const findSegment = (segments: TopologyNode[], terms: string[]) => segments.find((segment) => {
  const text = normalized(`${segment.label} ${segment.properties.zone ?? ""}`);
  return terms.some((term) => text.includes(term));
});

const spreadRow = (
  nodes: TopologyNode[],
  positions: Map<string, Position>,
  graph: TopologyGraphData,
  width: number,
  y: number,
) => {
  const anchored = nodes.map((node) => {
    const connected = graph.edges
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .map((edge) => positions.get(edge.source === node.id ? edge.target : edge.source)?.x)
      .filter((value): value is number => value !== undefined);
    return { node, preferredX: connected.length ? connected.reduce((sum, value) => sum + value, 0) / connected.length : width / 2 };
  }).sort((a, b) => a.preferredX - b.preferredX || a.node.label.localeCompare(b.node.label));
  if (!anchored.length) return;
  const step = Math.min(220, (width - 190) / Math.max(anchored.length - 1, 1));
  const start = width / 2 - step * Math.max(anchored.length - 1, 0) / 2;
  anchored.forEach(({ node }, index) => positions.set(node.id, { x: start + index * step, y }));
};

export const layoutTopologyGraph = (graph: TopologyGraphData, showSecurityContext = true): TopologyLayout => {
  const positions = new Map<string, Position>();
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const segments = graph.nodes.filter((node) => node.type === "NetworkSegment").sort((a, b) => segmentRank(a) - segmentRank(b) || a.label.localeCompare(b.label));
  const externalSegment = findSegment(segments, ["internet", "external"]);
  const internalSegments = segments.filter((segment) => segment.id !== externalSegment?.id);
  const interfaces = graph.nodes.filter((node) => node.type === "NetworkInterface");
  const assets = graph.nodes.filter((node) => node.type === "Asset");
  const infrastructure = assets.filter((asset) => INFRASTRUCTURE_TYPES.has(normalized(asset.asset_type)));

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
  const dmz = findSegment(internalSegments, ["dmz"]);
  const application = findSegment(internalSegments, ["application", "app"]);
  const data = findSegment(internalSegments, ["data", "database"]);
  const user = findSegment(internalSegments, ["user", "lan", "endpoint"]);

  assets.filter((asset) => !infrastructure.includes(asset)).forEach((asset) => {
    const directZones = (interfacesByAsset.get(asset.id) ?? [])
      .map((interfaceId) => segmentByInterface.get(interfaceId))
      .filter((segmentId): segmentId is string => Boolean(segmentId) && segmentId !== externalSegment?.id);
    if (directZones.length) {
      zoneByAsset.set(asset.id, directZones[0]);
      return;
    }
    const type = normalized(asset.asset_type);
    const label = normalized(asset.label);
    if ((label.includes("web") || label.includes("portal")) && dmz) zoneByAsset.set(asset.id, dmz.id);
    else if (type === "application" && application) zoneByAsset.set(asset.id, application.id);
    else if (type === "database" && data) zoneByAsset.set(asset.id, data.id);
    else if ((type === "endpoint" || type === "workstation") && user) zoneByAsset.set(asset.id, user.id);
  });

  const sharedAssets = assets.filter((asset) => !infrastructure.includes(asset) && !zoneByAsset.has(asset.id));
  const side = 36;
  const gap = 22;
  const perimeterWidth = 430;
  const zoneWidth = 286;
  const zoneCount = internalSegments.length + (sharedAssets.length ? 1 : 0);
  const width = Math.max(1500, side * 2 + perimeterWidth + gap + zoneCount * zoneWidth + Math.max(zoneCount - 1, 0) * gap);
  const panelY = 34;
  const panelHeight = 596;
  const zones: ZoneLayout[] = [{
    id: "__perimeter__",
    label: "Internet Edge & Core",
    subtitle: "External access, perimeter security and network fabric",
    x: side,
    y: panelY,
    width: perimeterWidth,
    height: panelHeight,
    fill: "#F8FAFC",
    stroke: "#475467",
    kind: "perimeter",
  }];

  internalSegments.forEach((segment, index) => {
    const tone = ZONE_TONES[index % ZONE_TONES.length];
    zones.push({
      id: segment.id,
      label: segment.label,
      subtitle: segmentSubtitle(segment),
      x: side + perimeterWidth + gap + index * (zoneWidth + gap),
      y: panelY,
      width: zoneWidth,
      height: panelHeight,
      fill: tone.fill,
      stroke: tone.stroke,
      kind: "network",
    });
  });
  if (sharedAssets.length) {
    const index = internalSegments.length;
    zones.push({
      id: "__shared__",
      label: "Shared Services",
      subtitle: "Enterprise and cloud services without a reported network segment",
      x: side + perimeterWidth + gap + index * (zoneWidth + gap),
      y: panelY,
      width: zoneWidth,
      height: panelHeight,
      fill: "#FFF7ED",
      stroke: "#FB923C",
      kind: "shared",
    });
  }

  const perimeter = zones[0];
  if (externalSegment) positions.set(externalSegment.id, { x: perimeter.x + 104, y: 176 });

  const orderedInfrastructure = [...infrastructure].sort((a, b) => {
    const order = (node: TopologyNode) => topologyGlyph(node) === "firewall" ? 0 : topologyGlyph(node) === "router" ? 1 : 2;
    return order(a) - order(b) || a.label.localeCompare(b.label);
  });
  orderedInfrastructure.forEach((asset, index) => positions.set(asset.id, {
    x: perimeter.x + 326 - (index % 2) * 114,
    y: 176 + index * 150,
  }));

  internalSegments.forEach((segment) => {
    const zone = zones.find((item) => item.id === segment.id)!;
    const centerX = zone.x + zone.width / 2;
    positions.set(segment.id, { x: centerX, y: 116 });
    const zoneAssets = assets.filter((asset) => zoneByAsset.get(asset.id) === segment.id).sort((a, b) => a.label.localeCompare(b.label));
    zoneAssets.forEach((asset, index) => positions.set(asset.id, { x: centerX, y: 252 + index * 132 }));
  });

  if (sharedAssets.length) {
    const zone = zones.find((item) => item.id === "__shared__")!;
    const centerX = zone.x + zone.width / 2;
    sharedAssets.sort((a, b) => a.label.localeCompare(b.label)).forEach((asset, index) => positions.set(asset.id, { x: centerX, y: 210 + index * 122 }));
  }

  const securityStartY = panelY + panelHeight + 112;
  if (showSecurityContext) {
    spreadRow(graph.nodes.filter((node) => node.type === "Identity" || node.type === "Vulnerability"), positions, graph, width, securityStartY);
    spreadRow(graph.nodes.filter((node) => node.type === "Risk" || node.type === "Control"), positions, graph, width, securityStartY + 118);
    spreadRow(graph.nodes.filter((node) => !["NetworkSegment", "NetworkInterface", "Asset", "Identity", "Vulnerability", "Risk", "Control"].includes(node.type)), positions, graph, width, securityStartY + 236);
  }
  return {
    positions,
    zones,
    width,
    height: showSecurityContext ? securityStartY + 315 : panelY + panelHeight + 34,
    securityStartY,
  };
};

export const layoutNodes = (nodes: TopologyNode[]): Map<string, Position> => layoutTopologyGraph({ nodes, edges: [] }, true).positions;

const nodeCode = (node: TopologyNode) => {
  if (node.type === "Vulnerability") return "CVE";
  if (node.type === "Risk") return "RISK";
  if (node.type === "Identity") return "USR";
  if (node.type === "Control") return "CTRL";
  if (node.type === "NetworkInterface") return "PORT";
  if (node.type === "NetworkSegment") return "NET";
  return "AST";
};

const truncate = (value: string, max: number) => value.length > max ? `${value.slice(0, max - 1)}…` : value;

const DeviceGlyph = ({ node, color }: { node: TopologyNode; color: string }) => {
  const glyph = topologyGlyph(node);
  const common = { fill: "none", stroke: color, strokeWidth: 3, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (glyph === "firewall") return <g {...common}><rect x="-23" y="-19" width="46" height="38" rx="3" /><path d="M-23-6H23M-23 7H23M-8-19V-6M9-19V-6M-16-6V7M3-6V7M-7 7V19M12 7V19" /></g>;
  if (glyph === "switch" || glyph === "router") return <g {...common}><rect x="-25" y="-15" width="50" height="30" rx="7" /><path d="M-15-4H15M-15 4H15M-10-9L-15-4-10 1M10-1L15 4 10 9" /><circle cx="-17" cy="10" r="2" fill={color} /><circle cx="-10" cy="10" r="2" fill={color} /></g>;
  if (glyph === "database") return <g {...common}><ellipse cx="0" cy="-15" rx="22" ry="8" /><path d="M-22-15V15C-22 25 22 25 22 15V-15M-22 0C-22 10 22 10 22 0M-22 14C-22 24 22 24 22 14" /></g>;
  if (glyph === "application") return <g {...common}><rect x="-25" y="-20" width="50" height="40" rx="5" /><path d="M-25-9H25" /><circle cx="-17" cy="-14" r="2" fill={color} /><circle cx="-10" cy="-14" r="2" fill={color} /><path d="M-13 1H13M-13 9H7" /></g>;
  if (glyph === "endpoint") return <g {...common}><rect x="-25" y="-19" width="50" height="34" rx="4" /><path d="M0 15V23M-14 23H14" /></g>;
  if (glyph === "cloud") return <g {...common}><path d="M-24 12H20C32 12 32-7 20-8C17-25-7-27-13-12C-29-14-34 8-24 12Z" /></g>;
  if (glyph === "server") return <g {...common}><rect x="-19" y="-24" width="38" height="48" rx="4" /><path d="M-11-13H8M-11-3H8M-11 7H8" /><circle cx="12" cy="-13" r="2" fill={color} /><circle cx="12" cy="-3" r="2" fill={color} /></g>;
  return <g {...common}><rect x="-22" y="-22" width="44" height="44" rx="8" /><path d="M-10 0H10M0-10V10" /></g>;
};

const edgeGeometry = (source: Position, target: Position, sourceNode: TopologyNode, targetNode: TopologyNode, category: string) => {
  const sourceSize = nodeSize(sourceNode);
  const targetSize = nodeSize(targetNode);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  if (category === "network") {
    if (Math.abs(dx) >= Math.abs(dy)) {
      const direction = dx >= 0 ? 1 : -1;
      const startX = source.x + direction * sourceSize.width / 2;
      const endX = target.x - direction * targetSize.width / 2;
      const midX = (startX + endX) / 2;
      return { path: `M ${startX} ${source.y} H ${midX} V ${target.y} H ${endX}`, label: { x: midX, y: (source.y + target.y) / 2 } };
    }
    const direction = dy >= 0 ? 1 : -1;
    const startY = source.y + direction * sourceSize.height / 2;
    const endY = target.y - direction * targetSize.height / 2;
    const midY = (startY + endY) / 2;
    return { path: `M ${source.x} ${startY} V ${midY} H ${target.x} V ${endY}`, label: { x: (source.x + target.x) / 2, y: midY } };
  }
  const direction = dy >= 0 ? 1 : -1;
  const startY = source.y + direction * sourceSize.height / 2;
  const endY = target.y - direction * targetSize.height / 2;
  const midY = (startY + endY) / 2;
  return { path: `M ${source.x} ${startY} C ${source.x} ${midY}, ${target.x} ${midY}, ${target.x} ${endY}`, label: { x: (source.x + target.x) / 2, y: midY } };
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
  const [showSecurityContext, setShowSecurityContext] = useState(false);
  const layout = useMemo(() => layoutTopologyGraph(graph, showSecurityContext), [graph, showSecurityContext]);
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

  const zoomBy = (factor: number) => setViewport((current) => ({ ...current, scale: Math.min(2.8, Math.max(0.42, current.scale * factor)) }));

  if (graph.nodes.length === 0) {
    return <Paper variant="outlined" sx={{ height, display: "grid", placeItems: "center", p: 3 }}><Typography color="text.secondary">No topology entities match the current view.</Typography></Paper>;
  }

  return (
    <Paper variant="outlined" sx={{ position: "relative", overflow: "hidden", height, bgcolor: "#F8FAFC" }}>
      <Stack direction="row" spacing={0.5} sx={{ position: "absolute", zIndex: 2, top: 10, right: 10, bgcolor: "white", borderRadius: 1, boxShadow: 1, p: 0.25 }}>
        <Button size="small" startIcon={<HubOutlinedIcon />} variant={showSecurityContext ? "contained" : "outlined"} onClick={() => { setShowSecurityContext((value) => !value); setViewport({ x: 0, y: 0, scale: 1 }); }}>
          {showSecurityContext ? "Hide security overlay" : "Show security overlay"}
        </Button>
        <Tooltip title="Zoom in"><IconButton size="small" onClick={() => zoomBy(1.2)}><ZoomInIcon /></IconButton></Tooltip>
        <Tooltip title="Zoom out"><IconButton size="small" onClick={() => zoomBy(0.8)}><ZoomOutIcon /></IconButton></Tooltip>
        <Tooltip title="Fit topology"><IconButton size="small" onClick={() => setViewport({ x: 0, y: 0, scale: 1 })}><CenterFocusStrongIcon /></IconButton></Tooltip>
      </Stack>
      <Box
        component="svg" viewBox={`0 0 ${layout.width} ${layout.height}`} sx={{ width: "100%", height: "100%", cursor: dragStart.current ? "grabbing" : "grab" }}
        onWheel={(event: React.WheelEvent<SVGSVGElement>) => { event.preventDefault(); zoomBy(event.deltaY < 0 ? 1.1 : 0.9); }}
        onPointerDown={(event: React.PointerEvent<SVGSVGElement>) => { event.currentTarget.setPointerCapture(event.pointerId); dragStart.current = { pointerX: event.clientX, pointerY: event.clientY, x: viewport.x, y: viewport.y }; }}
        onPointerMove={(event: React.PointerEvent<SVGSVGElement>) => { if (!dragStart.current) return; setViewport((current) => ({ ...current, x: dragStart.current!.x + event.clientX - dragStart.current!.pointerX, y: dragStart.current!.y + event.clientY - dragStart.current!.pointerY })); }}
        onPointerUp={() => { dragStart.current = null; }} onPointerCancel={() => { dragStart.current = null; }}
      >
        <defs>
          {Object.entries(EDGE_STYLES).map(([category, style]) => (
            <marker key={category} id={`arrow-${category}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill={style.color} /></marker>
          ))}
          <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.16" /></filter>
        </defs>
        <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
          {layout.zones.map((zone) => (
            <g key={zone.id} pointerEvents="none">
              <rect x={zone.x} y={zone.y} width={zone.width} height={zone.height} rx="18" fill={zone.fill} fillOpacity="0.82" stroke={zone.stroke} strokeWidth="2.5" strokeDasharray={zone.kind === "shared" ? "9 6" : undefined} />
              <rect x={zone.x} y={zone.y} width={zone.width} height="48" rx="18" fill={zone.stroke} fillOpacity="0.12" />
              <text x={zone.x + 16} y={zone.y + 21} fontSize="12" fontWeight="800" fill={zone.stroke} letterSpacing="1.2">{zone.kind === "perimeter" ? "PERIMETER & CORE" : zone.kind === "shared" ? "SHARED SERVICES" : "NETWORK ZONE"}</text>
              <text x={zone.x + 16} y={zone.y + 39} fontSize="10" fill="#475467">{truncate(zone.subtitle, Math.max(28, Math.floor(zone.width / 7)))}</text>
            </g>
          ))}
          {showSecurityContext && <g pointerEvents="none">
            <rect x="36" y={layout.securityStartY - 55} width={layout.width - 72} height="335" rx="18" fill="#FFFFFF" stroke="#98A2B3" strokeWidth="2" />
            <text x="56" y={layout.securityStartY - 22} fontSize="16" fontWeight="800" fill="#344054">Security overlay — findings, identities, risks and controls</text>
          </g>}

          {graph.edges.map((edge) => {
            const source = layout.positions.get(edge.source);
            const target = layout.positions.get(edge.target);
            const sourceNode = nodeById.get(edge.source);
            const targetNode = nodeById.get(edge.target);
            if (!source || !target || !sourceNode || !targetNode) return null;
            const style = EDGE_STYLES[edge.category] ?? EDGE_STYLES.other;
            const active = !selection.active || selection.edgeIds.has(edge.id);
            const geometry = edgeGeometry(source, target, sourceNode, targetNode, edge.category);
            const interfaceLabel = [edge.source_interface, edge.target_interface].filter(Boolean).join(" \u2194 ");
            const protocol = [edge.properties.protocol, edge.properties.port].filter(Boolean).join("/");
            const detail = [interfaceLabel, protocol].filter(Boolean).join(" · ");
            const assetToAsset = sourceNode.type === "Asset" && targetNode.type === "Asset";
            const showLabel = selectedEdgeId === edge.id || (edge.category === "network" && assetToAsset && MAIN_PATH_RELATIONSHIPS.has(edge.type));
            return (
              <g key={edge.id} opacity={active ? 1 : 0.1} onClick={(event) => { event.stopPropagation(); onSelectEdge?.(edge); }} style={{ cursor: "pointer" }}>
                <title>{`${edge.type.replace(/_/g, " ")}${detail ? ` — ${detail}` : ""}`}</title>
                <path d={geometry.path} fill="none" stroke="transparent" strokeWidth="14" />
                <path d={geometry.path} fill="none" stroke={style.color} strokeWidth={selectedEdgeId === edge.id ? style.width + 2 : style.width} strokeDasharray={style.dash} markerEnd={`url(#arrow-${edge.category in EDGE_STYLES ? edge.category : "other"})`} />
                {showLabel && <>
                  <rect x={geometry.label.x - 76} y={geometry.label.y - (detail ? 18 : 11)} width="152" height={detail ? 34 : 22} rx="8" fill="#FFFFFF" fillOpacity="0.97" stroke="#D0D5DD" />
                  <text x={geometry.label.x} y={geometry.label.y - (detail ? 4 : -4)} textAnchor="middle" fontSize="10" fontWeight="800" fill={style.color}>{truncate(edge.type.replace(/_/g, " "), 22)}</text>
                  {detail && <text x={geometry.label.x} y={geometry.label.y + 10} textAnchor="middle" fontSize="9" fill="#475467">{truncate(detail, 28)}</text>}
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
              NetworkInterface: { fill: "#FFFFFF", stroke: "#1570EF" }, NetworkSegment: { fill: "#FFFFFF", stroke: "#475467" },
            };
            const tone = asset ? { fill: "#FFFFFF", stroke: riskColor } : (colors[node.type] ?? { fill: "#FFFFFF", stroke: "#667085" });
            return (
              <g key={node.id} transform={`translate(${position.x} ${position.y})`} opacity={active ? 1 : 0.14} onClick={(event) => { event.stopPropagation(); onSelectNode?.(node); }} style={{ cursor: "pointer" }} role="button" aria-label={`${node.type}: ${node.label}`}>
                <title>{`${node.label}${node.ip_address ? ` — ${node.ip_address}` : ""}`}</title>
                <rect x={-size.width / 2} y={-size.height / 2} width={size.width} height={size.height} rx={node.type === "Identity" ? 28 : 11} fill={tone.fill} stroke={selected ? "#101828" : tone.stroke} strokeWidth={selected ? 5 : asset ? 3.5 : 2.5} strokeDasharray={node.type === "NetworkSegment" ? "8 4" : undefined} filter="url(#node-shadow)" />
                {asset ? <>
                  <rect x={-size.width / 2 + 9} y={-size.height / 2 + 9} width="66" height={size.height - 18} rx="9" fill={riskColor} fillOpacity="0.1" />
                  <g transform={`translate(${-size.width / 2 + 42} 0)`}><DeviceGlyph node={node} color={riskColor} /></g>
                  <text x={-size.width / 2 + 84} y="-24" fontSize="12" fontWeight="800" fill="#101828">{truncate(node.label, 19)}</text>
                  <text x={-size.width / 2 + 84} y="-5" fontSize="10" fill="#344054">{truncate(node.ip_address ?? "IP not reported", 21)}</text>
                  <text x={-size.width / 2 + 84} y="14" fontSize="9.5" fill="#667085">{truncate((node.asset_type ?? "asset").replace(/_/g, " "), 19)}</text>
                  <text x={-size.width / 2 + 84} y="32" fontSize="9.5" fontWeight="700" fill={riskColor}>{node.criticality ?? "unknown"} · {riskLevel} risk</text>
                  <circle cx={size.width / 2 - 13} cy={-size.height / 2 + 13} r="7" fill={riskColor} />
                </> : <>
                  <rect x={-size.width / 2 + 8} y={-size.height / 2 + 8} width="43" height={size.height - 16} rx="8" fill={tone.stroke} />
                  <text x={-size.width / 2 + 29.5} y="5" textAnchor="middle" fontSize="10" fontWeight="800" fill="#FFFFFF">{nodeCode(node)}</text>
                  <text x={-size.width / 2 + 59} y="-12" fontSize="11" fontWeight="800" fill="#101828">{truncate(node.label, node.type === "NetworkSegment" ? 23 : 17)}</text>
                  <text x={-size.width / 2 + 59} y="7" fontSize="9.5" fill="#475467">{node.type === "NetworkSegment" ? truncate(segmentSubtitle(node), 25) : truncate(node.type.replace(/_/g, " "), 19)}</text>
                  <text x={-size.width / 2 + 59} y="23" fontSize="9" fill="#667085">{truncate(String(node.properties.status ?? node.properties.zone ?? ""), 20)}</text>
                </>}
              </g>
            );
          })}
        </g>
      </Box>
    </Paper>
  );
};
