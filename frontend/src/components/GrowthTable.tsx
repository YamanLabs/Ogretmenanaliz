import React, { useState } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown, AlertTriangle } from "lucide-react";
import { ExtractedStudent } from "./types";

interface GrowthTableProps {
  students: ExtractedStudent[];
  onUpdateStudent: (schoolNo: string, updatedFields: Partial<ExtractedStudent>) => void;
}

type SortField = 
  | "school_no" 
  | "name" 
  | "growth_attendance" 
  | "growth_activities" 
  | "growth_product" 
  | "growth_social_emotional" 
  | "growth_progress";

type SortDirection = "asc" | "desc" | null;

export const GrowthTable: React.FC<GrowthTableProps> = ({ students, onUpdateStudent }) => {
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  
  // Track validation errors locally (key: schoolNo_field, value: error message)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortField(null);
        setSortDirection(null);
      } else {
        setSortDirection("asc");
      }
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const getSortedStudents = () => {
    if (!sortField || !sortDirection) return students;

    return [...students].sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];

      // Handle null values in sorting
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      // Special numeric sorting for school numbers
      if (sortField === "school_no") {
        return sortDirection === "asc" 
          ? Number(valA) - Number(valB)
          : Number(valB) - Number(valA);
      }

      if (typeof valA === "string") {
        return sortDirection === "asc" 
          ? valA.localeCompare(String(valB), "tr")
          : String(valB).localeCompare(valA, "tr");
      }

      return sortDirection === "asc"
        ? Number(valA) - Number(valB)
        : Number(valB) - Number(valA);
    });
  };

  const handleScoreChange = (
    schoolNo: string,
    field: "growth_attendance" | "growth_activities" | "growth_product" | "growth_social_emotional" | "growth_progress",
    rawVal: string
  ) => {
    const errorKey = `${schoolNo}_${field}`;

    if (rawVal.trim() === "") {
      // Clear errors for this cell
      const newErrors = { ...validationErrors };
      delete newErrors[errorKey];
      setValidationErrors(newErrors);
      
      onUpdateStudent(schoolNo, { [field]: null });
      return;
    }

    const num = parseFloat(rawVal.replace(",", "."));
    
    // Check if valid number
    if (isNaN(num)) {
      setValidationErrors(prev => ({ ...prev, [errorKey]: "Geçersiz Sayı" }));
      return;
    }

    // Check bounds 0-100
    if (num < 0 || num > 100) {
      setValidationErrors(prev => ({ ...prev, [errorKey]: "Not 0 - 100 arasında olmalıdır!" }));
      return;
    }

    // Clear error if valid
    const newErrors = { ...validationErrors };
    delete newErrors[errorKey];
    setValidationErrors(newErrors);

    onUpdateStudent(schoolNo, { [field]: Math.round(num * 100) / 100 });
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ChevronsUpDown className="w-4 h-4 ml-1 opacity-50" />;
    if (sortDirection === "asc") return <ChevronUp className="w-4 h-4 ml-1" />;
    return <ChevronDown className="w-4 h-4 ml-1" />;
  };

  const sortedStudents = getSortedStudents();

  // Check if there are any active validation errors in the table
  const hasErrors = Object.keys(validationErrors).length > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Dynamic Validation Warning Bar */}
      {hasErrors && (
        <div className="flex items-center gap-2 p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-lg text-sm font-medium animate-pulse shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>
            Hata! Arayüzde geçersiz gelişim notları tespit edildi. Notlar 0 ile 100 arasında bir değer olmalıdır. Lütfen kırmızı çerçeveli hücreleri düzeltin.
          </span>
        </div>
      )}

      <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 table-fixed">
          <thead className="bg-[#2b3e50] text-white select-none">
            <tr>
              <th className="w-[60px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider">
                #
              </th>
              <th 
                onClick={() => handleSort("school_no")}
                className="w-[110px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center">Okul No {getSortIcon("school_no")}</div>
              </th>
              <th 
                onClick={() => handleSort("name")}
                className="w-[200px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center">Adı Soyadı {getSortIcon("name")}</div>
              </th>
              <th 
                onClick={() => handleSort("growth_attendance")}
                className="w-[140px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center justify-center text-center">Ders Katılım {getSortIcon("growth_attendance")}</div>
              </th>
              <th 
                onClick={() => handleSort("growth_activities")}
                className="w-[140px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center justify-center text-center">Sınıf Dışı Faal. {getSortIcon("growth_activities")}</div>
              </th>
              <th 
                onClick={() => handleSort("growth_product")}
                className="w-[140px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center justify-center text-center">Ürün Değer. {getSortIcon("growth_product")}</div>
              </th>
              <th 
                onClick={() => handleSort("growth_social_emotional")}
                className="w-[140px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center justify-center text-center">Sosyal Duygusal {getSortIcon("growth_social_emotional")}</div>
              </th>
              <th 
                onClick={() => handleSort("growth_progress")}
                className="w-[140px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
              >
                <div className="flex items-center justify-center text-center">Öğrenci Gelişimi {getSortIcon("growth_progress")}</div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {sortedStudents.map((student) => {
              return (
                <tr 
                  key={student.school_no} 
                  className="hover:bg-slate-50 transition"
                >
                  <td className="px-4 py-2.5 text-center text-sm font-medium text-slate-500">
                    {student.row_index}
                  </td>
                  <td className="px-4 py-2.5 text-sm font-semibold text-slate-700">
                    {student.school_no}
                  </td>
                  <td className="px-4 py-2.5 text-sm font-medium text-slate-900 truncate">
                    {student.name}
                  </td>
                  
                  {/* Growth Score Inputs */}
                  {([
                    { key: "growth_attendance", label: "Ders Katılım" },
                    { key: "growth_activities", label: "Sınıf Dışı" },
                    { key: "growth_product", label: "Ürün Değer." },
                    { key: "growth_social_emotional", label: "Sosyal Duygusal" },
                    { key: "growth_progress", label: "Gelişim" }
                  ] as const).map(({ key }) => {
                    const errorKey = `${student.school_no}_${key}`;
                    const errorMsg = validationErrors[errorKey];
                    const val = student[key];

                    return (
                      <td key={key} className="px-4 py-2 text-center relative">
                        <input
                          type="text"
                          className={`w-16 h-8 text-center text-sm font-medium border rounded-md outline-none transition ${
                            errorMsg 
                              ? "bg-rose-50 border-rose-500 text-rose-900 focus:ring-1 focus:ring-rose-500" 
                              : "bg-slate-50/60 border-slate-200 focus:bg-white focus:border-[#1976d2] focus:ring-1 focus:ring-[#1976d2]"
                          }`}
                          value={val === null ? "" : val}
                          onChange={(e) => handleScoreChange(student.school_no, key, e.target.value)}
                          title={errorMsg || `${student.name} - ${key}`}
                        />
                        {errorMsg && (
                          <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 px-1 py-0.5 bg-rose-600 text-white text-[9px] rounded font-bold whitespace-nowrap shadow-md select-none z-10">
                            {errorMsg}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
