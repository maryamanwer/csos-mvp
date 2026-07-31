import React, { useState } from "react";
import { Alert, Box, Button, Card, CardContent, Typography } from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { api } from "@/services/api";

export const CustomStandardsPage = () => {
  const [status, setStatus] = useState<string | null>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post("/standards/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setStatus(`Uploaded ${data.file_name} (${data.size_bytes} bytes) — status: ${data.status}`);
  };

  return (
    <>
      <Typography variant="h4" gutterBottom>Custom Standards & Policies</Typography>
      <Card>
        <CardContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Supported formats: CSV, Excel, Word, JSON, or manual entry.
          </Typography>
          {status && <Alert severity="info" sx={{ mb: 2 }}>{status}</Alert>}
          <Button component="label" variant="contained" startIcon={<UploadFileIcon />}>
            Upload File
            <input type="file" hidden onChange={handleFile} accept=".csv,.xlsx,.docx,.json" />
          </Button>
          {/* TODO(P4): manual-entry form + "Map Controls to Assets" table below */}
        </CardContent>
      </Card>
    </>
  );
};
