import * as XLSX from "xlsx";

export type SpreadsheetRow = Record<string, string | number | boolean>;

export function sheetRows(workbook: XLSX.WorkBook): SpreadsheetRow[] {
  const sheet = workbook.Sheets[workbook.SheetNames[0] ?? ""];
  if (!sheet) return [];
  return XLSX.utils
    .sheet_to_json<SpreadsheetRow>(sheet, { defval: "" })
    .map((row) =>
      Object.fromEntries(
        Object.entries(row).map(([key, value]) => [key.replace(/^\uFEFF/, ""), value]),
      ),
    );
}

export function csvRows(csv: string): SpreadsheetRow[] {
  return sheetRows(XLSX.read(csv.replace(/^\uFEFF/, ""), { type: "string" }));
}
