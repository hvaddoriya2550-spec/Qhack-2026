import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Sparkles,
  ShieldCheck,
  LineChart,
  Zap,
  Mail,
  Lock,
} from "lucide-react";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function HomePage() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const [loginError, setLoginError] = useState("");

  const handleLogin = (event) => {
    event.preventDefault();
    if (formData.email === "cleo@cloover.com" && formData.password === "cleoai") {
      setLoginError("");
      navigate("/form");
    } else {
      setLoginError("Invalid email or password");
    }
  };

  return (
    <div className="login-home-page">
      <div className="login-bg-glow login-glow-1"></div>
      <div className="login-bg-glow login-glow-2"></div>
      <div className="login-grid-overlay"></div>

      <section className="login-hero-section">
        <motion.div
          className="login-hero-left"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants} className="login-brand">
            Cleo
          </motion.div>

          <motion.div variants={itemVariants}>
            <div className="badge">
              <Sparkles size={16} />
              <span>AI-Powered Sales Intelligence</span>
            </div>
          </motion.div>

          <motion.h1 variants={itemVariants}>
            Installer financing and
            <span className="gradient-text"> sales coaching</span>
            <br />
            in one workspace
          </motion.h1>

          <motion.p variants={itemVariants} className="login-hero-description">
            Turn lead information into financing-ready recommendations,
            structured project insights, and guided sales conversations with a
            modern AI sales workflow.
          </motion.p>

          <motion.div variants={itemVariants} className="login-feature-list">
            <motion.div
              className="login-feature-item"
              whileHover={{ x: 6, boxShadow: "0 8px 30px rgba(53,53,243,0.12)" }}
              transition={{ duration: 0.2 }}
            >
              <ShieldCheck size={18} />
              <span>Smarter lead qualification</span>
            </motion.div>

            <motion.div
              className="login-feature-item"
              whileHover={{ x: 6, boxShadow: "0 8px 30px rgba(53,53,243,0.12)" }}
              transition={{ duration: 0.2 }}
            >
              <LineChart size={18} />
              <span>Structured recommendations and financing insights</span>
            </motion.div>

            <motion.div
              className="login-feature-item"
              whileHover={{ x: 6, boxShadow: "0 8px 30px rgba(53,53,243,0.12)" }}
              transition={{ duration: 0.2 }}
            >
              <Zap size={18} />
              <span>Voice-powered sales coaching on the go</span>
            </motion.div>
          </motion.div>
        </motion.div>

        <motion.div
          className="login-hero-right"
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
        >
          <motion.div
            className="login-card"
            whileHover={{ y: -4 }}
            transition={{ duration: 0.3 }}
          >
            <div className="login-card-header">
              <p className="section-kicker">Welcome back</p>
              <h2>Sign in to Cleo</h2>
              <p className="login-card-subtitle">
                Access your lead analysis workspace and generate sales-ready
                reports.
              </p>
            </div>

            <form className="login-form" onSubmit={handleLogin}>
              <div className="input-group">
                <label>Email address</label>
                <div className="input-shell">
                  <Mail size={18} />
                  <input
                    type="email"
                    name="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Password</label>
                <div className="input-shell">
                  <Lock size={18} />
                  <input
                    type="password"
                    name="password"
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="login-meta-row">
                <label className="remember-row">
                  <input type="checkbox" />
                  <span>Remember me</span>
                </label>

                <button
                  type="button"
                  className="text-link-btn"
                  onClick={() => alert("Support feature coming soon")}
                >
                  Need help?
                </button>
              </div>

              <motion.button
                className="primary-btn login-submit-btn"
                type="submit"
                whileHover={{ scale: 1.02, boxShadow: "0 8px 30px rgba(53,53,243,0.3)" }}
                whileTap={{ scale: 0.97 }}
              >
                Login
                <ArrowRight size={18} />
              </motion.button>
            </form>

            {loginError && (
              <p style={{ margin: "12px 0 0", textAlign: "center", color: "#ef4444", fontSize: "0.88rem", fontWeight: 500 }}>
                {loginError}
              </p>
            )}

            <div className="login-footer-note">
              Secure access for installer and sales workflows
            </div>
          </motion.div>
        </motion.div>
      </section>
    </div>
  );
}
