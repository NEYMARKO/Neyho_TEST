import win32com.client as win32
import os
from excel import PyExcel
import time
# import pyautogui

EXCEL_INPUT_FILE = "DS_06_2025_168_BB.xlsx"
EXCEL_INPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXCEL_INPUT_FILE)
EXCEL_OUTPUT_FILE = "Hospira evidencije rada 06-2025.xlsm"
EXCEL_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXCEL_OUTPUT_FILE)
EXCEL_REPORTS_FILE = "Reports.xlsx"
EXCEL_REPORTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXCEL_REPORTS_FILE)
# excel = win32.gencache.EnsureDispatch('Excel.Application')
# excel.Visible = True

OUTPUT_FILE_HEADER_ROW = 2
UNDEFINED_CODE_MESSAGE = "Navedena šifra se ne poklapa sa listom šifri, molim provjeru."
class Employee:
    
    def __init__(self, row : dict) -> None:
        self.ID = row.get('Employee ID', '')
        self.organization_unit = row.get('Organization unit', '')
        self.first_name = row.get('First name', '')
        self.last_name = row.get('Surname', '')
        self.monthly_data = row.get('monthly_data', '')
    
    def struct_data(self) -> list[str]:
        return [self.ID, self.organization_unit, self.first_name, self.last_name, self.monthly_data]

    def get_full_name(self) -> str:
        return self.first_name + self.last_name
    
    def gather_report_info(self) -> dict:
        return {"Employee ID": self.ID, "Organization Name": self.organization_unit}
    
    def print_data(self) -> None:
        structured_data = self.struct_data()
        for value in structured_data:
            print(f"{value} ", end='')
        print()
        return
    

def row_empty(row : int, col_cnt : int, ws : any) -> bool:
    """
    Checks whether all values in row are None
    """
    for i in range(1, col_cnt + 1):
        if ws.Cells(row, i).Value is not None:
            return False
    return True

def extract_values_from_validation(validation_formula : any, wb : any) -> list[str]:
    try:
        allowed_values = []
        if validation_formula.startswith("="):
            validation_formula = validation_formula[1:]
            sheet_name, adress_range = validation_formula.split("!")
            sheet_name = sheet_name.strip("'")
            ref_ws = wb.Sheets(sheet_name)
            ref_range = ref_ws.Range(adress_range)
            values_2d = ref_range.Value
            for row in values_2d:
                for value in row:
                    if value:
                        allowed_values.append(value)
        else:
            allowed_values = [v.strip() for v in validation_formula.split(",")]
        
        return allowed_values
    
    except:
        print("No validation available")

def batch_row_insert(row : int, start_col : int, end_col : int, data : list[str], ws : any) -> None:
    used_range = ws.UsedRange
    for row, row_details in data:
        data_2d = [row_details]
        target_range = ws.Range(used_range.Cells(row, start_col), used_range.Cells(row, end_col))
        target_range.Value = data_2d

    return

def find_employee_in_table(id : str, ws : any) -> tuple[list[str], int]:
    """
    Returns row's content and index for employee that matches parameter id.
    """
    used_range = ws.UsedRange
    found_cell = used_range.Find(What=id)
    if found_cell:
        row = found_cell.Row
        col_cnt = used_range.Columns.Count
        return ([used_range.Cells(row, col).Value for col in range(1, col_cnt + 1)], row)
    return ([], -1)

def fill_master_table(excel_app : any, employees_data : list[Employee]) -> list[dict]:
    """
    Fills master table and returns code reports as result.
    """
    wb = excel_app.openFile(EXCEL_OUTPUT_PATH)
    ws = excel_app.resolveSheet("Evidencija", wb.Name)
    used_range = ws.UsedRange
    columns_count = ws.UsedRange.Columns.Count

    starting_col = -1
    ending_col = -1
    for i in range(1, columns_count + 1):
        try:
            int(ws.Cells(OUTPUT_FILE_HEADER_ROW, i).Value)
            if starting_col == -1:
                starting_col = i
        except:
            if starting_col != -1:
                ending_col = i - 1
                break
    
    data = []
    print("Should remove or update cashe if there are more than 1 formulas")
    validation_cache = []
    code_reports = []

    month, year = extract_date_from_name(EXCEL_OUTPUT_FILE)
    for employee in employees_data:
        captured_undefined_codes = []
        row_data, row = find_employee_in_table(id=employee.ID, ws=ws)
        print(f"{row=}")
        if row_data:
            month_codes_input = []
            for i in range(starting_col, ending_col + 1):
                cell = used_range.Cells(row, i)
                #i - starting_col because loop starts from starting_col => list items are in range [0, len(list)]
                code = employee.monthly_data[i - starting_col]
                if not validation_cache:
                    validation_cache = extract_values_from_validation(validation_formula=cell.Validation.Formula1, wb=wb)
                if code and code not in validation_cache:
                    month_codes_input.append(None)
                    if code not in captured_undefined_codes:
                        captured_undefined_codes.append(code)
                        date = f"{"0" if (i - starting_col) < 10 else ""}{i-starting_col}.{month}.{year}"
                        code_reports.append({"Šifra": code, "Datum": date, "Employee ID": employee.ID, "Organization Name": employee.organization_unit, "Komentar": UNDEFINED_CODE_MESSAGE})
                    continue
                month_codes_input.append(code)
        row_tuple = (row, month_codes_input)
        data.append(row_tuple)
    for report in code_reports:
        print(f"{report=}")
    batch_row_insert(row=row, start_col=starting_col, end_col=ending_col, data=data, ws=ws)
    wb.Save()
    excel_app.closeFile(EXCEL_OUTPUT_PATH)
    return code_reports

def fill_reports_table(excel_app : PyExcel, code_reports : list[dict]) -> None:

    wb = excel_app.openFile(EXCEL_REPORTS_PATH)
    print("ALIGN SHEET NAME TO MATCH SHEET NAME FROM FILE")
    ws = excel_app.resolveSheet("Sheet1", wb.Name)
    used_range = ws.UsedRange
    columns_count = used_range.Columns.Count

    row = 2
    for report in code_reports:
        # print(list(report.values()))
        data_2d = [list(report.values())]
        target_range = ws.Range(used_range.Cells(row, 1), used_range(row, columns_count))
        row += 1
        target_range.Value = data_2d
    wb.Save()
    excel_app.closeFile(EXCEL_REPORTS_PATH)
    return

def extract_date_from_name(file_name : str) -> tuple[str, str]:
    l = file_name.split(" ")
    for part in l:
        if ("-") in part:
            date = part.split("-")
            return date[0], date[1].partition(".")[0]
    return

def main():

    excel_app = PyExcel()
    wb = excel_app.openFile(EXCEL_INPUT_PATH)
    ws = excel_app.resolveSheet('EVIDENCIJE', wb.Name)
    
    used_range = ws.UsedRange
    row_count = used_range.Rows.Count
    col_count = used_range.Columns.Count

    employees = []
    
    categories = {}
    for i in range(1, col_count + 1):
        categories[i] = used_range.Cells(1, i).Value

    for i in range(2, row_count + 1):
        row_values = {}
        monthly_data = []

        if row_empty(row=i, col_cnt=col_count, ws=ws):
            break

        for j in range(1, col_count + 1):
            try:
                int(categories.get(j))
                monthly_data.append(used_range.Cells(i, j).Value)
            except:
                row_values[categories.get(j)] = used_range.Cells(i, j).Value
        row_values['monthly_data'] = monthly_data
        employees.append(Employee(row=row_values))

    # for employee in employees:
    #     print(f"{employee.ID=}")
    excel_app.closeFile(EXCEL_INPUT_PATH)

    start_time = time.perf_counter()
    code_reports = fill_master_table(excel_app=excel_app, employees_data=employees)
    end_time = time.perf_counter()

    print(f"Insert lasted: {end_time - start_time}s")

    fill_reports_table(excel_app, code_reports)

    excel_app.quit()
    return

if __name__ == "__main__":
    main()
