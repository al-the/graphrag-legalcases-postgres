import React, { useState } from "react";
import { register, login, setToken } from "../api/authApi";

export function RegisterPage({ onSuccess, onLogin }: { onSuccess: () => void; onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email, password, name);
      const token = await login(email, password);
      setToken(token);
      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create Account</h1>
        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>Display Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} style={styles.input} />
          <label style={styles.label}>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            required style={styles.input} />
          <label style={styles.label}>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            required minLength={8} style={styles.input} />
          {error && <p style={styles.error}>{error}</p>}
          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? "Creating…" : "Create Account"}
          </button>
        </form>
        <p style={styles.foot}>
          Already have an account?{" "}
          <button onClick={onLogin} style={styles.link}>Sign In</button>
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "#0f172a" },
  card: { background: "#1e293b", borderRadius: 16, padding: 40, width: 360, display: "flex", flexDirection: "column", gap: 4 },
  title: { margin: "0 0 24px", fontSize: 24, fontWeight: 700, color: "#f1f5f9", textAlign: "center" },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  label: { fontSize: 13, fontWeight: 600, color: "#94a3b8" },
  input: { padding: "10px 14px", borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#e2e8f0", fontSize: 14 },
  btn: { marginTop: 8, padding: "12px", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontWeight: 700, fontSize: 15, cursor: "pointer" },
  error: { color: "#f87171", fontSize: 13, margin: 0 },
  foot: { textAlign: "center", color: "#64748b", fontSize: 13, marginTop: 16 },
  link: { background: "none", border: "none", color: "#818cf8", cursor: "pointer", fontSize: 13 },
};
