import React, { ReactNode } from "react";
import { AppBar, Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import StorageIcon from "@mui/icons-material/Storage";
import SecurityIcon from "@mui/icons-material/Security";
import PolicyIcon from "@mui/icons-material/Policy";
import ChatIcon from "@mui/icons-material/Chat";
import DescriptionIcon from "@mui/icons-material/Description";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import BugReportIcon from "@mui/icons-material/BugReport";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import CableIcon from "@mui/icons-material/Cable";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { label: "Executive Dashboard", path: "/dashboard/executive", icon: <DashboardIcon />, roles: ["Admin", "Executive"] },
  { label: "Analyst Dashboard", path: "/dashboard/analyst", icon: <DashboardIcon />, roles: ["Admin", "Analyst", "Engineer"] },
  { label: "Asset Inventory", path: "/assets", icon: <StorageIcon />, roles: ["Admin", "Analyst", "Engineer", "Executive"] },
  { label: "Network Topology", path: "/topology", icon: <AccountTreeIcon />, roles: ["Admin", "Analyst", "Engineer", "Executive", "ComplianceOfficer"] },
  { label: "Security Findings", path: "/findings", icon: <FactCheckIcon />, roles: ["Admin", "Analyst", "Engineer", "Executive", "ComplianceOfficer"] },
  { label: "Vulnerability Repository", path: "/vulnerabilities", icon: <BugReportIcon />, roles: ["Admin", "Analyst", "Engineer", "Executive"] },
  { label: "Risk Dashboard", path: "/risk", icon: <SecurityIcon />, roles: ["Admin", "Analyst", "Engineer", "Executive"] },
  { label: "Compliance", path: "/compliance", icon: <PolicyIcon />, roles: ["Admin", "ComplianceOfficer", "Executive"] },
  { label: "AI Chat Assistant", path: "/chat", icon: <ChatIcon />, roles: ["Admin", "Analyst", "Engineer", "ComplianceOfficer", "Executive"] },
  { label: "Data Sources", path: "/data-sources", icon: <CableIcon />, roles: ["Admin", "Engineer"] },
  { label: "Local AI Models", path: "/ai-models", icon: <SmartToyIcon />, roles: ["Admin", "Engineer"] },
  { label: "Custom Standards", path: "/standards", icon: <UploadFileIcon />, roles: ["Admin", "ComplianceOfficer"] },
  { label: "Reports", path: "/reports", icon: <DescriptionIcon />, roles: ["Admin", "ComplianceOfficer", "Executive"] },
  { label: "Administration", path: "/admin", icon: <AdminPanelSettingsIcon />, roles: ["Admin"] },
];

export const AppLayout = ({ children }: { children: ReactNode }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const role = user?.role;

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <Typography variant="h6">Cyber Security Operating System (CSOS)</Typography>
          <Box>
            <Typography variant="body2" component="span" sx={{ mr: 2 }}>
              {user?.full_name} ({role})
            </Typography>
            <button onClick={logout} style={{ cursor: "pointer" }}>
              Sign out
            </button>
          </Box>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{ width: DRAWER_WIDTH, flexShrink: 0, [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH } }}
      >
        <Toolbar />
        <List>
          {NAV_ITEMS.filter((item) => role && item.roles.includes(role)).map((item) => (
            <ListItemButton key={item.path} onClick={() => navigate(item.path)}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        {children}
      </Box>
    </Box>
  );
};
