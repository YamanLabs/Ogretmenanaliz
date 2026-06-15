"use client";

import React, { useState, useEffect } from "react";
import { Key, Eye, EyeOff, Trash2, X, AlertCircle } from "lucide-react";

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (key: string) => void;
}

export function ApiKeyModal({ isOpen, onClose, onSave }: ApiKeyModalProps) {
  const [apiKey, setApiKey] = useState<string>("");
  const [showKey, setShowKey] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load key from localStorage when modal opens
  useEffect(() => {
    if (isOpen) {
      const savedKey = localStorage.getItem("gemini_api_key") || "";
      setApiKey(savedKey);
      setErrorMsg(null);
      setShowKey(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    const trimmedKey = apiKey.trim();
    if (!trimmedKey) {
      setErrorMsg("Lütfen geçerli bir API anahtarı girin.");
      return;
    }
    
    // Simple format check (Gemini API keys typically start with AIzaSy)
    if (!trimmedKey.startsWith("AIzaSy")) {
      if (!window.confirm("Girdiğiniz anahtar standart Gemini API anahtarı formatına ('AIzaSy...') benzemiyor. Yine de kaydetmek istiyor musunuz?")) {
        return;
      }
    }

    localStorage.setItem("gemini_api_key", trimmedKey);
    onSave(trimmedKey);
    onClose();
  };

  const handleClear = () => {
    if (window.confirm("Kayıtlı Gemini API anahtarını silmek istediğinizden emin misiniz?")) {
      localStorage.removeItem("gemini_api_key");
      setApiKey("");
      onSave("");
      setErrorMsg(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 transition-opacity duration-300">
      <div 
        className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden transform scale-100 transition-all duration-300 flex flex-col"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-violet-700 to-indigo-800 px-6 py-4 flex items-center justify-between text-white">
          <div className="flex items-center gap-2.5">
            <Key className="w-5 h-5 text-indigo-200" />
            <h2 className="text-base font-bold tracking-wide">Gemini API Anahtarı</h2>
          </div>
          <button 
            onClick={onClose}
            className="text-white/80 hover:text-white transition p-1 hover:bg-white/10 rounded-lg"
            aria-label="Kapat"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex flex-col gap-4">
          <div className="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 rounded-lg p-3">
            <p className="font-semibold text-slate-800 mb-1">🔒 Güvenli ve Yerel Saklama</p>
            API anahtarınız sadece tarayıcınızda (<code className="bg-slate-200 px-1 py-0.5 rounded font-mono text-[10px]">localStorage</code>) saklanır. 
            Sunucuya kalıcı olarak kaydedilmez, her görsel analizinde doğrudan backend üzerinden API isteğine eklenir.
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Gemini API Key
            </label>
            <div className="relative flex items-center">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  if (errorMsg) setErrorMsg(null);
                }}
                placeholder="AIzaSy..."
                className="w-full pl-3 pr-20 py-2.5 text-sm font-mono border border-slate-200 rounded-lg focus:outline-hidden focus:border-violet-600 focus:ring-1 focus:ring-violet-600 transition"
              />
              <div className="absolute right-2 flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 transition hover:bg-slate-100 rounded-md"
                  title={showKey ? "Gizle" : "Göster"}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                {localStorage.getItem("gemini_api_key") && (
                  <button
                    type="button"
                    onClick={handleClear}
                    className="p-1.5 text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition rounded-md"
                    title="Anahtarı Temizle"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {errorMsg && (
            <div className="flex items-center gap-2 p-2.5 bg-rose-50 border border-rose-100 text-rose-800 text-xs rounded-lg font-medium animate-pulse">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="text-[10px] text-slate-500">
            API anahtarınız yoksa, Google AI Studio üzerinden ücretsiz bir tane alabilirsiniz.
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-6 py-4 flex justify-between items-center gap-3 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-700 transition"
          >
            Şimdilik Atla
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 bg-violet-700 hover:bg-violet-800 text-white text-xs font-bold rounded-lg transition shadow-sm hover:shadow"
          >
            Kaydet
          </button>
        </div>
      </div>
    </div>
  );
}
