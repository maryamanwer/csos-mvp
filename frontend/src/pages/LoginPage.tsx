import React, { useState } from "react";
import { Alert, Box, Button, Card, CardContent, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export const LoginPage = () => {
  const [email, setEmail] = useState("admin@csos.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate("/dashboard/executive");
    } catch {
      setError("Invalid credentials");
    }
  };

  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <Card sx={{ width: 360 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            CSOS Login
          </Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth label="Email" margin="normal" value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              fullWidth label="Password" type="password" margin="normal" value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button fullWidth type="submit" variant="contained" sx={{ mt: 2 }}>
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};
