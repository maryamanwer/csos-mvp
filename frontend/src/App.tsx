import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { AppLayout } from "@/components/common/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { ExecutiveDashboard } from "@/pages/ExecutiveDashboard";
import { AnalystDashboard } from "@/pages/AnalystDashboard";
import { AssetInventoryPage } from "@/pages/AssetInventoryPage";
import { AssetDetailsPage } from "@/pages/AssetDetailsPage";
import { RiskDashboardPage } from "@/pages/RiskDashboardPage";
import { ComplianceDashboardPage } from "@/pages/ComplianceDashboardPage";
import { ChatAssistantPage } from "@/pages/ChatAssistantPage";
import { CustomStandardsPage } from "@/pages/CustomStandardsPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { AdministrationPage } from "@/pages/AdministrationPage";
import { NetworkTopologyPage } from "@/pages/NetworkTopologyPage";
import { VulnerabilityRepositoryPage } from "@/pages/VulnerabilityRepositoryPage";
import { WorkflowsPage } from "@/pages/WorkflowsPage";
import { Role } from "@/types";

const landingPath = (role: Role) => {
  if (role === "Analyst" || role === "Engineer") return "/dashboard/analyst";
  if (role === "ComplianceOfficer") return "/compliance";
  return "/dashboard/executive";
};

const Protected = ({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: Role[];
}) => {
  const { user, loading } = useAuth();
  if (loading) {
    return <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}><CircularProgress /></Box>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={landingPath(user.role)} replace />;
  }
  return <AppLayout>{children}</AppLayout>;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard/executive" element={<Protected roles={["Admin", "Executive"]}><ExecutiveDashboard /></Protected>} />
          <Route path="/dashboard/analyst" element={<Protected roles={["Admin", "Analyst", "Engineer"]}><AnalystDashboard /></Protected>} />
          <Route path="/assets" element={<Protected roles={["Admin", "Analyst", "Engineer", "Executive"]}><AssetInventoryPage /></Protected>} />
          <Route path="/assets/:assetId" element={<Protected roles={["Admin", "Analyst", "Engineer", "Executive"]}><AssetDetailsPage /></Protected>} />
          <Route path="/topology" element={<Protected roles={["Admin", "Analyst", "Engineer", "Executive", "ComplianceOfficer"]}><NetworkTopologyPage /></Protected>} />
          <Route path="/vulnerabilities" element={<Protected roles={["Admin", "Analyst", "Engineer", "Executive"]}><VulnerabilityRepositoryPage /></Protected>} />
          <Route path="/risk" element={<Protected roles={["Admin", "Analyst", "Engineer", "Executive"]}><RiskDashboardPage /></Protected>} />
          <Route path="/compliance" element={<Protected roles={["Admin", "ComplianceOfficer", "Executive"]}><ComplianceDashboardPage /></Protected>} />
          <Route path="/chat" element={<Protected><ChatAssistantPage /></Protected>} />
          <Route path="/standards" element={<Protected roles={["Admin", "ComplianceOfficer"]}><CustomStandardsPage /></Protected>} />
          <Route path="/reports" element={<Protected roles={["Admin", "ComplianceOfficer", "Executive"]}><ReportsPage /></Protected>} />
          <Route path="/workflows" element={<Protected roles={["Admin", "Analyst", "Engineer", "ComplianceOfficer"]}><WorkflowsPage /></Protected>} />
          <Route path="/admin" element={<Protected roles={["Admin"]}><AdministrationPage /></Protected>} />
          <Route path="*" element={<Navigate to="/dashboard/executive" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
