import win32com.client as win32
import os
import re
from excel import PyExcel
import time
from datetime import datetime
import holidays
# import pyautogui

INPUT_FOLDER = "INPUT_6"
INPUT_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), INPUT_FOLDER)
OUTPUT_FOLDER = "OUTPUT_6"
OUTPUT_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FOLDER)

MASTER_TABLE_PATH = f"{OUTPUT_FOLDER_PATH}/Hospira evidencije rada 06-2025.xlsm"
# MASTER_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), MASTER_TABLE_FILE)

REPORTS_PATH = f"{OUTPUT_FOLDER_PATH}/Reports.xlsx"

CUMULATIVES_PATH = f"{OUTPUT_FOLDER_PATH}/Hospira satnica.xlsm"
# REPORTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), REPORTS_FILE)
# excel = win32.gencache.EnsureDispatch('Excel.Application')
# excel.Visible = True

OUTPUT_FILE_HEADER_ROW = 2
UNDEFINED_CODE_MESSAGE = "Navedena šifra se ne poklapa sa listom šifri, molim provjeru."
CODES_MAPPING = {'BO': 'BO-AO', 'J+3': 'J-PR3', 'J+4': 'J-PR4', 'J4': 'J-PR4', 'NER': 'DO', 'PR-P8': 'PR-O8', 'U': 'J'}

REL_HOLIDAY_CODE = "rel_hol"
NAT_HOLIDAY_CODE = "nat_hol"
SATURDAY_CODE = "sat"
SUNDAY_CODE = "sun"

CUMULATIVE_STARTING_COL = 4

class Employee:
    
    def __init__(self, row : dict) -> None:
        self.ID = row.get('Employee ID', '')
        self.organization_name = row.get('Organization name', '')
        self.organization_unit = row.get('Organization unit', '')
        self.first_name = row.get('First Name', 'BLA-LA')
        self.last_name = row.get('Surname', '')
        self.monthly_data = row.get('monthly_data', [])
        
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

def batch_rows_insert(start_col : int, end_col : int, data : list[str], ws : any) -> None:
    used_range = ws.UsedRange
    for row, row_details in data:
        data_2d = [row_details]
        target_range = ws.Range(used_range.Cells(row, start_col), used_range.Cells(row, end_col))
        target_range.Value = data_2d
        # print(f"ENTERED: (row, s_col, e_col) : ({row}, {start_col}, {end_col})")
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
    wb = excel_app.openFile(MASTER_TABLE_PATH)
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

    month, year = extract_date_from_name(MASTER_TABLE_PATH)
    for employee in employees_data:
        captured_undefined_codes = []
        row_data, row = find_employee_in_table(id=employee.ID, ws=ws)
        print(f"{row=}")
        # print(f"{row_data=}")
        if row_data:
            month_codes_input = []
            for i in range(starting_col, ending_col + 1):
                cell = used_range.Cells(row, i)
                #i - starting_col because loop starts from starting_col => list items are in range [0, len(list)]
                code = employee.monthly_data[i - starting_col]
                code = code if not code else code.upper().strip()
                if not validation_cache:
                    validation_cache = extract_values_from_validation(validation_formula=cell.Validation.Formula1, wb=wb)
                mapped_code = CODES_MAPPING.get(code, None)
                if code and (code not in validation_cache and mapped_code not in validation_cache):
                    
                    employee.monthly_data[i - starting_col] = None

                    month_codes_input.append(None)
                    # if code not in captured_undefined_codes:
                    captured_undefined_codes.append(code)
                    # + 1 because it is starting from 1, not from 0 (first day in month has value
                    # of 1, not 0) 
                    date = f"{"0" if (i - starting_col + 1) < 10 else ""}{i-starting_col + 1}.{month}.{year}"
                    code_reports.append({"Šifra": code, "Datum": date, "Employee ID": employee.ID, 
                                         "Name": employee.first_name, "Surname": employee.last_name, 
                                         "Organization Name": employee.organization_name, "Organization unit": employee.organization_unit, 
                                         "Komentar": UNDEFINED_CODE_MESSAGE})
                    continue
                employee.monthly_data[i - starting_col] = code if not mapped_code else mapped_code
                month_codes_input.append(code if not mapped_code else mapped_code)
            row_tuple = (row, month_codes_input)
            data.append(row_tuple)
    # for report in code_reports:
    #     print(f"{report=}")
    batch_rows_insert(start_col=starting_col, end_col=ending_col, data=data, ws=ws)
    wb.Save()
    excel_app.closeFile(MASTER_TABLE_PATH)
    print(f"INSERTED {len(employees_data)} elements")
    return code_reports

def fill_reports_table(excel_app : PyExcel, code_reports : list[dict]) -> None:

    wb = excel_app.openFile(REPORTS_PATH)
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
    excel_app.closeFile(REPORTS_PATH)
    return

def extract_date_from_name(file_path : str) -> tuple[str, str]:
    file_name = os.path.basename(file_path)
    l = file_name.split(" ")
    for part in l:
        if ("-") in part:
            date = part.split("-")
            return date[0], date[1].partition(".")[0]
    return


def pack_cumulative_columns(data : list[str]) -> dict[set]:

    replacements = {
        "prekovremeno": "pr",
        "prv": "pr",
        "subota": SATURDAY_CODE,
        "nedjelja": SUNDAY_CODE,
        "blagdan": REL_HOLIDAY_CODE,
        "praznik": NAT_HOLIDAY_CODE,
        "1. smjena": "j",
        "2. smjena": "p",
        "3. smjena": "n",
        "i smjena": "j",
        "ii smjena": "p",
        "iii smjena": "n",
        "jutro" : "j",
        "popodne": "p",
        "redovan rad": "",
        "na": "",
        "noć": "n",
        "očinski": "bo-od",
        "ništa": "n/a"
    }
    result = {}
    for i in range(len(data)):
        pattern = re.compile("|".join(map(re.escape, replacements.keys())))
        """
        Lambda is called once for each match => the function recives match object 'm'
        for example: m = <re.Match object; span=(12, 18), match='subota'>
        So for each match, python will call lambda m: replacements[m.group()]
        m.group(0) returns the exact substring that matched regex => for example 'subota'
        => replacements[m.group(0)] looks up that workd in dictionary and sub replaces the match with 
        whatever lambda returns
        """
        s = pattern.sub(lambda m: replacements[m.group(0)], data[i].lower())
        print(f"DATA[I]: {data[i]} ||||||||| FOR STRING: {s}")
        data[i] = frozenset(set(s.split()))
        result[data[i]] = CUMULATIVE_STARTING_COL + i
    print(f"{result=}")
    return result

def disect_code(code : str) -> tuple[int, frozenset[set]]:
    code_list = []
    number = 0
    try:
        code_list = code.split("-")
    except:
        return (0, frozenset(set([code]))) 
    for i in range(len(code_list)):
        number_split = re.split("(\d+)", code_list[i])
        if len(number_split) > 1:
            code_list.remove(code_list[i])
            i -= 1
            try:
                number = int(number_split[0])
                code_list.append(number_split[1])
            except:
                number = int(number_split[1])
                code_list.append(number_split[0])
    code_set = set(code_list)
    if '' in code_set:
        code_set.remove('')
    return (number, frozenset(code_set))

def fill_cumulative_table(excel_app : any, employees_data : list[Employee]) -> None:
    month, year = extract_date_from_name(MASTER_TABLE_PATH)
    saturdays = []
    sundays = []
    holidays_cro = holidays.country_holidays('HR', years=int(year))
    # print(f'{holidays=}')
    # for i in range(len(employees_data[0].monthly_data)):
    #     date = f'{i + 1} {month} {year}'
    #     dt = datetime.strptime(date, "%d %m %Y")
    #     if (dt.weekday() == 5):
    #             saturdays.append(i)
    #     elif (dt.weekday() == 6):
    #             sundays.append(i)
    
    religious_holidays = {
        "Epiphany",
        "Easter Sunday",
        "Easter Monday",
        "Corpus Christi",
        "Assumption Day",
        "All Saints' Day",
        "Christmas Day",
        "Saint Stephen's Day",
    }

    national_holidays = {
        "New Year's Day",
        "Labor Day",
        "Statehood Day",
        "Anti-Fascist Struggle Day",
        "Victory and Homeland Thanksgiving Day and Croatian Veterans Day",
        "Remembrance Day",
    }

    SHEET_NAME = "Sumarno"
    ACTIVE_ROW = 2
    wb = excel_app.openFile(CUMULATIVES_PATH)
    ws = excel_app.resolveSheet(SHEET_NAME, wb.Name)
    used_range = ws.UsedRange
    columns_count = used_range.Columns.Count

    data = list(ws.Range(used_range.Cells(ACTIVE_ROW, CUMULATIVE_STARTING_COL), used_range.Cells(ACTIVE_ROW, columns_count)).Value2[0])
    packed_column_header_codes = pack_cumulative_columns(data)
    
    day_data = None
    row = -1
    col = -1

    # employee_cumulatives = [None] * len(packed_column_header_codes)
    employee_cumulatives = [0] * len(packed_column_header_codes)
    insertion_data = []

    for e in employees_data:
        row = - 1
        found_cell = used_range.Find(What=e.ID)
        if found_cell:
            row = found_cell.Row
        if row == -1:
            print(f"Unable to enter cumulatives for employee: {e.ID} - person not in table")
            continue
        for i in range(len(e.monthly_data)):
            day_data = "n/a" if not e.monthly_data[i] else e.monthly_data[i].lower()
            #doesn't matter if these days are made on holiday or sometime else
            if day_data == "n/a" or 'go' in day_data or 'bo' in day_data:
                #mapping to [0, len(dict)-1] range
                col = packed_column_header_codes[frozenset(set([day_data]))] - CUMULATIVE_STARTING_COL
                # employee_cumulatives[col] = 8 if not employee_cumulatives[col] else employee_cumulatives[col] + 8 
                if col >= len(e.monthly_data):
                    print(f"index of {frozenset(set([day_data]))} is: {col}")
                employee_cumulatives[col] += 8 
                continue
            date = f'{i + 1} {month} {year}'
            dt = datetime.strptime(date, "%d %m %Y")
            if i in saturdays:
                day_data += f"-{SATURDAY_CODE}"
            elif i in sundays:
                day_data += f"-{SUNDAY_CODE}"
            
            holiday = holidays_cro.get(dt.date(), '')
            if holiday in religious_holidays:
                day_data += f"-{REL_HOLIDAY_CODE}"
            elif holiday in national_holidays:
                day_data += f"-{NAT_HOLIDAY_CODE}"
            overtime_hours, hashed_set = disect_code(day_data)
            col = packed_column_header_codes[hashed_set] - CUMULATIVE_STARTING_COL
            employee_cumulatives[col] += (overtime_hours + 8)
        
        insertion_data.append((row, employee_cumulatives))
        # print(f"MODIFIED MONTH REPORT: {e.monthly_data}")
    batch_rows_insert(start_col=CUMULATIVE_STARTING_COL, end_col=columns_count, data=insertion_data, ws=ws)
    wb.Save()
    excel_app.closeFile(CUMULATIVES_PATH)
    print(f"INSERTED cumulatives")
    return

def main():

    os.chdir('/')
    os.chdir(INPUT_FOLDER_PATH)
    files = os.listdir()
    print(f"{files=}")

    excel_app = PyExcel()
    # wb = excel_app.openFile(f"{INPUT_FOLDER_PATH}/{files[0]}")
    # ws = excel_app.resolveSheet('EVIDENCIJE', wb.Name)
    
    # used_range = ws.UsedRange
    # row_count = used_range.Rows.Count
    # col_count = used_range.Columns.Count

    # employees = []
    
    # categories = {}
    # for i in range(1, col_count + 1):
    #     categories[i] = used_range.Cells(1, i).Value

    # excel_app.closeFile(f"{INPUT_FOLDER_PATH}/{files[0]}")

    
    # for file in files:
    #     file_path = f"{INPUT_FOLDER_PATH}/{file}"
    #     wb = excel_app.openFile(file_path=file_path)
    #     ws = excel_app.resolveSheet('EVIDENCIJE', wb.Name)

    #     used_range = ws.UsedRange
    #     row_count = used_range.Rows.Count
    #     col_count = used_range.Columns.Count

    #     for i in range(2, row_count + 1):
    #         row_values = {}
    #         monthly_data = []

    #         if row_empty(row=i, col_cnt=col_count, ws=ws):
    #             break

    #         for j in range(1, col_count + 1):
    #             try:
    #                 int(categories.get(j))
    #                 monthly_data.append(used_range.Cells(i, j).Value)
    #             except:
    #                 row_values[categories.get(j)] = used_range.Cells(i, j).Value
    #         row_values['monthly_data'] = monthly_data
    #         employees.append(Employee(row=row_values))
    #     excel_app.closeFile(file_path=file_path)
    # # for employee in employees:
    # #     print(f"{employee.ID=}")
    # # excel_app.closeFile(EXCEL_INPUT_PATH)
    # print("Sucessfully read all input")
    # start_time = time.perf_counter()
    # code_reports = fill_master_table(excel_app=excel_app, employees_data=employees)
    # end_time = time.perf_counter()

    # print(f"Insert lasted: {end_time - start_time}s")

    # fill_reports_table(excel_app, code_reports)

    # fill_cumulative_table(excel_app, employees)
    fill_cumulative_table(excel_app, [])

    excel_app.quit()
    return

if __name__ == "__main__":
    main()
