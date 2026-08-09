import { describe, expect, it } from "vitest";
import { layoutNodes, layoutTopologyGraph, resolveNodeRiskLevel, RISK_COLORS } from "./TopologyGraph";
import { TopologyNode } from "@/types";
import { filterTopologyGraph } from "@/pages/NetworkTopologyPage";

const node = (id: string, type: string, assetType?: string): TopologyNode => ({
  id,
  entity_id: id,
  label: id,
  type,
  asset_type: assetType,
  properties: {},
});

describe("CSOS topology presentation", () => {
  it("uses the client-approved high, medium, and low risk colors", () => {
    expect(RISK_COLORS.high).toBe("#D92D20");
    expect(RISK_COLORS.medium).toBe("#F79009");
    expect(RISK_COLORS.low).toBe("#12B76A");
  });

  it("places network and security entities into semantic layers instead of a circle", () => {
    const positions = layoutNodes([
      node("internet", "NetworkSegment"),
      node("firewall", "Asset", "firewall"),
      node("switch", "Asset", "switch"),
      node("web", "Asset", "server"),
      node("cve", "Vulnerability"),
      node("risk", "Risk"),
    ]);

    expect(positions.get("internet")!.y).toBeLessThan(positions.get("firewall")!.y);
    expect(positions.get("firewall")!.y).toBeLessThan(positions.get("switch")!.y);
    expect(positions.get("switch")!.y).toBeLessThan(positions.get("web")!.y);
    expect(positions.get("web")!.y).toBeLessThan(positions.get("cve")!.y);
    expect(positions.get("cve")!.y).toBeLessThan(positions.get("risk")!.y);
  });

  it("groups assets into their stored network zones without overlapping", () => {
    const internet = node("internet", "NetworkSegment");
    const dmz = node("dmz", "NetworkSegment");
    const firewall = { ...node("firewall", "Asset", "firewall"), criticality: "critical" };
    const web = { ...node("web", "Asset", "server"), criticality: "high" };
    const wan = node("wan", "NetworkInterface");
    const eth0 = node("eth0", "NetworkInterface");
    const layout = layoutTopologyGraph({
      nodes: [internet, dmz, firewall, web, wan, eth0],
      edges: [
        { id: "fw-if", source: "firewall", target: "wan", type: "HAS_INTERFACE", category: "network", properties: {} },
        { id: "wan-zone", source: "wan", target: "internet", type: "LOCATED_IN", category: "network", properties: {} },
        { id: "web-if", source: "web", target: "eth0", type: "HAS_INTERFACE", category: "network", properties: {} },
        { id: "eth-zone", source: "eth0", target: "dmz", type: "LOCATED_IN", category: "network", properties: {} },
      ],
    });

    expect(layout.zones.map((zone) => zone.label)).toEqual(["internet", "dmz"]);
    expect(layout.positions.get("firewall")!.x).not.toBe(layout.positions.get("web")!.x);
    expect(layout.positions.get("wan")!.y).toBeLessThan(layout.positions.get("web")!.y);
  });

  it("falls back to asset criticality when a risk score is not available", () => {
    expect(resolveNodeRiskLevel({ ...node("critical", "Asset", "server"), criticality: "critical" })).toBe("high");
    expect(resolveNodeRiskLevel({ ...node("medium", "Asset", "server"), criticality: "medium" })).toBe("medium");
    expect(resolveNodeRiskLevel(node("unknown", "Asset", "server"))).toBe("unknown");
  });

  it("filters assets while preserving their directly connected security context", () => {
    const web = { ...node("web", "Asset", "server"), label: "WEB-PROD-01", risk_level: "high" as const, properties: { environment: "production" } };
    const app = { ...node("app", "Asset", "application"), risk_level: "low" as const, properties: { environment: "production" } };
    const cve = { ...node("cve", "Vulnerability"), label: "CVE-2026-4102" };
    const graph = {
      nodes: [web, app, cve],
      edges: [
        { id: "network", source: "web", target: "app", type: "DEPENDS_ON", category: "network" as const, properties: {} },
        { id: "finding", source: "web", target: "cve", type: "HAS_VULNERABILITY", category: "vulnerability" as const, properties: {} },
      ],
    };

    const filtered = filterTopologyGraph(graph, {
      assetType: "all", riskLevel: "high", environment: "all",
      relationship: "all", search: "web-prod",
    });

    expect(filtered.nodes.map((item) => item.id).sort()).toEqual(["app", "cve", "web"]);
    expect(filtered.edges).toHaveLength(2);
  });
});
