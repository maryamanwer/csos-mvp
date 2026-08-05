import { createTheme } from "@mui/material";

// Design system per docs/wireframes/wireframes.md
export const theme = createTheme({
  palette: {
    primary: { main: "#1E3A5F" }, // navy
    secondary: { main: "#2FA6A6" }, // teal accent
    error: { main: "#D32F2F" }, // critical
    warning: { main: "#F57C00" }, // high
    info: { main: "#FBC02D" }, // medium (used as a badge color, not MUI "info" semantics)
    success: { main: "#43A047" }, // low
  },
  shape: { borderRadius: 8 },
});

// Risk/criticality color helper used across dashboards & tables
export const riskColor = (level: string): string => {
  switch (level) {
    case "critical":
      return "#D32F2F";
    case "high":
      return "#F57C00";
    case "medium":
      return "#FBC02D";
    case "low":
    default:
      return "#43A047";
  }
};
