import React, { useState } from "react";
import { Alert, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { generateReport } from "@/services/api";

export const ReportsPage = () => {
  const [reportType, setReportType] = useState("risk");
  const [format, setFormat] = useState("pdf");
  const [status, setStatus] = useState<string | null>(null);

  const handleGenerate = async () => {
    const { data } = await generateReport(reportType, format);
    setStatus(`Report queued: ${data.report_type} (${data.format})`);
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>Reports</Typography>
      <Card sx={{ maxWidth: 480 }}>
        <CardContent>
          <Stack spacing={2}>
            {status && <Alert severity="success">{status}</Alert>}
            <TextField select label="Report Type" value={reportType} onChange={(e) => setReportType(e.target.value)}>
              <MenuItem value="risk">Risk</MenuItem>
              <MenuItem value="compliance">Compliance</MenuItem>
              <MenuItem value="asset">Asset</MenuItem>
            </TextField>
            <TextField select label="Format" value={format} onChange={(e) => setFormat(e.target.value)}>
              <MenuItem value="pdf">PDF</MenuItem>
              <MenuItem value="xlsx">Excel</MenuItem>
            </TextField>
            <Button variant="contained" onClick={handleGenerate}>Generate</Button>
            {/* TODO(M4): real PDF/Excel generation + download link + history table */}
          </Stack>
        </CardContent>
      </Card>
    </>
  );
};
