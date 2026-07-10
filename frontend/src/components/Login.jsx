import { useState } from "react";
import "./Login.css";
import { useNavigate } from "react-router-dom";
import user_icon from "../assets/person.png";
import email_icon from "../assets/email.png";
import password_icon from "../assets/password.png";
import { API_BASE } from "../api/config";

const Login = ({ onAuth }) => {
  const navigate = useNavigate();
  const [action, setAction] = useState("Sign Up");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [messageKey, setMessageKey] = useState(0);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const extractError = (detail) => {
    if (!detail) return "Request failed";
    if (Array.isArray(detail)) return detail[0]?.msg || "Request failed";
    if (typeof detail === "object") return detail.msg || JSON.stringify(detail);
    return String(detail);
  };

  const showMessage = (msg) => {
    setMessageKey((k) => k + 1);
    setMessage(msg);
  };

  const handleSubmit = async () => {
    if (!form.email.trim()) {
      showMessage("Email is required");
      return;
    }
    if (form.password.length < 8) {
      showMessage("Password must be at least 8 characters");
      return;
    }

    setMessage("");
    setLoading(true);
    const endpoint = action === "Sign Up" ? "/auth/register" : "/auth/login";
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.email, password: form.password }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(extractError(data?.detail));

      if (action === "Sign Up") {
        showMessage("Account created! You can now login.");
        setTimeout(() => setMessage(""), 3000);
      } else {
        onAuth({ email: data.email ?? form.email, token: data.token });
        navigate("/dashboard");
      }
    } catch (err) {
      showMessage(err.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = () => {
    onAuth(null);
    navigate("/dashboard");
  };

  return (
    <>
      <div className="brand-header">
        <span className="brand-header__logo">⚡</span>
        <span className="brand-header__name">PromptBox</span>
        <p className="brand-header__tag">LLM Prompt Testing & Version Control</p>
      </div>
      <div className="container">
        <div className="header">
          <div className="text">{action}</div>
          <div className="underline"></div>
        </div>
        <div className="inputs">
          {action === "Login" ? null : (
            <div className="input">
              <img src={user_icon} alt="" />
              <input
                type="text"
                placeholder="Name"
                value={form.name}
                onChange={handleChange("name")}
              />
            </div>
          )}
          <div className="input">
            <img src={email_icon} alt="" />
            <input
              type="email"
              placeholder="Email Id"
              value={form.email}
              onChange={handleChange("email")}
            />
          </div>
          <div className="input">
            <img src={password_icon} alt="" />
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange("password")}
            />
          </div>
        </div>
        

        {message && <div className="message" key={messageKey}>{message}</div>}

        <div className="submit-container">
          <div
            className={action === "Login" ? "submit gray" : "submit"}
            onClick={() => action === "Sign Up" ? handleSubmit() : setAction("Sign Up")}
            data-testid="signup-btn"
          >
            Sign Up
          </div>
          <div
            className={action === "Sign Up" ? "submit gray" : "submit"}
            onClick={() => action === "Login" ? handleSubmit() : setAction("Login")}
            data-testid="login-btn"
          >
            Login
          </div>
          <div
            className="submit guest"
            onClick={handleGuest}
            data-testid="guest-btn"
          >
            Continue as Guest
          </div>
        </div>
      </div>
    </>
  );
};

export default Login;
