import React, { useEffect, useState } from "react";
import { Tab, Tabs, Typography } from "@mui/material";
import { auditLog, listUsers } from "@/services/api";

export const AdministrationPage = () => {
  const [tab, setTab] = useState(0);
  const [users, setUsers] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    listUsers().then((r) => setUsers(r.data)).catch(() => setUsers([]));
    auditLog().then((r) => setLogs(r.data)).catch(() => setLogs([]));
  }, []);

  return (
    <>
      <Typography variant="h4" gutterBottom>Administration</Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Users" /><Tab label="Roles & Permissions" /><Tab label="Audit Log" /><Tab label="System Settings" />
      </Tabs>
      {tab === 0 && (
        <Typography color="text.secondary">
          {users.length === 0 ? "No users yet — backend not connected to live DB (M2)." : `${users.length} users`}
        </Typography>
      )}
      {tab === 2 && (
        <Typography color="text.secondary">
          {logs.length === 0 ? "No audit entries yet (M2)." : `${logs.length} entries`}
        </Typography>
      )}
      {(tab === 1 || tab === 3) && <Typography color="text.secondary">Coming in Milestone 2/4.</Typography>}
    </>
  );
};
