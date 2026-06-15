import React, { useState } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown, AlertCircle } from "lucide-react";
import { ExtractedStudent } from "./types";

interface AcademicTableProps {
  students: ExtractedStudent[];
  onUpdateStudent: (schoolNo: string, updatedFields: Partial<ExtractedStudent>) => void;
}

type SortField = "school_no" | "name" | "exam1" | "exam2" | "perf1" | "perf2" | "calculated_average" | "status";
type SortDirection = "asc" | "desc" | null;

export const AcademicTable: React.FC<AcademicTableProps> = ({ students, onUpdateStudent }) => {
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

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

      // Handle null values in sorting (put them at the end)
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

  const handleGradeChange = (
    schoolNo: string,
    field: "exam1" | "exam2" | "perf1" | "perf2",
    valueStr: string
  ) => {
    const cleanVal = valueStr.trim().toUpperCase();
    
    // G case (Absent)
    if (cleanVal === "G" || cleanVal === "g") {
      onUpdateStudent(schoolNo, { [field]: null });
      return;
    }

    if (cleanVal === "" || cleanVal === "-") {
      onUpdateStudent(schoolNo, { [field]: null });
      return;
    }

    // Convert to number
    const num = parseFloat(cleanVal.replace(",", "."));
    if (isNaN(num) || num < 0 || num > 100) {
      // Keep state as is, validation can be managed locally or reset
      return;
    }

    onUpdateStudent(schoolNo, { [field]: Math.round(num * 100) / 100 });
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ChevronsUpDown className="w-4 h-4 ml-1 opacity-50" />;
    if (sortDirection === "asc") return <ChevronUp className="w-4 h-4 ml-1" />;
    return <ChevronDown className="w-4 h-4 ml-1" />;
  };

  const sortedStudents = getSortedStudents();

  return (
    <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 table-fixed">
        <thead className="bg-[#2b3e50] text-white select-none">
          <tr>
            <th className="w-[60px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider">
              #
            </th>
            <th 
              onClick={() => handleSort("school_no")}
              className="w-[120px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center">Okul No {getSortIcon("school_no")}</div>
            </th>
            <th 
              onClick={() => handleSort("name")}
              className="w-[240px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center">Adı Soyadı {getSortIcon("name")}</div>
            </th>
            <th 
              onClick={() => handleSort("exam1")}
              className="w-[100px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">1. Sınav {getSortIcon("exam1")}</div>
            </th>
            <th 
              onClick={() => handleSort("exam2")}
              className="w-[100px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">2. Sınav {getSortIcon("exam2")}</div>
            </th>
            <th 
              onClick={() => handleSort("perf1")}
              className="w-[100px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">1. Perf {getSortIcon("perf1")}</div>
            </th>
            <th 
              onClick={() => handleSort("perf2")}
              className="w-[100px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">2. Perf {getSortIcon("perf2")}</div>
            </th>
            <th 
              onClick={() => handleSort("calculated_average")}
              className="w-[110px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">Ortalama {getSortIcon("calculated_average")}</div>
            </th>
            <th 
              onClick={() => handleSort("status")}
              className="w-[110px] px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-slate-700 transition"
            >
              <div className="flex items-center justify-center">Durum {getSortIcon("status")}</div>
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-slate-100">
          {sortedStudents.map((student) => {
            const isAbsent = 
              student.exam1 === null || 
              student.exam2 === null || 
              student.perf1 === null || 
              student.perf2 === null;

            return (
              <tr 
                key={student.school_no} 
                className={`hover:bg-slate-50 transition ${student.is_new_student ? "bg-amber-50/40" : ""}`}
              >
                <td className="px-4 py-2.5 text-center text-sm font-medium text-slate-500">
                  {student.row_index}
                </td>
                <td className="px-4 py-2.5 text-sm font-semibold text-slate-700">
                  {student.school_no}
                </td>
                <td className="px-4 py-2.5 text-sm font-medium text-slate-900 truncate">
                  <div className="flex items-center gap-1.5">
                    {student.name}
                    {student.is_new_student && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                        Yeni
                      </span>
                    )}
                  </div>
                </td>
                
                {/* Grades Input Cells */}
                {([
                  { key: "exam1", label: "1. Sınav" },
                  { key: "exam2", label: "2. Sınav" },
                  { key: "perf1", label: "1. Perf" },
                  { key: "perf2", label: "2. Perf" }
                ] as const).map(({ key }) => (
                  <td key={key} className="px-4 py-2 text-center">
                    <input
                      type="text"
                      className="w-16 h-8 text-center text-sm font-medium border border-slate-200 rounded-md bg-slate-50/60 focus:bg-white focus:border-[#1976d2] focus:ring-1 focus:ring-[#1976d2] outline-none transition uppercase"
                      value={student[key] === null ? "" : student[key]}
                      placeholder="G"
                      onChange={(e) => handleGradeChange(student.school_no, key, e.target.value)}
                    />
                  </td>
                ))}

                {/* Average Cell */}
                <td className="px-4 py-2 text-center text-sm font-bold text-slate-800">
                  {student.calculated_average !== null ? student.calculated_average.toFixed(2) : "-"}
                </td>

                {/* Status Badge */}
                <td className="px-4 py-2 text-center">
                  {student.status === "Geçti" && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Geçti
                    </span>
                  )}
                  {student.status === "Kaldı" && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                      Kaldı
                    </span>
                  )}
                  {student.status === "Belirsiz" && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-50 text-slate-600 border border-slate-200">
                      {isAbsent ? (
                        <div className="flex items-center gap-1" title="Eksik not var. Ortalama hesaplanamıyor.">
                          Belirsiz <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                        </div>
                      ) : (
                        "Belirsiz"
                      )}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
