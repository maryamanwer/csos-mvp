import { describe, expect, it } from "vitest";
import { layoutNodes, RISK_COLORS } from "./TopologyGraph";
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
