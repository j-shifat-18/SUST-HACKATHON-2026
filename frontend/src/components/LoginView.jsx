"use client";

import React, { useState, useEffect, useRef } from "react";
import { RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";
import { auth } from "../../firebase/firebase.init";
import { AlertCircle, CheckCircle, Shield } from "lucide-react";

export default function LoginView({ onLoginSuccess }) {
  const [authMode, setAuthMode] = useState("signin");
  const [formData, setFormData] = useState({
    name: "",
    phone: "+880",
    language: "English",
    division: "Dhaka",
    district: "",
  });
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const confirmationResultRef = useRef(null);

  useEffect(() => {
    return () => {
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear();
          window.recaptchaVerifier = null;
        } catch (e) {}
      }
    };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const initRecaptchaVerifier = () => {
    if (!window.recaptchaVerifier) {
      window.recaptchaVerifier = new RecaptchaVerifier(auth, "recaptcha-container", {
        size: "invisible",
        callback: () => {},
      });
    }
  };

  const handleSendOtp = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!formData.phone.trim() || formData.phone.length < 10) {
      setErrorMsg("Please enter a valid phone number with country code.");
      return;
    }

    if (authMode === "register") {
      if (!formData.name.trim()) {
        setErrorMsg("Full name is required to register.");
        return;
      }
      if (!formData.district.trim()) {
        setErrorMsg("District is required to register.");
        return;
      }
    }

    setLoading(true);
    try {
      initRecaptchaVerifier();
      const appVerifier = window.recaptchaVerifier;
      const result = await signInWithPhoneNumber(auth, formData.phone, appVerifier);
      confirmationResultRef.current = result;
      setOtpSent(true);
      setSuccessMsg("Verification code sent successfully!");
    } catch (err) {
      setErrorMsg(err.message || "Failed to send code. Verify phone number format (+8801...)");
      if (window.recaptchaVerifier) {
        window.recaptchaVerifier.clear();
        window.recaptchaVerifier = null;
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (otp.length !== 6) {
      setErrorMsg("Verification code must be exactly 6 digits.");
      return;
    }

    setLoading(true);
    try {
      const userCredential = await confirmationResultRef.current.confirm(otp);
      const user = userCredential.user;

      if (authMode === "register") {
        const idToken = await user.getIdToken();
        const phoneValue = user.phoneNumber || formData.phone;

        await fetch("http://localhost:8000/api/v1/users", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${idToken}`,
          },
          body: JSON.stringify({
            phone: phoneValue,
            name: formData.name,
            region: formData.division,
            area: formData.district,
          }),
        });

        const userProfile = {
          uid: user.uid,
          name: formData.name,
          phone: phoneValue,
          language: formData.language,
          division: formData.division,
          district: formData.district,
          role: "operator",
        };
        setSuccessMsg("Account created!");
        setTimeout(() => onLoginSuccess(userProfile), 500);
      } else {
        const idToken = await user.getIdToken();
        let userProfile = null;

        try {
          const response = await fetch(
            `http://localhost:8000/api/v1/users?phone=${encodeURIComponent(user.phoneNumber)}`,
            { headers: { Authorization: `Bearer ${idToken}` } }
          );
          if (response.ok) {
            const data = await response.json();
            const matchedUser = Array.isArray(data)
              ? data.find(
                  (u) =>
                    String(u.phone).replace(/\D/g, "").slice(-10) ===
                    String(user.phoneNumber).replace(/\D/g, "").slice(-10)
                )
              : data;
            if (matchedUser) {
              userProfile = {
                uid: user.uid,
                id: matchedUser.id,
                name: matchedUser.name,
                phone: matchedUser.phone,
                language: matchedUser.language || "English",
                division: matchedUser.region,
                district: matchedUser.area,
                role: matchedUser.role,
              };
            }
          }
        } catch {}

        if (userProfile) {
          setSuccessMsg("Logged in!");
          setTimeout(() => onLoginSuccess(userProfile), 500);
        } else {
          setSuccessMsg("OTP Verified! Complete your profile.");
          setAuthMode("register");
          setOtpSent(false);
          setOtp("");
          setFormData((prev) => ({ ...prev, phone: user.phoneNumber || prev.phone }));
        }
      }
    } catch {
      setErrorMsg("Invalid verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const toggleAuthMode = () => {
    setAuthMode((prev) => (prev === "signin" ? "register" : "signin"));
    setOtpSent(false);
    setOtp("");
    setErrorMsg("");
    setSuccessMsg("");
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Shield className="w-8 h-8 text-primary" />
          <h1 className="text-3xl font-bold text-heading tracking-wide">CashScope</h1>
        </div>
        <p className="text-sm text-muted-custom">
          {authMode === "signin" ? "Sign in to your account" : "Create a new CashScope profile"}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-6 border border-border-custom rounded-2xl shadow-2xl shadow-primary/5">
          {errorMsg && (
            <div className="mb-4 p-3 bg-error-custom/10 border border-error-custom/20 rounded-lg flex items-start gap-2 text-xs text-error-custom">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="mb-4 p-3 bg-primary/10 border border-primary/20 rounded-lg flex items-start gap-2 text-xs text-primary">
              <CheckCircle size={16} className="shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {!otpSent ? (
            <form onSubmit={handleSendOtp} className="space-y-4">
              {authMode === "register" && (
                <div>
                  <label className="block text-xs font-semibold text-muted-custom uppercase tracking-wide mb-1.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter full name"
                    className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
                    disabled={loading}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-muted-custom uppercase tracking-wide mb-1.5">
                  Phone Number
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="+88017XXXXXXXX"
                  className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
                  disabled={loading}
                />
              </div>

              {authMode === "register" && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-muted-custom uppercase tracking-wide mb-1.5">
                        Division
                      </label>
                      <select
                        name="division"
                        value={formData.division}
                        onChange={handleInputChange}
                        className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-primary transition-all"
                        disabled={loading}
                      >
                        {["Dhaka", "Sylhet", "Chittagong", "Rajshahi", "Rangpur", "Khulna", "Barishal", "Mymensingh"].map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-muted-custom uppercase tracking-wide mb-1.5">
                        District
                      </label>
                      <input
                        type="text"
                        name="district"
                        value={formData.district}
                        onChange={handleInputChange}
                        placeholder="e.g. Sylhet"
                        className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
                        disabled={loading}
                      />
                    </div>
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-primary-light text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-all shadow-lg shadow-primary/20 focus:outline-none cursor-pointer flex justify-center items-center gap-2 mt-6"
              >
                {loading && <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />}
                {authMode === "signin" ? "Send Sign In OTP" : "Send Registration OTP"}
              </button>

              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={toggleAuthMode}
                  className="text-xs font-medium text-primary hover:text-primary-light cursor-pointer transition-colors"
                >
                  {authMode === "signin" ? "Don't have an account? Register" : "Already registered? Sign In"}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-muted-custom uppercase tracking-wide mb-1.5">
                  Verification Code (OTP)
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="Enter 6-digit code"
                  className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm text-center font-bold tracking-[0.3em] focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-primary-light text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-all shadow-lg shadow-primary/20 focus:outline-none cursor-pointer flex justify-center items-center gap-2"
              >
                {loading && <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />}
                {authMode === "signin" ? "Verify & Sign In" : "Verify & Register"}
              </button>

              <button
                type="button"
                onClick={() => { setOtpSent(false); setOtp(""); setErrorMsg(""); setSuccessMsg(""); }}
                className="w-full bg-surface-elevated hover:bg-surface-hover text-muted-custom py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer"
              >
                ← Back
              </button>
            </form>
          )}

          <div id="recaptcha-container" className="mt-2" />
        </div>
      </div>
    </div>
  );
}
