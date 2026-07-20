import React, { useEffect, useState } from "react";
import { Button, Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { listAssets } from "@/services/api";
import { Asset } from "@/types";
import { riskColor } from "@/theme";

export const AssetInventoryPage = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    listAssets().then((res) => setAssets(res.data)).catch(() => setAssets([]));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom sx={{ display: "flex", justifyContent: "space-between" }}>
        Asset Inventory
        <Button variant="contained">Import CSV/Excel</Button>
        {/* TODO(M2): wire to POST /assets/import */}
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell><TableCell>Type</TableCell><TableCell>Owner</TableCell>
              <TableCell>Criticality</TableCell><TableCell>Environment</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {assets.map((a) => (
              <TableRow key={a.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/assets/${a.id}`)}>
                <TableCell>{a.name}</TableCell>
                <TableCell>{a.type}</TableCell>
                <TableCell>{a.owner ?? "—"}</TableCell>
                <TableCell><Chip label={a.criticality} sx={{ bgcolor: riskColor(a.criticality), color: "#fff" }} size="small" /></TableCell>
                <TableCell>{a.environment}</TableCell>
              </TableRow>
            ))}
            {assets.length === 0 && (
              <TableRow><TableCell colSpan={5}>No assets yet — backend not connected to a live database.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};
