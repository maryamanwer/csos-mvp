import React, { useEffect, useState } from "react";
import { LinearProgress, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { complianceCoverage } from "@/services/api";
import { ComplianceCoverage } from "@/types";

export const ComplianceDashboardPage = () => {
  const [coverage, setCoverage] = useState<ComplianceCoverage[]>([]);

  useEffect(() => {
    complianceCoverage().then((res) => setCoverage(res.data)).catch(() => setCoverage([]));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom>Compliance Dashboard</Typography>
      {/* TODO(P4): add framework selector and coverage visualization */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow><TableCell>Framework</TableCell><TableCell>Controls Met</TableCell><TableCell>Coverage</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {coverage.map((c) => (
              <TableRow key={c.framework}>
                <TableCell>{c.framework}</TableCell>
                <TableCell>{c.controls_met} / {c.total_controls}</TableCell>
                <TableCell sx={{ width: 300 }}>
                  <LinearProgress variant="determinate" value={c.coverage_pct} sx={{ height: 10, borderRadius: 5 }} />
                  <Typography variant="caption">{c.coverage_pct}%</Typography>
                </TableCell>
              </TableRow>
            ))}
            {coverage.length === 0 && <TableRow><TableCell colSpan={3}>No compliance data yet.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};
