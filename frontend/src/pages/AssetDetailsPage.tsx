import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Box, Chip, Tab, Tabs, Typography } from "@mui/material";
import { getAsset } from "@/services/api";
import { Asset } from "@/types";
import { riskColor } from "@/theme";

export const AssetDetailsPage = () => {
  const { assetId } = useParams();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    if (assetId) getAsset(assetId).then((res) => setAsset(res.data)).catch(() => setAsset(null));
  }, [assetId]);

  if (!asset) return <Typography>Loading asset…</Typography>;

  return (
    <>
      <Typography variant="h4">
        {asset.name}{" "}
        <Chip label={asset.criticality} sx={{ bgcolor: riskColor(asset.criticality), color: "#fff" }} />
      </Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Overview" /><Tab label="Relationships" /><Tab label="Vulnerabilities" />
        <Tab label="Compliance Controls" /><Tab label="History" />
      </Tabs>
      <Box>
        {tab === 0 && (
          <Typography>
            Type: {asset.type} · Environment: {asset.environment} · Owner: {asset.owner ?? "—"}
          </Typography>
        )}
        {/* TODO(M2/M3): Relationships tab -> graph view via Neo4j;
            Vulnerabilities/Controls tabs -> query respective endpoints */}
        {tab !== 0 && <Typography color="text.secondary">Coming in Milestone 2/3.</Typography>}
      </Box>
    </>
  );
};
