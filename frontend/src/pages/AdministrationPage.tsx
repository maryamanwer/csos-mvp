import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import {
  auditLog,
  createUser,
  listRoles,
  listUsers,
  updateRole,
  updateUser,
  getSystemSettings,
} from "@/services/api";
import { AuditEntry, Role, RoleInfo, User } from "@/types";

interface UserDraft {
  email: string;
  password: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

const EMPTY_USER: UserDraft = {
  email: "",
  password: "",
  full_name: "",
  role: "Analyst",
  is_active: true,
};

export const AdministrationPage = () => {
  const [tab, setTab] = useState(0);
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draft, setDraft] = useState<UserDraft>(EMPTY_USER);
  const [message, setMessage] = useState<{ severity: "success" | "error"; text: string } | null>(null);

  const load = useCallback(() => {
    Promise.all([listUsers(), listRoles(), auditLog(), getSystemSettings()])
      .then(([userResponse, roleResponse, auditResponse, settingsResponse]) => {
        setUsers(userResponse.data);
        setRoles(roleResponse.data);
        setLogs(auditResponse.data);
        setSettings(settingsResponse.data);
      })
      .catch(() => setMessage({ severity: "error", text: "Administration data could not be loaded." }));
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveUser = async () => {
    try {
      await createUser(draft);
      setDialogOpen(false);
      setDraft(EMPTY_USER);
      setMessage({ severity: "success", text: "User created." });
      load();
    } catch {
      setMessage({ severity: "error", text: "The user could not be created. Check the email and password." });
    }
  };

  const changeUser = async (user: User, values: Record<string, unknown>) => {
    try {
      await updateUser(user.id, values);
      setMessage({ severity: "success", text: "User updated." });
      load();
    } catch {
      setMessage({ severity: "error", text: "The user could not be updated." });
    }
  };

  const changeRolePermission = async (
    role: RoleInfo,
    permission: string,
    enabled: boolean,
  ) => {
    const permissionCodes = enabled
      ? [...new Set([...role.permission_codes, permission])]
      : role.permission_codes.filter((code) => code !== permission);
    try {
      await updateRole(role.id, { permission_codes: permissionCodes });
      setMessage({ severity: "success", text: `${role.name} permissions updated.` });
      load();
    } catch {
      setMessage({ severity: "error", text: "The role permissions could not be updated." });
    }
  };

  const allPermissions = [...new Set(roles.flatMap((role) => role.permission_codes))].sort();

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4" gutterBottom>Administration</Typography>
        {tab === 0 && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>Add User</Button>}
      </Box>
      {message && <Alert severity={message.severity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>{message.text}</Alert>}
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label="Users" /><Tab label="Roles & Permissions" /><Tab label="Audit Log" /><Tab label="System Settings" />
      </Tabs>

      {tab === 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead><TableRow>
              <TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>Role</TableCell>
              <TableCell>Active</TableCell><TableCell>Last Login</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {users.map((user) => <TableRow key={user.id}>
                <TableCell>{user.full_name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <TextField
                    select size="small" value={user.role}
                    onChange={(event) => void changeUser(user, { role: event.target.value })}
                    sx={{ minWidth: 180 }}
                  >
                    {roles.map((role) => <MenuItem key={role.id} value={role.name}>{role.name}</MenuItem>)}
                  </TextField>
                </TableCell>
                <TableCell><Switch checked={user.is_active} onChange={(_, checked) => void changeUser(user, { is_active: checked })} /></TableCell>
                <TableCell>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</TableCell>
              </TableRow>)}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 1 && (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
          {roles.map((role) => <Card key={role.id}>
            <CardContent>
              <Typography variant="h6">{role.name}</Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>{role.description}</Typography>
              <Typography variant="subtitle2">Permissions</Typography>
              <Box sx={{ display: "grid" }}>
                {allPermissions.map((permission) => (
                  <FormControlLabel
                    key={permission}
                    label={permission}
                    control={
                      <Checkbox
                        size="small"
                        checked={role.permission_codes.includes(permission)}
                        onChange={(_, checked) => void changeRolePermission(role, permission, checked)}
                      />
                    }
                  />
                ))}
              </Box>
            </CardContent>
          </Card>)}
        </Box>
      )}

      {tab === 2 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead><TableRow>
              <TableCell>Time</TableCell><TableCell>Action</TableCell><TableCell>Entity</TableCell>
              <TableCell>Entity ID</TableCell><TableCell>IP Address</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {logs.map((entry) => <TableRow key={entry.id}>
                <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                <TableCell>{entry.action}</TableCell>
                <TableCell>{entry.entity_type ?? "—"}</TableCell>
                <TableCell>{entry.entity_id ?? "—"}</TableCell>
                <TableCell>{entry.ip_address ?? "—"}</TableCell>
              </TableRow>)}
              {logs.length === 0 && <TableRow><TableCell colSpan={5}>No audit events recorded.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 3 && <Card><CardContent>
        <Typography variant="h6">Operational Settings</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>Effective non-secret configuration. Change deployment values through Codespaces secrets or the backend environment file, then restart the service.</Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "minmax(180px, 260px) 1fr", gap: 1 }}>
          {Object.entries(settings).map(([key, value]) => <React.Fragment key={key}>
            <Typography fontWeight={600}>{key.replace(/_/g, " ")}</Typography>
            <Typography sx={{ overflowWrap: "anywhere" }}>{Array.isArray(value) ? value.join(", ") : String(value)}</Typography>
          </React.Fragment>)}
        </Box>
      </CardContent></Card>}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add User</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: "16px !important" }}>
          <TextField label="Full name" value={draft.full_name} onChange={(event) => setDraft({ ...draft, full_name: event.target.value })} required />
          <TextField type="email" label="Email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} required />
          <TextField type="password" label="Temporary password" helperText="Minimum 8 characters" value={draft.password} onChange={(event) => setDraft({ ...draft, password: event.target.value })} required />
          <TextField select label="Role" value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value as Role })}>
            {roles.map((role) => <MenuItem key={role.id} value={role.name}>{role.name}</MenuItem>)}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveUser()} disabled={!draft.full_name || !draft.email || draft.password.length < 8}>Create User</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
