"use client";

import React, { useState, useEffect } from "react";
import { 
  Upload, 
  Save, 
  FileSpreadsheet, 
  TrendingUp, 
  CheckCircle, 
  AlertCircle,
  Database,
  RefreshCw,
  HelpCircle,
  Trash2,
  Printer,
  Key
} from "lucide-react";
import { ExtractedStudent } from "../components/types";
import { AcademicTable } from "../components/AcademicTable";
import { GrowthTable } from "../components/GrowthTable";
import { AnalyticsChart } from "../components/AnalyticsChart";
import { ApiKeyModal } from "../components/ApiKeyModal";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export default function DashboardPage() {
  const [className, setClassName] = useState<string>("10-A");
  const [classId, setClassId] = useState<number | null>(null);
  const [students, setStudents] = useState<ExtractedStudent[]>([]);
  const [activeTab, setActiveTab] = useState<"academic" | "growth">("academic");
  const [processor, setProcessor] = useState<"local" | "gemini">("local");
  
  // Status states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState<boolean>(false);

  // Check Gemini API Key on initial mount
  useEffect(() => {
    const savedKey = localStorage.getItem("gemini_api_key");
    if (!savedKey) {
      setIsApiKeyModalOpen(true);
    }
  }, []);

  // Load from LocalStorage on mount/class change
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const cachedData = localStorage.getItem(`eokul_students_${className}`);
    const cachedId = localStorage.getItem(`eokul_class_id_${className}`);
    
    if (cachedData) {
      try {
        setStudents(JSON.parse(cachedData));
        if (cachedId) setClassId(parseInt(cachedId, 10));
      } catch (e) {
        console.error("Failed to parse cached student data", e);
      }
    } else {
      setStudents([]);
      setClassId(null);
    }
  }, [className]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const showToast = (type: "success" | "error" | "info", text: string) => {
    setStatusMsg({ type, text });
    setTimeout(() => {
      setStatusMsg((prev) => (prev?.text === text ? null : prev));
    }, 4500);
  };

  // Sync cache with current state
  const updateCache = (newStudents: ExtractedStudent[], id: number | null) => {
    localStorage.setItem(`eokul_students_${className}`, JSON.stringify(newStudents));
    if (id !== null) {
      localStorage.setItem(`eokul_class_id_${className}`, id.toString());
    } else {
      localStorage.removeItem(`eokul_class_id_${className}`);
    }
  };

  // Fetch from Database
  const handleFetchFromDB = async () => {
    if (!className) return;
    setIsLoading(true);
    showToast("info", "Veritabanından en güncel notlar sorgulanıyor...");

    try {
      // Sınıf ID'sini bulmak için önce veri tabanını veya LocalStorage'ı tararız
      // ID yoksa isme göre veri tabanından sorgulama simüle edilir
      // API'den doğrudan getireceğiz, class_id'yi LocalStorage'dan alıyoruz
      let cid = classId;
      if (!cid) {
        // En yüksek olasılıklı ID 1 (eğer ilk oluşturulansa)
        cid = 1; 
      }

      const res = await fetch(`${BACKEND_URL}/api/grades/${cid}?term=2024-2025-1`);
      if (!res.ok) {
        throw new Error("Sınıf veritabanında bulunamadı veya henüz kaydedilmemiş.");
      }

      const dbStudents: ExtractedStudent[] = await res.json();
      setStudents(dbStudents);
      setClassId(cid);
      updateCache(dbStudents, cid);
      showToast("success", `Sınıf '${className}' veritabanı kayıtları başarıyla çekildi.`);
    } catch (err: unknown) {
      loggerError(err);
      showToast("error", getErrorMessage(err, "Veritabanı bağlantısı kurulamadı. Lütfen API sunucusunun açık olduğunu kontrol edin."));
    } finally {
      setIsLoading(false);
    }
  };

  const loggerError = (msg: unknown) => {
    console.error("API error:", msg);
  };

  // Clear Class Data from database and local cache
  const handleClearClassData = async () => {
    if (!className) return;
    
    const confirmClear = window.confirm(
      `'${className}' sınıfına ait TÜM verileri (öğrenciler ve notlar dahil) silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz!`
    );
    if (!confirmClear) return;

    setIsLoading(true);
    showToast("info", `'${className}' sınıfı verileri temizleniyor...`);

    try {
      const res = await fetch(`${BACKEND_URL}/api/grades/class/${className}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        if (res.status === 404) {
          console.log("Sınıf veritabanında bulunamadı, sadece yerel veriler temizleniyor.");
        } else {
          const errorData = await res.json();
          throw new Error(errorData.detail || "Veritabanından silinirken bir hata oluştu.");
        }
      }

      // Clear local state and cache
      setStudents([]);
      setClassId(null);
      localStorage.removeItem(`eokul_students_${className}`);
      localStorage.removeItem(`eokul_class_id_${className}`);

      showToast("success", `'${className}' sınıfı verileri başarıyla temizlendi.`);
    } catch (err: unknown) {
      loggerError(err);
      showToast("error", getErrorMessage(err, "Veri temizlenirken bir hata oluştu."));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectGemini = () => {
    const savedKey = localStorage.getItem("gemini_api_key");
    if (!savedKey) {
      showToast("info", "Gemini'yi kullanabilmek için lütfen önce API anahtarınızı girin.");
      setIsApiKeyModalOpen(true);
    } else {
      setProcessor("gemini");
    }
  };

  const handleSaveApiKey = (key: string) => {
    if (key) {
      setProcessor("gemini");
      showToast("success", "Gemini API anahtarı kaydedildi. Gemini tarama yöntemi etkinleştirildi.");
    } else {
      setProcessor("local");
      showToast("info", "Gemini API anahtarı temizlendi. Yerel OCR yöntemine geçildi.");
    }
  };

  // Upload Screenshot (OCR)
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (processor === "gemini") {
      const savedKey = localStorage.getItem("gemini_api_key") || "";
      if (!savedKey) {
        showToast("error", "Gemini ile analiz yapmak için geçerli bir API anahtarı girmelisiniz.");
        setIsApiKeyModalOpen(true);
        event.target.value = "";
        return;
      }
    }

    setIsLoading(true);
    showToast(
      "info",
      processor === "gemini" ? "Gemini analiz ediyor..." : "Yerel OCR çalışıyor..."
    );

    const formData = new FormData();
    formData.append("file", file);
    formData.append("class_name", className);
    formData.append("processor", processor);

    if (processor === "gemini") {
      const savedKey = localStorage.getItem("gemini_api_key") || "";
      formData.append("gemini_api_key", savedKey);
    }

    try {
      const res = await fetch(`${BACKEND_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Görsel işlenirken bir hata oluştu.");
      }

      const data = await res.json();
      
      // Update state
      const processedStudents: ExtractedStudent[] = data.students;
      setStudents(processedStudents);
      setClassId(data.class_id);
      updateCache(processedStudents, data.class_id);

      showToast(
        "success",
        `${processor === "gemini" ? "Gemini analizi" : "Yerel OCR"} tamamlandı. ${data.total_rows} öğrenci notu ayıklandı.`
      );
    } catch (err: unknown) {
      loggerError(err);
      showToast("error", getErrorMessage(err, "Görsel işleme sunucusuna ulaşılamadı. Lütfen API'nin çalıştığını kontrol edin."));
    } finally {
      setIsLoading(false);
      // Reset input element
      event.target.value = "";
    }
  };

  // Handle single student local state update (calculates averages automatically)
  const handleUpdateStudent = (schoolNo: string, updatedFields: Partial<ExtractedStudent>) => {
    const updated = students.map((s) => {
      if (s.school_no !== schoolNo) return s;

      const merged = { ...s, ...updatedFields };

      // Recalculate average and status for Tab 1 academic changes
      const s1 = merged.exam1;
      const s2 = merged.exam2;
      const p1 = merged.perf1;
      const p2 = merged.perf2;

      // Filter out null or undefined grades
      const validGrades = [s1, s2, p1, p2].filter((g) => g !== null && g !== undefined) as number[];
      
      if (validGrades.length < 4) {
        merged.calculated_average = null;
        merged.status = "Belirsiz";
      } else {
        const sum = validGrades.reduce((acc, val) => acc + val, 0);
        const avg = sum / validGrades.length;
        merged.calculated_average = Math.round(avg * 100) / 100;
        merged.status = avg >= 50.0 ? "Geçti" : "Kaldı";
      }

      return merged;
    });

    setStudents(updated);
    updateCache(updated, classId);
  };

  // Save to SQLite
  const handleSaveGrades = async () => {
    if (students.length === 0) {
      showToast("error", "Kaydedilecek öğrenci verisi bulunmuyor.");
      return;
    }

    setIsLoading(true);
    showToast("info", "Değişiklikler veritabanına kaydediliyor...");

    const gradesPayload = students.map((s) => ({
      school_no: s.school_no,
      name: s.name,
      class_name: className,
      exam1: s.exam1,
      exam2: s.exam2,
      perf1: s.perf1,
      perf2: s.perf2,
      growth_attendance: s.growth_attendance,
      growth_activities: s.growth_activities,
      growth_product: s.growth_product,
      growth_social_emotional: s.growth_social_emotional,
      growth_progress: s.growth_progress,
      term: "2024-2025-1",
    }));

    try {
      const res = await fetch(`${BACKEND_URL}/api/save-grades`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grades: gradesPayload }),
      });

      if (!res.ok) {
        throw new Error("Notlar kaydedilirken bir sunucu hatası oluştu.");
      }

      const result = await res.json();
      if (result.errors && result.errors.length > 0) {
        console.warn("Save warnings:", result.errors);
      }

      showToast(
        "success",
        `Başarıyla kaydedildi! ${result.saved} yeni öğrenci eklendi, ${result.updated} öğrenci kaydı güncellendi.`
      );
    } catch (err: unknown) {
      loggerError(err);
      showToast("error", getErrorMessage(err, "Sunucu bağlantı hatası: Kaydedilemedi."));
    } finally {
      setIsLoading(false);
    }
  };

  // Export Academic Excel
  const handleExportAcademic = async () => {
    if (!classId) {
      showToast("error", "Sınıf veritabanına kaydedilmeden Excel çıktısı alınamaz. Lütfen önce Kaydet butonuna tıklayın.");
      return;
    }
    
    showToast("info", "Akademik not tablosu indiriliyor...");
    window.open(`${BACKEND_URL}/api/export-excel/${classId}`, "_blank");
  };

  // Export Growth Excel
  const handleExportGrowth = async () => {
    if (!classId) {
      showToast("error", "Sınıf veritabanına kaydedilmeden Gelişim Raporu indirilemez. Lütfen önce Kaydet butonuna tıklayın.");
      return;
    }

    showToast("info", "Gelişim raporu Excel tablosu indiriliyor...");
    window.open(`${BACKEND_URL}/api/export-growth-excel/${classId}`, "_blank");
  };

  // Export PDF / Print layout
  const handlePrintDocument = (type: "academic" | "growth", variant: "grades" | "empty") => {
    if (students.length === 0) {
      showToast("error", "Yazdırılacak öğrenci verisi bulunmuyor.");
      return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      showToast("error", "Yeni pencere açılması engellendi. Lütfen pop-up engelleyicinizi kontrol edin.");
      return;
    }

    const today = new Date().toLocaleDateString("tr-TR");
    let docTitle = "";
    if (type === "academic") {
      docTitle = variant === "grades" 
        ? `${className} Sınıfı Fizik Dersi Not Çizelgesi`
        : `${className} Sınıfı Fizik Dersi Boş Değerlendirme Çizelgesi`;
    } else {
      docTitle = variant === "grades"
        ? `${className} Sınıfı Gelişim Değerlendirme Raporu`
        : `${className} Sınıfı Gelişim Değerlendirme Boş Çizelgesi`;
    }

    let tableHeadersHTML = "";
    let tableBodyHTML = "";

    if (type === "academic") {
      tableHeadersHTML = `
        <tr>
          <th style="width: 5%">#</th>
          <th style="width: 15%">Okul No</th>
          <th>Adı Soyadı</th>
          <th style="width: 10%">1. Sınav</th>
          <th style="width: 10%">2. Sınav</th>
          <th style="width: 10%">1. Perf.</th>
          <th style="width: 10%">2. Perf.</th>
          <th style="width: 10%">Ortalama</th>
          <th style="width: 10%">Durum</th>
        </tr>
      `;

      tableBodyHTML = students.map((s, idx) => {
        const avgVal = (variant === "grades" && s.calculated_average !== null) ? s.calculated_average.toFixed(2) : "";
        const statusVal = variant === "grades" ? (s.status || "-") : "";
        
        return `
          <tr>
            <td style="text-align: center;">${idx + 1}</td>
            <td style="text-align: center; font-weight: bold;">${s.school_no}</td>
            <td>${s.name}</td>
            <td style="text-align: center;">${variant === "grades" && s.exam1 !== null ? s.exam1 : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.exam2 !== null ? s.exam2 : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.perf1 !== null ? s.perf1 : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.perf2 !== null ? s.perf2 : ""}</td>
            <td style="text-align: center; font-weight: bold;">${avgVal}</td>
            <td style="text-align: center;">${statusVal}</td>
          </tr>
        `;
      }).join("");
    } else {
      tableHeadersHTML = `
        <tr>
          <th style="width: 5%">#</th>
          <th style="width: 15%">Okul No</th>
          <th>Adı Soyadı</th>
          <th style="width: 13%">Ders Katılım</th>
          <th style="width: 13%">Sınıf Dışı Faal.</th>
          <th style="width: 13%">Ürün Değer.</th>
          <th style="width: 13%">Sosyal Duygusal</th>
          <th style="width: 13%">Öğrenci Gelişimi</th>
        </tr>
      `;

      tableBodyHTML = students.map((s, idx) => {
        return `
          <tr>
            <td style="text-align: center;">${idx + 1}</td>
            <td style="text-align: center; font-weight: bold;">${s.school_no}</td>
            <td>${s.name}</td>
            <td style="text-align: center;">${variant === "grades" && s.growth_attendance !== null ? s.growth_attendance : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.growth_activities !== null ? s.growth_activities : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.growth_product !== null ? s.growth_product : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.growth_social_emotional !== null ? s.growth_social_emotional : ""}</td>
            <td style="text-align: center;">${variant === "grades" && s.growth_progress !== null ? s.growth_progress : ""}</td>
          </tr>
        `;
      }).join("");
    }

    const printContent = `
      <!DOCTYPE html>
      <html lang="tr">
      <head>
        <meta charset="UTF-8">
        <title>${docTitle}</title>
        <style>
          @media print {
            @page {
              size: A4 portrait;
              margin: 15mm 10mm 15mm 10mm;
            }
            body {
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
          }
          body {
            font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #000;
            background-color: #fff;
            margin: 0;
            padding: 0;
          }
          .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px double #000;
            padding-bottom: 10px;
          }
          .header h1 {
            font-size: 14px;
            margin: 0 0 5px 0;
            font-weight: bold;
          }
          .header h2 {
            font-size: 12px;
            margin: 0 0 5px 0;
            font-weight: normal;
          }
          .header .meta-info {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            margin-top: 10px;
            font-weight: bold;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
          }
          th, td {
            border: 1px solid #000;
            padding: 6px 8px;
          }
          td {
            font-size: 11px;
          }
          th {
            background-color: #f2f2f2 !important;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 10px;
            text-align: center;
          }
          tr {
            page-break-inside: avoid;
          }
          .footer-signature {
            margin-top: 40px;
            display: flex;
            justify-content: flex-end;
            page-break-inside: avoid;
          }
          .signature-box {
            text-align: center;
            width: 200px;
            font-weight: bold;
          }
          .signature-box .date {
            margin-bottom: 15px;
            font-weight: normal;
          }
          .signature-box .name-line {
            margin-top: 50px;
            border-top: 1px dotted #000;
            padding-top: 5px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>T.C. MİLLÎ EĞİTİM BAKANLIĞI</h1>
          <h2>2024-2025 EĞİTİM-ÖĞRETİM YILI</h2>
          <h1 style="font-size: 13px; margin-top: 5px;">
            ${className} SINIFI FİZİK DERSİ ${type === "academic" ? "AKADEMİK NOT" : "GELİŞİM DEĞERLENDİRME"} ${variant === "grades" ? "ÇİZELGESİ" : "BOŞ DEĞERLENDİRME ÖLÇEĞİ"}
          </h1>
          <div class="meta-info">
            <span>Ders: Fizik</span>
            <span>Sınıf: ${className}</span>
            <span>Tarih: ${today}</span>
          </div>
        </div>

        <table>
          <thead>
            ${tableHeadersHTML}
          </thead>
          <tbody>
            ${tableBodyHTML}
          </tbody>
        </table>

        <div class="footer-signature">
          <div class="signature-box">
            <div class="date">İmza Tarihi: ..... / ..... / 20...</div>
            <div>Fizik Dersi Öğretmeni</div>
            <div class="name-line">Adı Soyadı / İmza</div>
          </div>
        </div>

        <script>
          window.onload = function() {
            window.print();
            setTimeout(function() {
              window.close();
            }, 500);
          };
        </script>
      </body>
      </html>
    `;

    printWindow.document.open();
    printWindow.document.write(printContent);
    printWindow.document.close();
  };

  return (
    <div className="min-height-screen bg-slate-50 flex flex-col font-sans antialiased text-slate-800">
      {/* Navbar header */}
      <header className="bg-[#2b3e50] text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-[#1976d2] bg-white rounded p-1" />
            <div>
              <h1 className="text-lg font-bold tracking-tight">Fizik Dersi Değerlendirme Paneli</h1>
              <p className="text-[11px] text-slate-300 font-medium">e-Okul Uyumlu Akademik ve Gelişim Matrisi</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <Database className="w-3.5 h-3.5 mr-1" /> Yerel SQLite Aktif
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6">
        
        {/* Toast Notification */}
        {statusMsg && (
          <div className={`p-4 rounded-lg border text-sm font-semibold flex items-center gap-3 shadow-md animate-bounce ${
            statusMsg.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" :
            statusMsg.type === "error" ? "bg-rose-50 border-rose-200 text-rose-800" :
            "bg-blue-50 border-blue-200 text-blue-800"
          }`}>
            {statusMsg.type === "success" ? <CheckCircle className="w-5 h-5 text-emerald-600" /> :
             statusMsg.type === "error" ? <AlertCircle className="w-5 h-5 text-rose-600" /> :
             <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Top Control Bar Panel */}
        <section className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col sm:flex-row gap-4 items-center justify-between">
          
          {/* Class input controls */}
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <label htmlFor="class-input" className="text-sm font-bold text-slate-600 uppercase tracking-wider shrink-0">Sınıf Seçimi:</label>
            <input
              id="class-input"
              type="text"
              className="w-28 px-3 py-1.5 text-center text-sm font-bold uppercase border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:border-[#1976d2] focus:ring-1 focus:ring-[#1976d2] outline-none transition"
              value={className}
              onChange={(e) => setClassName(e.target.value.toUpperCase())}
            />
            <button
              onClick={handleFetchFromDB}
              disabled={isLoading}
              title="Veritabanındaki son kayıtları yükle"
              className="flex items-center gap-1.5 px-3.5 py-1.8 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-lg border border-slate-200 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} /> Güncelle
            </button>
            <button
              onClick={handleClearClassData}
              disabled={isLoading || !className}
              title="Sınıfın tüm verilerini sil"
              className="flex items-center gap-1.5 px-3.5 py-1.8 bg-rose-50 hover:bg-rose-100 text-rose-700 text-sm font-semibold rounded-lg border border-rose-200 transition disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" /> Verileri Temizle
            </button>
          </div>

          {/* Action buttons (Screenshot OCR and Save) */}
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto justify-end">
            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Tarama yöntemi
              </span>
              <div className="flex items-center gap-1.5">
                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1">
                  <button
                    type="button"
                    aria-pressed={processor === "local"}
                    disabled={isLoading}
                    onClick={() => setProcessor("local")}
                    className={`rounded-md px-3 py-1.5 text-xs font-bold transition disabled:opacity-50 ${
                      processor === "local"
                        ? "bg-white text-[#1976d2] shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    Yerel OCR
                  </button>
                  <button
                    type="button"
                    aria-pressed={processor === "gemini"}
                    disabled={isLoading}
                    onClick={handleSelectGemini}
                    className={`rounded-md px-3 py-1.5 text-xs font-bold transition disabled:opacity-50 ${
                      processor === "gemini"
                        ? "bg-white text-violet-700 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    Gemini 3.1 Flash-Lite
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setIsApiKeyModalOpen(true)}
                  className="p-1.5 text-slate-400 hover:text-violet-700 hover:bg-violet-50 transition border border-slate-200 rounded-lg bg-white shadow-xs"
                  title="Gemini API Anahtarını Ayarla"
                >
                  <Key className="w-4 h-4" />
                </button>
              </div>
              <span className="max-w-52 text-[10px] leading-tight text-slate-500">
                {processor === "gemini"
                  ? "Görsel Google Gemini API'ye gönderilir."
                  : "Görsel yalnızca bu bilgisayarda işlenir."}
              </span>
            </div>
            
            {/* Screenshot upload */}
            <label className="flex items-center gap-2 px-4 py-2 bg-[#1976d2] hover:bg-[#1565c0] text-white text-sm font-bold rounded-lg cursor-pointer transition shadow-sm hover:shadow active:scale-95 disabled:opacity-50">
              <Upload className="w-4 h-4" />
              <span>e-Okul Ekran Görüntüsü Yükle</span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                disabled={isLoading}
                onChange={handleFileUpload}
              />
            </label>

            {/* Save Database */}
            <button
              onClick={handleSaveGrades}
              disabled={isLoading || students.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-lg transition shadow-sm hover:shadow active:scale-95 disabled:opacity-40"
            >
              <Save className="w-4 h-4" />
              <span>Değişiklikleri Kaydet</span>
            </button>
          </div>
        </section>

        {/* Tab Controls Navigation */}
        <section className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 border-b border-slate-200">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab("academic")}
              className={`px-5 py-3 text-sm font-bold tracking-wide transition border-b-2 -mb-[2px] ${
                activeTab === "academic"
                  ? "border-[#1976d2] text-[#1976d2]"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
              }`}
            >
              Akademik Not Matrisi
            </button>
            <button
              onClick={() => setActiveTab("growth")}
              className={`px-5 py-3 text-sm font-bold tracking-wide transition border-b-2 -mb-[2px] ${
                activeTab === "growth"
                  ? "border-[#1976d2] text-[#1976d2]"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
              }`}
            >
              Gelişim Değerlendirme Matrisi
            </button>
          </div>

          {/* Export and Print Actions */}
          <div className="flex flex-wrap items-center gap-2 pb-2 md:pb-0">
            {activeTab === "academic" ? (
              <>
                <button
                  onClick={handleExportAcademic}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span>Excel&apos;e Aktar</span>
                </button>
                <button
                  onClick={() => handlePrintDocument("academic", "grades")}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <Printer className="w-4 h-4 text-blue-600" />
                  <span>Not Çizelgesi Yazdır (PDF)</span>
                </button>
                <button
                  onClick={() => handlePrintDocument("academic", "empty")}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <Printer className="w-4 h-4 text-slate-500" />
                  <span>Boş Liste Yazdır (PDF)</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleExportGrowth}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span>Excel&apos;e Aktar</span>
                </button>
                <button
                  onClick={() => handlePrintDocument("growth", "grades")}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <Printer className="w-4 h-4 text-blue-600" />
                  <span>Gelişim Çizelgesi Yazdır (PDF)</span>
                </button>
                <button
                  onClick={() => handlePrintDocument("growth", "empty")}
                  disabled={students.length === 0}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-md border border-slate-200 transition disabled:opacity-40"
                >
                  <Printer className="w-4 h-4 text-slate-500" />
                  <span>Boş Liste Yazdır (PDF)</span>
                </button>
              </>
            )}
          </div>
        </section>

        {/* Tab Content Tables and Visual Analytics */}
        <section className="flex flex-col lg:flex-row gap-6 items-start">
          
          {/* Main Table Grid container */}
          <div className="w-full lg:flex-1 flex flex-col gap-4">
            {students.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-16 bg-white border border-slate-200 rounded-lg text-center shadow-sm select-none">
                <Upload className="w-12 h-12 text-slate-300 mb-4 animate-bounce" />
                <h2 className="text-base font-bold text-slate-700 mb-1">Değerlendirme Verisi Bulunmuyor</h2>
                <p className="text-xs text-slate-500 max-w-sm mx-auto mb-6 leading-relaxed">
                  İşlemleri başlatmak için e-okul not giriş ekranı görüntüsünü yukarıdan yükleyin. Ya da sınıf adını yazıp &quot;Güncelle&quot; butonuna basarak veritabanından çekin.
                </p>
                <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs font-medium text-amber-800 text-left max-w-md">
                  <HelpCircle className="w-5 h-5 text-amber-600 shrink-0" />
                  <span>
                    <b>Öneri:</b> E-Okul not giriş ekranının tamamını tarayıcıdan kırpmadan ekran görüntüsü olarak yükleyebilirsiniz. Sistem tabloyu otomatik olarak bulacaktır.
                  </span>
                </div>
              </div>
            ) : activeTab === "academic" ? (
              <AcademicTable students={students} onUpdateStudent={handleUpdateStudent} />
            ) : (
              <GrowthTable students={students} onUpdateStudent={handleUpdateStudent} />
            )}
          </div>

          {/* Right Column: Visual analytics sidebar (visible only on Academic tab) */}
          {activeTab === "academic" && students.length > 0 && (
            <aside className="w-full lg:w-[320px] shrink-0">
              <AnalyticsChart students={students} />
            </aside>
          )}
        </section>

      </main>

      {/* Footer copyright */}
      <footer className="bg-slate-100 border-t border-slate-200 py-4 select-none">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500 font-medium">
          Fizik Dersi Akademik ve Gelişim Değerlendirme Sistemi © 2026. Tamamen Yerel ve Güvenli Veri Saklama.
        </div>
      </footer>

      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
        onSave={handleSaveApiKey}
      />
    </div>
  );
}
