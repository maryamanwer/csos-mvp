import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
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

// TODO(M2): add a real <ProtectedRoute> that checks useAuth().user and
// redirects to /login if absent, instead of rendering AppLayout unconditionally.
const Protected = ({ children }: { children: React.ReactNode }) => <AppLayout>{children}</AppLayout>;

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard/executive" element={<Protected><ExecutiveDashboard /></Protected>} />
          <Route path="/dashboard/analyst" element={<Protected><AnalystDashboard /></Protected>} />
          <Route path="/assets" element={<Protected><AssetInventoryPage /></Protected>} />
          <Route path="/assets/:assetId" element={<Protected><AssetDetailsPage /></Protected>} />
          <Route path="/risk" element={<Protected><RiskDashboardPage /></Protected>} />
          <Route path="/compliance" element={<Protected><ComplianceDashboardPage /></Protected>} />
          <Route path="/chat" element={<Protected><ChatAssistantPage /></Protected>} />
          <Route path="/standards" element={<Protected><CustomStandardsPage /></Protected>} />
          <Route path="/reports" element={<Protected><ReportsPage /></Protected>} />
          <Route path="/admin" element={<Protected><AdministrationPage /></Protected>} />
          <Route path="*" element={<Navigate to="/dashboard/executive" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
