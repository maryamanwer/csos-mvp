import React, { useEffect, useState } from "react";
import { Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { topRisks } from "@/services/api";
import { Risk } from "@/types";

export const RiskDashboardPage = () => {
  const [risks, setRisks] = useState<Risk[]>([]);

  useEffect(() => {
    topRisks(20).then((res) => setRisks(res.data)).catch(() => setRisks([]));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom>Risk Dashboard</Typography>
      {/* TODO(P4): likelihood x impact heatmap (recharts ScatterChart or custom SVG grid) */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Risk</TableCell><TableCell>Score</TableCell><TableCell>Likelihood</TableCell>
              <TableCell>Impact</TableCell><TableCell>Status</TableCell><TableCell>Affected Asset</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {risks.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.title}</TableCell>
                <TableCell><Chip label={r.score} color={r.score > 70 ? "error" : r.score > 40 ? "warning" : "success"} size="small" /></TableCell>
                <TableCell>{r.likelihood}</TableCell>
                <TableCell>{r.impact}</TableCell>
                <TableCell>{r.status}</TableCell>
                <TableCell>{r.affected_asset_id ?? "—"}</TableCell>
              </TableRow>
            ))}
            {risks.length === 0 && <TableRow><TableCell colSpan={6}>No risk data yet.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};
