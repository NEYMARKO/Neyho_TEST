import win32com.client as win32
import os
from excel import PyExcel
import time
# import pyautogui

EXCEL_INPUT_FILE = "DS_06_2025_168_BB.xlsx"
EXCEL_INPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXCEL_INPUT_FILE)
EXCEL_OUTPUT_FILE = "Hospira evidencije rada 06-2025.xlsm"
EXCEL_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXCEL_OUTPUT_FILE)
# excel = win32.gencache.EnsureDispatch('Excel.Application')
# excel.Visible = True

OUTPUT_FILE_HEADER_ROW = 2

class Employee:
    
    def __init__(self, row : dict) -> None:
        self.ID = row.get('Employee ID', '')
        self.organization_unit = row.get('Organization unit', '')
        self.first_name = row.get('First name', '')
        self.last_name = row.get('Surname', '')
        self.monthly_data = row.get('monthly_data', '')
    
    def struct_data(self):
        return [self.ID, self.organization_unit, self.first_name, self.last_name, self.monthly_data]

    def print_data(self):
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
        
        # print(f"Dropdown values: {allowed_values}")
        return allowed_values
    
    except:
        print("No validation available")

def pick_dropdown_value(cell_name : str, value : str, ws : any, wb : any) -> None:
    cell = ws.Range(cell_name)
    cell.Select()
    validation = ws.Range(cell_name).Validation
    if value not in extract_values_from_validation(validation_formula=validation.Formula1, wb=wb):
        print(f"Value {value} not defined")
        return
    cell.Value = value

    return

def batch_row_insert(row : int, start_col : int, end_col : int, data : list[str], ws : any) -> None:
    used_range = ws.UsedRange
    for row, row_details in data:
        data_2d = [row_details]
        target_range = ws.Range(used_range.Cells(row, start_col), used_range.Cells(row, end_col))
        target_range.Value = data_2d
    # data_2d = [data]
    # target_range = ws.Range(ws.Cells(row, start_col), ws.Cells(row, end_col))
    # target_range.Value = data_2d

    return

def find_employee_in_table(id : str, ws : any) -> tuple[list[str], int]:
    """
    Returns row's content and index for employee that matches parameter id.
    """
    found_cell = ws.UsedRange.Find(What=id)
    if found_cell:
        row = found_cell.Row
        col_cnt = ws.UsedRange.Columns.Count
        return ([ws.Cells(row, col).Value for col in range(1, col_cnt + 1)], row)
    return ([], -1)

def populate_output(excel_app : any, employees_data : list[Employee]) -> None:

    wb = excel_app.openFile(EXCEL_OUTPUT_PATH)
    ws = excel_app.resolveSheet("Evidencija", wb.Name)

    columns_count = ws.UsedRange.Columns.Count

    starting_col = -1
    ending_col = -1
    for i in range(1, columns_count + 1):
        try:
            # print(f"CELL VALUE : {ws.Cells(OUTPUT_FILE_HEADER_ROW, i).Value}")
            int(ws.Cells(OUTPUT_FILE_HEADER_ROW, i).Value)
            # days_columns_indexes.append(i)
            if starting_col == -1:
                starting_col = i
        except:
            if starting_col != -1:
                ending_col = i - 1
                break
    
    print(f"{starting_col=}, {ending_col=}")
    data = []
    validation_cache = []
    for employee in employees_data:
        row_data, row = find_employee_in_table(id=employee.ID, ws=ws)
        print(f"{row=}")
        if row_data:
            codes_list = []
            for i in range(starting_col, ending_col + 1):
                cell = ws.Cells(row, i)
                # cell_name = cell.Address
                # print(f"CELL NAME: {cell_name}")
                #i - starting_col because loop starts from starting_col => list items are in range [0, len(list)]
                value = employee.monthly_data[i - starting_col]
                if not validation_cache:
                    validation_cache = extract_values_from_validation(validation_formula=cell.Validation.Formula1, wb=wb)
                if not value or value not in validation_cache:
                    codes_list.append(None)
                    continue
                codes_list.append(value)
                # pick_dropdown_value(cell_name=cell_name, value=value, ws=ws, wb=wb)
        # print(f"Row data: {data}")
        row_tuple = (row, codes_list)
        data.append(row_tuple)
    batch_row_insert(row=row, start_col=starting_col, end_col=ending_col, data=data, ws=ws)
    wb.Save()
    excel_app.closeFile(EXCEL_OUTPUT_PATH)
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
        categories[i] = ws.Cells(1, i).Value

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

    excel_app.closeFile(EXCEL_INPUT_PATH)
    # for employee in employees:
    #     employee.print_data()
    start_time = time.perf_counter()
    populate_output(excel_app=excel_app, employees_data=employees)
    end_time = time.perf_counter()

    print(f"Insert lasted: {end_time - start_time}s")
    excel_app.quit()
    return

if __name__ == "__main__":
    main()
