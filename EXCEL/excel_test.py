import win32com.client as win32
import os
import re
from excel import PyExcel
import time
from datetime import datetime
import holidays
from enum import Enum
# import pyautogui

INPUT_FOLDER = "INPUT_6_MASTER"
INPUT_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), INPUT_FOLDER)
OUTPUT_FOLDER = "OUTPUT_6"
OUTPUT_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FOLDER)

MASTER_TABLE_PATH = f"{OUTPUT_FOLDER_PATH}/Hospira evidencije rada 06-2025.xlsm"
# MASTER_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), MASTER_TABLE_FILE)

REPORTS_PATH = f"{OUTPUT_FOLDER_PATH}/Reports.xlsx"
REPORTS_HEADERS = ["Code", "Date", "Employee ID", "Name", "Surname", "Organization Name", "Organization unit", "Comment"]
CUMULATIVES_PATH = f"{OUTPUT_FOLDER_PATH}/Hospira satnica - MARKO.xlsm"
# REPORTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), REPORTS_FILE)
# excel = win32.gencache.EnsureDispatch('Excel.Application')
# excel.Visible = True

OUTPUT_FILE_HEADER_ROW = 2
UNDEFINED_CODE_MESSAGE = "Navedena šifra se ne poklapa sa listom šifri, molim provjeru."
USER_NOT_FOUND_MESSAGE = "Nisam uspio pronaći zaposlenika"
CODES_MAPPING = {'BO': 'BO-AO', 'J+3': 'J-PR3', 'J+4': 'J-PR4', 'J4': 'J-PR4', 'NER': 'DO', 'PR-P8': 'PR-O8', 'U': 'J'}

#used for 'BLAGDAN'
HOLIDAY_CODE = "hol"
#used for 'PRAZNIK'
HOLIDAY_OFF_CODE = "hol_off"
SATURDAY_CODE = "sat"
SUNDAY_CODE = "sun"

"""Starts from 'GREŠKA' column - nothing before that can be overriden (everything must be perserved)"""
CUMULATIVE_STARTING_COL = 8
OVERTIME_OVERFLOW = 24

class Day(Enum):
    FRIDAY = 1
    SATURDAY = 2
    SUNDAY = 3

class Employee:
    
    def __init__(self, row : dict) -> None:
        self.ID = row.get('Employee ID', '')
        self.organization_name = row.get('Organization name', '')
        self.organization_unit = row.get('Organization unit', '')
        self.first_name = row.get('First Name', '')
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

def find_employee_in_table(id : str, name : str, surname : str, ws : any) -> tuple[list[str], int]:
    """
    Function searches for row in which wanted employee is mentioned.

    Looks for emplyoee using his ID. If ID isn't provided, function uses employee's 
    first and last name in search.

    Parameters
    - id: employee's id
    - name: employee's first name
    - surname: employee's last name

    Returns
    - tuple with row's content and row index of row that matches search parameters
    - empty list for content and -1 for row index if user hasn't been found
    """
    used_range = ws.UsedRange
    row = -1
    if id:
        found_cell = used_range.Find(What=id)
        if found_cell:
            row = found_cell.Row
        else:
            return ([], -1)
    else:
        first_surname_cell = used_range.Find(What=surname)
        if not first_surname_cell:
            return ([], -1)
        next_cell = used_range.FindNext(first_surname_cell)
        while next_cell and next_cell.Address != first_surname_cell.Address:
            row = next_cell.Row
            row_range = ws.Rows(row)
            name_cell = row_range.Find(What=name)
            if name_cell:
                col_cnt = used_range.Columns.Count
                return ([used_range.Cells(row, col).Value for col in range(1, col_cnt + 1)], row)
            next_cell = used_range.FindNext(next_cell)
        return ([], -1)
    if row != -1:
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
        row_data, row = find_employee_in_table(id=employee.ID, name=employee.first_name, surname=employee.last_name, ws=ws)
        print(f"{row=}")
        # print(f"employee id: {employee.ID}")
        # print(f"{row_data=}")
        # print(f"{employee.last_name=}")
        if row_data:
            month_codes_input = []
            for i in range(starting_col, ending_col + 1):
                cell = used_range.Cells(row, i)
                # print(f"CELL: {cell.Address}")
                #i - starting_col because loop starts from starting_col => list items are in range [0, len(list)]
                # print(f"EMPLOYEE DATA: {employee.monthly_data}")
                # print(f"I: {i}, STARTING COL: {starting_col}")
                code = employee.monthly_data[i - starting_col]
                code = code if not code else "".join(code.upper().split())
                if not validation_cache:
                    # validation_formula = None
                    # try:
                    #     validation_formula = cell.Validation.Formula1
                    #     validation_cache = extract_values_from_validation(validation_formula=validation_formula, wb=wb)
                    # except:
                    #     validation_cache = None
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
                    code_reports.append({"Code": code, "Date": date, "Employee ID": employee.ID, 
                                         "Name": employee.first_name, "Surname": employee.last_name, 
                                         "Organization Name": employee.organization_name, "Organization unit": employee.organization_unit, 
                                         "Comment": UNDEFINED_CODE_MESSAGE})
                    continue
                employee.monthly_data[i - starting_col] = code if not mapped_code else mapped_code
                month_codes_input.append(code if not mapped_code else mapped_code)
            row_tuple = (row, month_codes_input)
            data.append(row_tuple)
        else:
            code_reports.append({"Code": "/", "Date": "/", "Employee ID": employee.ID, 
                                         "Name": employee.first_name, "Surname": employee.last_name, 
                                         "Organization Name": employee.organization_name, "Organization unit": employee.organization_unit, 
                                         "Comment": USER_NOT_FOUND_MESSAGE})
    # for report in code_reports:
    #     print(f"{report=}")
    batch_rows_insert(start_col=starting_col, end_col=ending_col, data=data, ws=ws)
    wb.Save()
    excel_app.closeFile(MASTER_TABLE_PATH)
    print(f"INSERTED {len(data)}/{len(employees_data)} total elements")
    return code_reports

def create_reports_table(excel_app : PyExcel) -> any:
    """
    Creates file if it doesn't exists, otherwise opens file with specified reports path
    defined in REPORTS_PATH global value. If file was sucessfully opened, it is populated
    with headers
    """
    print("---------------------------------OPENING REPORTS TABLE---------------------------------")
    wb = excel_app.openFile(REPORTS_PATH)
    if not wb:
        try:
            print("---------------------------------CREATING REPORTS TABLE---------------------------------")
            excel_app.createFile(REPORTS_PATH)
        except:
            print(f"Having trouble creating {REPORTS_PATH} file")
            return None
    #already able to open wb => no need for populating it with headers
    else:
        return wb
    
    #try to open after creating - fill with categories and save
    wb = excel_app.openFile(REPORTS_PATH)
    if not wb:
        return None
    ws = excel_app.resolveSheet("Sheet1", wb.Name)
    used_range = ws.UsedRange

    target_range = ws.Range(used_range.Cells(1, 1), used_range.Cells(1, len(REPORTS_HEADERS)))
    target_range.Value = REPORTS_HEADERS

    wb.Save()
    return wb
   
    
def fill_reports_table(excel_app : PyExcel, code_reports : list[dict]) -> None:
    wb = create_reports_table(excel_app)
    if not wb:
        return None
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


def pack_cumulative_columns(data : list[str]) -> dict[frozenset[set]]:
    """
    Replaces key words with appropriate codes (for example: "jutro" is mapped to "j").
    Values used for mapping are read from file that containts cumulatives.

    Returns
    - dictionary with frozenset (hashable sets) as keys (mapped codes) and column index as value
    """

    replacements = {
        "prekovremeno": "pr",
        "prv": "pr",
        "subota": SATURDAY_CODE,
        "nedjelja": SUNDAY_CODE,
        "blagdan": HOLIDAY_CODE,
        "praznik": HOLIDAY_OFF_CODE,
        "jutro" : "j",
        "popodne": "p",
        "noć": "n",
        "preko 8 sati": "o",
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
        # s = pattern.sub(lambda m: replacements[m.group(0)], data[i].lower())
        data[i] = pattern.sub(lambda m: replacements[m.group(0)], data[i].lower())
        # print(f"DATA[I]: {data[i]} ||||||||| FOR STRING: {s}")
        # data[i] = frozenset(set(s.split()))
        data[i] = frozenset(set(data[i].split()))
        result[data[i]] = CUMULATIVE_STARTING_COL + i
    print(f"{result=}")
    return result

def disect_code(code : str) -> tuple[int, set[str]]:
    code_list = []
    number = 0
    just_overtime = False
    try:
        code_list = code.split("-")
    except:
        return (0, set([code])) 
    
    try:
        just_overtime = (code_list.index("pr") == 0)
    except:
        #'pr' is not in list (might have 'pr1' which will trigger error - needs to be only 'pr)
        just_overtime = False

    for i in range(len(code_list)):
        # print("THISE USED TO BE '(\d+)' - NOT RAW")
        number_split = re.split(r"(\d+)", code_list[i])
        if len(number_split) > 1:
            code_list.remove(code_list[i])
            i -= 1
            try:
                # number = int(number_split[0]) if (code_list.index("pr") == 0) else int(number_split[0]) + OVERTIME_OVERFLOW
                number = int(number_split[0]) if just_overtime else int(number_split[0]) + OVERTIME_OVERFLOW
                code_list.append(number_split[1])
            except:
                number = int(number_split[1]) if just_overtime else int(number_split[1]) + OVERTIME_OVERFLOW
                code_list.append(number_split[0])
    code_set = set(code_list)
    if '' in code_set:
        code_set.remove('')
    return (number, code_set)

def is_special_code_case(code : str) -> bool:
    return "do" in code or "go" in code or "pd" in code or "bo" in code

#there isn't a case where person is doing both overtime and base time night shift
#==============>hardcoded 2 and 6 hours
def handle_night_shift_overflow(day : int, employee_cumulatives : list, day_of_shift : Day, code_set : set, column_header_codes : dict, transferable_hol=False) -> None:
    """
    In case person worked night shift on friday/saturday/sunday, 2 hours should get written that day, and other 6 in the next day.
    """
    
    #if day_of shift is monday - thursday, this logic will still work because
    #none of the codes will get removed and 6 hours will get added to the same 
    #code combination (same day)
    col = column_header_codes[frozenset(code_set)] - CUMULATIVE_STARTING_COL
    employee_cumulatives[col] += 2

    if day_of_shift == Day.FRIDAY:
        code_set.add(SATURDAY_CODE)
    #if it is last day of month, 6 hours will get added to either day in the weekend - i decided it will be sunday
    elif day_of_shift == Day.SATURDAY or day == len(employee_cumulatives) - 1:
        code_set.remove(SATURDAY_CODE)
        code_set.add(SUNDAY_CODE)
    elif day_of_shift == Day.SUNDAY:
        code_set.remove(SUNDAY_CODE)

    #day_of_shift != None means that it is either Friday, Saturday, Sunday
    #or last day in month => hours should get transfered to next day
        #2 HOURS HAVE ALREADY BEEN ADDED TO CURRENT DAY - at the top of the function
        #NOW WE HAVE TO MODIFY CODES FOR NEXT DAY (TOMMOROW) TO KNOW WHERE SHOULD
        #REMAINING 6 HOURS GET ADDED
    if day_of_shift != None:

        #today is holiday, tommorw it isn't => remove HOLIDAY_CODE from code_set 
        #(weekends have already been removed/added)
        if HOLIDAY_CODE in code_set and not transferable_hol:
            code_set.remove(HOLIDAY_CODE)
        #today isn't holiday, but it is tommorow => add HOLIDAY_CODE to code_set
        elif HOLIDAY_CODE not in code_set and transferable_hol:
            code_set.add(HOLIDAY_CODE)
    print(f"ADDED TO {code_set}")
    col = column_header_codes[frozenset(code_set)] - CUMULATIVE_STARTING_COL
    employee_cumulatives[col] += 6

def fill_cumulative_table(excel_app : any, employees_data : list[Employee]) -> None:
    month, year = extract_date_from_name(MASTER_TABLE_PATH)
    fridays = set()
    saturdays = set()
    sundays = set()
    holidays_cro = holidays.country_holidays('HR', years=int(year))
    # print(f'{holidays=}')
    for i in range(len(employees_data[0].monthly_data)):
        date = f'{i + 1} {month} {year}'
        dt = datetime.strptime(date, "%d %m %Y")
        if (dt.weekday() == 4):
            fridays.add(i)
        elif (dt.weekday() == 5):
            saturdays.add(i)
        elif (dt.weekday() == 6):
            sundays.add(i)

    SHEET_NAME = "Sumarno"
    ACTIVE_ROW = 2

    print(f"{CUMULATIVES_PATH=}")
    wb = excel_app.openFile(CUMULATIVES_PATH)
    ws = excel_app.resolveSheet(SHEET_NAME, wb.Name)
    used_range = ws.UsedRange
    columns_count = used_range.Columns.Count

    data = list(ws.Range(used_range.Cells(ACTIVE_ROW, CUMULATIVE_STARTING_COL), used_range.Cells(ACTIVE_ROW, columns_count)).Value2[0])
    # print(f"{data=}")
    packed_column_header_codes = pack_cumulative_columns(data)
    
    day_data = ""
    row = -1
    col = -1
    
    insertion_data = []

    for e in employees_data:
        employee_cumulatives = [0] * len(packed_column_header_codes)
        row = - 1
        found_cell = used_range.Find(What=e.ID)
        if found_cell:
            row = found_cell.Row
        if row == -1:
            print(f"Unable to enter cumulatives for employee: {e.ID} - person not in table")
            continue
        for i in range(len(e.monthly_data)):
            day_data = "" if (e.monthly_data[i] == 0 or e.monthly_data[i] == 0.0 or not e.monthly_data[i]) else e.monthly_data[i]
            day_data = day_data.lower() if day_data else day_data
            # print(f"{day_data=}")
            #doesn't matter if these days are made on holiday or sometime else
            if day_data and is_special_code_case(day_data):
                #mapping to [0, len(dict)-1] range
                col = packed_column_header_codes[frozenset(set([day_data]))] - CUMULATIVE_STARTING_COL
                employee_cumulatives[col] += 8 
                continue      
            
            # day_data = "n/a" if (not e.monthly_data[i] or e.monthly_data[i] == 0) else e.monthly_data[i].lower()
            
            """
            If employee didn't work on HOLIDAY, write 8h under 'Praznik' column
            otherwise append holiday code and proceed like with any other code
            (it will get written under columns that contain 'blagdan' in their name)
            """

            date_str = f'{i + 1} {month} {year}'
            dt = datetime.strptime(date_str, "%d %m %Y")
            holiday = holidays_cro.get(dt.date(), '')
            #persoh didn't work on holiday => write in praznik - if holiday was on weekend
            #and person didn't work that day, don't write anything
            if holiday and not day_data and not (i in saturdays or i in sundays):
                day_data_set = {HOLIDAY_OFF_CODE}
                col = packed_column_header_codes[frozenset(day_data_set)] - CUMULATIVE_STARTING_COL
                employee_cumulatives[col] += 8
                continue
            #has worked on holiday
            elif holiday and day_data:
                day_data += f"-{HOLIDAY_CODE}"
            
            #if day_data is still empty, that means person didn't work that day and holiday
            #doesn't fall on that day (NOTICE THAT everything (every code) gets appended to day_data)
            #=> if day_data is empty up until this point, person didn't work and holiday wasn't that day)
            if not day_data:
                continue
            
            #now it makes sense to check whether it was weekend because person actually worked
            #that day
            if i in saturdays and day_data:
                day_data += f"-{SATURDAY_CODE}"
            elif i in sundays and day_data:
                day_data += f"-{SUNDAY_CODE}"

            working_hours, code_set = disect_code(day_data)
            # print(f"{overtime_hours=}")
            # print(f"employee {e.ID} at day: {i+1}")
            """Employee has worked overtime + base time"""
            if (working_hours > OVERTIME_OVERFLOW):
                #OVERTIME_OVERFLOW has been set to 24 => no person can work 24 extra
                #hours in a day - it is distinct between cases where person worked
                #just overtime vs when person worked base + overtime - this addition was used
                #to avoid some more complexed logic - just check if working hours are something extreme
                #24+ => person has worked both overtime + base => take away those 24 and you will get
                #real value for overtime hours that person has worked
                working_hours -= OVERTIME_OVERFLOW
                col = packed_column_header_codes[frozenset(code_set)] - CUMULATIVE_STARTING_COL
                employee_cumulatives[col] += working_hours
                code_set.remove("pr")
                col = packed_column_header_codes[frozenset(code_set)] - CUMULATIVE_STARTING_COL
                employee_cumulatives[col] += 8
            else:
                """Employee has worked overtime without base time (just overtime) or just base time"""
                if 'N' in code_set or 'n' in code_set:
                    day_of_shift = None
                    #get the next day to see whether to remove "hol" from code_set when allocating 6 hours
                    #for next day in night shift
                    transferable_hol = False
                    try:
                        next_day_date = f'{i + 2} {month} {year}'
                        dt = datetime.strptime(next_day_date, "%d %m %Y")
                        #EASTER + EASTER MONDAY
                        transferable_hol = holidays_cro.get(dt.date(), '') != ''
                    except ValueError as e:
                        print(str(e))
                    
                    if i in fridays:
                        day_of_shift = Day.FRIDAY
                    elif i in saturdays:
                        day_of_shift = Day.SATURDAY
                    elif i in sundays:
                        day_of_shift = Day.SUNDAY
                        print(f"{code_set=}")
                        print(f"{day_of_shift=}")
                    handle_night_shift_overflow(i, employee_cumulatives, day_of_shift, code_set, packed_column_header_codes, transferable_hol)
                else:
                    col = packed_column_header_codes[frozenset(code_set)] - CUMULATIVE_STARTING_COL
                    #if person has worked overtime, he/she could have worked for 5 hours instead of 8
                    employee_cumulatives[col] += working_hours if working_hours > 0 else 8
        
        insertion_data.append((row, employee_cumulatives))
        # print(f"MODIFIED MONTH REPORT: {e.monthly_data}")
    batch_rows_insert(start_col=CUMULATIVE_STARTING_COL, end_col=columns_count, data=insertion_data, ws=ws)
    wb.Save()
    excel_app.closeFile(CUMULATIVES_PATH)
    print(f"INSERTED cumulatives")
    return

def find_headers_row(ws : any) -> int:
    """
    Finds row in which headers are defined
    """
    used_range = ws.UsedRange
    header_key_words = ["employee id", "first", "last", "name", "organization", "unit"]
    for word in header_key_words:
        if found_cell := used_range.Find(What=word):
            # print(found_cell.Row)
            """
            Used range does not perserve original row numbers. It shrinks to the
            smallest rectangle containing data. If first 2 rows are empty, used_range
            will start from row 3 => used_range.Cells(1, 1) will actually point to
            cell (3, 1) in worksheet => hence why we need to subtract that value
            from row that headers were found in => find global (on worksheet level)
            row value of header - also need to increment the difference by 1 
            (because 1st row has index 1 => not 0 like in lists, vectors and any other
            data structure)
            """
            return found_cell.Row - used_range.Cells(1,1).Row + 1
    
def get_worksheet_name(excel_app : PyExcel, wb : any) -> str:
    all_worksheets = wb.Worksheets
    for sheet in all_worksheets:
        if sheet.Name.lower() == "evidencije" or sheet.Name.lower() == "sheet1":
            excel_app.setActiveWorkSheet(sheet.Name)
            return sheet.Name
    return ""

def main():

    os.chdir('/')
    os.chdir(INPUT_FOLDER_PATH)
    files = os.listdir()
    print(f"{files=}")

    excel_app = PyExcel()
    wb = excel_app.openFile(f"{INPUT_FOLDER_PATH}/{files[0]}")

    active_sheet_name = get_worksheet_name(excel_app, wb)
    if not active_sheet_name:
        active_sheet_name = None
    ws = excel_app.resolveSheet(active_sheet_name, wb.Name)
    
    used_range = ws.UsedRange
    row_count = used_range.Rows.Count
    col_count = used_range.Columns.Count

    employees = []
    
    categories = {}

    headers_row = find_headers_row(ws)
    # print(f"actual start in sheet: {used_range.Cells(1, 1).Row}")
    for i in range(1, col_count + 1):
        categories[i] = used_range.Cells(headers_row, i).Value
        print(f"({headers_row}, {i}): {categories[i]}")
        # print(f"({headers_row, i}):{used_range.Cells(headers_row, i).Value}")

    excel_app.closeFile(f"{INPUT_FOLDER_PATH}/{files[0]}")

    print(f"CATEGORIES: {categories}")
    for file in files:
        file_path = f"{INPUT_FOLDER_PATH}/{file}"
        wb = excel_app.openFile(file_path=file_path)        
        
        active_sheet_name = get_worksheet_name(excel_app, wb)
        if not active_sheet_name:
            active_sheet_name = None
        ws = excel_app.resolveSheet(active_sheet_name, wb.Name)

        used_range = ws.UsedRange
        row_count = used_range.Rows.Count
        col_count = used_range.Columns.Count

        print(f"------------------------------------------READING {wb.Name}------------------------------------------\n")
        for i in range(find_headers_row(ws) + 1, row_count + 1):
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
            # print(row_values)
            employees.append(Employee(row=row_values))
        excel_app.closeFile(file_path=file_path)
    # for employee in employees:
    #     print(f"{employee.ID=}")
    # excel_app.closeFile(EXCEL_INPUT_PATH)
    print("------------------------------------------Sucessfully read all input------------------------------------------")
    start_time = time.perf_counter()
    code_reports = fill_master_table(excel_app=excel_app, employees_data=employees)
    end_time = time.perf_counter()

    print(f"Insert lasted: {end_time - start_time}s")

    fill_reports_table(excel_app, code_reports)

    fill_cumulative_table(excel_app, employees)
    # fill_cumulative_table(excel_app, [])

    excel_app.quit()
    return

if __name__ == "__main__":
    main()
