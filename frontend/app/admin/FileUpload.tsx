"use client";
import React, { useState } from "react";
import { FileUpload } from "@/components/ui/file-upload";
import Papa from "papaparse"; // install papaparse: npm install papaparse

export function FileUploadDemo() {
  const [csvData, setCsvData] = useState<any[]>([]);
  const [headers, setHeaders] = useState<string[]>([]);

  const handleFileUpload = (files: File[]) => {
    if (files.length > 0) {
      const file = files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        Papa.parse(text, {
          header: true,
          skipEmptyLines: true,
          complete: (results: any) => {
            setHeaders(results.meta.fields || []);
            setCsvData(results.data as any[]);
          },
        });
      };
      reader.readAsText(file);
    }
  };

  const handleCellChange = (rowIndex: number, key: string, value: string) => {
    const newData = [...csvData];
    newData[rowIndex][key] = value;
    setCsvData(newData);
    console.log("Updated JSON:", newData);
  };

  return (
    <div className="w-full max-w-4xl mx-auto min-h-96 border border-dashed bg-gray-400 dark:bg-black border-neutral-200 dark:border-neutral-800 rounded-lg">
        
      <FileUpload onChange={handleFileUpload} />

      {csvData.length > 0 && (
        <div className="overflow-x-auto mt-6">
          <table className="w-full table-auto border-collapse">
            <thead>
              <tr>
                {headers.map((header) => (
                  <th key={header} className="border px-4 py-2 text-left">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {csvData.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {headers.map((header) => (
                    <td key={header} className="border px-4 py-2">
                      <input
                        className="bg-transparent border-none outline-none text-white w-full"
                        value={row[header]}
                        onChange={(e) =>
                          handleCellChange(rowIndex, header, e.target.value)
                        }
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
