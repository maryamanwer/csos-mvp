import React from "react";
import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import { ChatPanel } from "@/components/chat/ChatPanel";

export const AnalystDashboard = () => {
  return (
    <>
      <Typography variant="h4" gutterBottom>Analyst Dashboard</Typography>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <Card sx={{ height: 500 }}>
            <CardContent>
              <Typography variant="h6">Investigation Queue</Typography>
              {/* TODO(M2): filterable list of open vulnerabilities/risks */}
              <Typography variant="body2" color="text.secondary">No items — backend not connected yet.</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card sx={{ height: 500 }}>
            <CardContent>
              <Typography variant="h6">Detail Panel</Typography>
              {/* TODO(M2): show selected vulnerability/risk detail */}
              <Typography variant="body2" color="text.secondary">Select an item from the queue.</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Box sx={{ height: 500 }}>
            <ChatPanel docked />
          </Box>
        </Grid>
      </Grid>
    </>
  );
};
