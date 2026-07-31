import React, { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, CircularProgress, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Role } from "@/types";

const landingPath = (role: Role) => {
  if (role === "Analyst" || role === "Engineer") return "/dashboard/analyst";
  if (role === "ComplianceOfficer") return "/compliance";
  return "/dashboard/executive";
};

export const LoginPage = () => {
  const [email, setEmail] = useState("admin@csos.com");
  const [password, setPassword] = useState("csos-demo");
  const [error, setError] = useState<string | null>(null);
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate(landingPath(user.role), { replace: true });
    }
  }, [loading, navigate, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const currentUser = await login(email, password);
      navigate(landingPath(currentUser.role));
    } catch {
      setError("Invalid credentials");
    }
  };

  if (loading) return <Box sx={{ display: "grid", placeItems: "center", height: "100vh" }}><CircularProgress /></Box>;

  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <Card sx={{ width: 360 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Cyber Security Operating System
          </Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth label="Email" type="email" margin="normal" value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              fullWidth label="Password" type="password" margin="normal" value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button fullWidth type="submit" variant="contained" sx={{ mt: 2 }} disabled={!email || password.length < 8}>
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};
