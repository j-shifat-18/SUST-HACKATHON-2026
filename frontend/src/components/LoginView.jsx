"use client";

import React, { useState, useEffect, useRef } from "react";
import { RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";
import { auth } from "../../firebase/firebase.init";
import { AlertCircle, CheckCircle } from "lucide-react";

export default function LoginView({ onLoginSuccess }) {
  const [authMode, setAuthMode] = useState("signin");
  const [formData, setFormData] = useState({
    name: "",
    phone: "+880",
    language: "English",
    division: "Dhaka",
    district: ""
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
        } catch (e) {
          console.error("Recaptcha cleanup error", e);
        }
      }
    };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const initRecaptchaVerifier = () => {
    try {
      if (!window.recaptchaVerifier) {
        window.recaptchaVerifier = new RecaptchaVerifier(auth, "recaptcha-container", {
          size: "invisible",
          callback: (response) => {}
        });
      }
    } catch (err) {
      console.error("Recaptcha init error", err);
      setErrorMsg("Failed to initialize safety reCAPTCHA. Please reload.");
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

    // Check if phone number is already registered in local storage
    const checkDuplicatePhone = () => {
      const inputDigits = formData.phone.replace(/\D/g, "");
      if (inputDigits.length < 10) return false;
      const inputLast10 = inputDigits.slice(-10);

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith("cashscope_profile_")) {
          try {
            const profile = JSON.parse(localStorage.getItem(key));
            if (profile && profile.phone) {
              const storedDigits = String(profile.phone).replace(/\D/g, "");
              if (storedDigits.length >= 10) {
                const storedLast10 = storedDigits.slice(-10);
                if (inputLast10 === storedLast10) {
                  console.warn("Duplicate phone match found in storage:", { key, profile });
                  return true;
                }
              }
            }
          } catch (e) {
            console.error("Local storage read error", e);
          }
        }
      }
      return false;
    };

    if (authMode === "register") {
      if (!formData.name.trim()) {
        setErrorMsg("Full name is required to register.");
        return;
      }
      if (!formData.district.trim()) {
        setErrorMsg("District is required to register.");
        return;
      }
      if (checkDuplicatePhone()) {
        setErrorMsg("This phone number is already registered. Please Sign In instead.");
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
      setSuccessMsg("Verification code sent successfully to your phone!");
    } catch (err) {
      console.error("OTP send error", err);
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

      try {
        const token = await user.getIdToken();
        console.log("Firebase Access Token:", token);
      } catch (tokenErr) {
        console.error("Failed to retrieve ID token:", tokenErr);
      }

      if (authMode === "register") {
        let idToken = "";
        try {
          idToken = await user.getIdToken();
        } catch (tokenErr) {
          console.error("Token generation error:", tokenErr);
        }

        const phoneValue = user.phoneNumber || formData.phone;
        try {
          const response = await fetch("http://localhost:8000/api/v1/users", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": idToken ? `Bearer ${idToken}` : ""
            },
            body: JSON.stringify({
              phone: phoneValue,
              name: formData.name,
              region: formData.division,
              area: formData.district
            })
          });

          if (!response.ok) {
            const errBody = await response.json().catch(() => ({}));
            throw new Error(errBody.message || `Server responded with status ${response.status}`);
          }
          console.log("Backend registration successful");
        } catch (apiErr) {
          console.error("Failed to post user metadata to backend API:", apiErr);
          setErrorMsg("Failed to store profile details on the backend at localhost:8000. Please ensure the backend server is running.");
          return;
        }

        // Registration mode: save new metadata profile
        const userProfile = {
          uid: user.uid,
          name: formData.name,
          phone: phoneValue,
          language: formData.language,
          division: formData.division,
          district: formData.district
        };
        localStorage.setItem(`cashscope_profile_${user.uid}`, JSON.stringify(userProfile));
        localStorage.setItem("cashscope_active_user_uid", user.uid);
        setSuccessMsg("Account created and verified successfully!");
        setTimeout(() => {
          onLoginSuccess(userProfile);
        }, 500);
      } else {
        // Sign-in mode: retrieve existing metadata profile
        const stored = localStorage.getItem(`cashscope_profile_${user.uid}`);
        if (stored) {
          const userProfile = JSON.parse(stored);
          setSuccessMsg("Verified and logged in successfully!");
          setTimeout(() => {
            onLoginSuccess(userProfile);
          }, 500);
        } else {
          // No profile details exist yet for this phone number: route to complete profile details
          setSuccessMsg("OTP Verified! Complete profile details to activate dashboard.");
          setAuthMode("register");
          setOtpSent(false);
          setOtp("");
          setFormData(prev => ({
            ...prev,
            phone: user.phoneNumber || prev.phone
          }));
        }
      }
    } catch (err) {
      console.error("OTP verify error", err);
      setErrorMsg("Invalid verification code. Please check and try again.");
    } finally {
      setLoading(false);
    }
  };

  const toggleAuthMode = () => {
    setAuthMode(prev => (prev === "signin" ? "register" : "signin"));
    setOtpSent(false);
    setOtp("");
    setErrorMsg("");
    setSuccessMsg("");
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 className="text-4xl font-extrabold tracking-wider">
          CashScope
        </h1>
        <p className="mt-2 text-sm text-muted-custom">
          {authMode === "signin" ? "Sign in to your account" : "Create a new CashScope profile"}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-4 border border-border-custom rounded-2xl shadow-lg sm:px-10">
          
          {/* Notifications */}
          {errorMsg && (
            <div className="mb-4 p-3 bg-error-custom/10 border border-error-custom/25 rounded-lg flex items-start gap-2 text-xs text-error-custom">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3 bg-success-custom/10 border border-success-custom/25 rounded-lg flex items-start gap-2 text-xs text-success-custom">
              <CheckCircle size={16} className="shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Form */}
          {!otpSent ? (
            <form onSubmit={handleSendOtp} className="space-y-4">
              
              {authMode === "register" && (
                <>
                  <div>
                    <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Enter full name"
                      className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-secondary"
                      disabled={loading}
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="e.g. +88017XXXXXXXX"
                  className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-secondary font-mono"
                  disabled={loading}
                />
              </div>

              {authMode === "register" && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                        Language
                      </label>
                      <select
                        name="language"
                        value={formData.language}
                        onChange={handleInputChange}
                        className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-secondary"
                        disabled={loading}
                      >
                        <option value="English">English</option>
                        <option value="Bengali">Bengali (বাংলা)</option>
                        <option value="Banglish">Both</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                        Division
                      </label>
                      <select
                        name="division"
                        value={formData.division}
                        onChange={handleInputChange}
                        className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-secondary"
                        disabled={loading}
                      >
                        <option value="Dhaka">Dhaka</option>
                        <option value="Sylhet">Sylhet</option>
                        <option value="Chittagong">Chittagong</option>
                        <option value="Rajshahi">Rajshahi</option>
                        <option value="Rangpur">Rangpur</option>
                        <option value="Khulna">Khulna</option>
                        <option value="Barishal">Barishal</option>
                        <option value="Mymensingh">Mymensingh</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                      District
                    </label>
                    <input
                      type="text"
                      name="district"
                      value={formData.district}
                      onChange={handleInputChange}
                      placeholder="Enter district (e.g. Sylhet)"
                      className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-secondary"
                      disabled={loading}
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-secondary hover:bg-secondary/90 text-white font-bold py-2.5 px-4 rounded-lg text-sm transition-colors shadow-sm focus:outline-none cursor-pointer flex justify-center items-center gap-2"
              >
                {loading && (
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                )}
                {authMode === "signin" ? "Send Sign In OTP" : "Send Registration OTP"}
              </button>

              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={toggleAuthMode}
                  className="text-xs font-semibold text-secondary hover:underline cursor-pointer focus:outline-none"
                >
                  {authMode === "signin"
                    ? "Don't have an account? Register"
                    : "Already registered? Sign In"}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-heading uppercase tracking-wide mb-1">
                  Verification Code (OTP)
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="Enter 6-digit code"
                  className="w-full bg-background border border-border-custom text-text-main rounded-lg px-3 py-2 text-sm text-center font-bold tracking-widest focus:outline-none focus:border-secondary"
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-primary/90 text-heading font-bold py-2.5 px-4 rounded-lg text-sm transition-colors shadow-sm focus:outline-none cursor-pointer flex justify-center items-center gap-2"
              >
                {loading && (
                  <span className="w-4 h-4 rounded-full border-2 border-heading/30 border-t-heading animate-spin"></span>
                )}
                {authMode === "signin" ? "Verify & Sign In" : "Verify & Register"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setOtpSent(false);
                  setOtp("");
                  setErrorMsg("");
                  setSuccessMsg("");
                }}
                className="w-full bg-slate-100 hover:bg-slate-200 text-muted-custom py-2 rounded-lg text-xs font-semibold transition-colors focus:outline-none"
              >
                Back to credentials
              </button>
            </form>
          )}

          <div id="recaptcha-container" className="mt-2"></div>

        </div>
      </div>
    </div>
  );
}
