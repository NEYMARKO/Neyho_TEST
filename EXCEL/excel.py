import shlex
import subprocess
import win32com.client as win32
from win32com.client import constants
import time
import os
from collections import OrderedDict
import re
import shutil
import sys
import win32com


def condenseArray(array):
    condensed=[]
    for i in range(len(array)):
        if i == 0: 
            condensed.append(array[i])
            
        else:
            tmp = condensed.pop()
            if tmp!=array[i]:
                condensed.extend([tmp,array[i]])
            else:
                condensed.append(tmp)
    return condensed

class PyExcel:

    def __init__(self, visible=True):
        try:
            self.runtime_object = win32.gencache.EnsureDispatch('Excel.Application')
        except AttributeError:
            # Remove cache and try again.
            MODULE_LIST = [m.__name__ for m in sys.modules.values()]
            for module in MODULE_LIST:
                if re.match(r'win32com\.gen_py\..+', module):
                    del sys.modules[module]
            shutil.rmtree(os.path.abspath(win32com.__gen_path__+'/..'))
        
            self.runtime_object = win32.gencache.EnsureDispatch('Excel.Application')

        self.runtime_object.Visible = visible
        self.runtime_object.DisplayAlerts = False


    def resolveWorkbook(self, wb_name):
        if wb_name is None:
            return self.runtime_object.ActiveWorkbook

        if not self.isWorkbookOpen(wb_name):
            self.openFile(wb_name)

        if "xl" in wb_name or "XL" in wb_name:
            wb_name = os.path.basename(wb_name)
            
        return self.runtime_object.Workbooks(wb_name)


    def resolveSheet(self, ws_name, wb_name=None):
        wb = self.resolveWorkbook(wb_name)
        if ws_name is None:
            return self.runtime_object.ActiveSheet
        return wb.Worksheets(ws_name)


    def setActiveWorkbook(self, wb_name):
        wb = self.resolveWorkbook(wb_name)
        wb.Activate()


    def setActiveWorkSheet(self, ws_name):
        self.runtime_object.Worksheets(ws_name).Activate()


    def get_excel(self):
        return self.runtime_object


    def quit(self):
        self.runtime_object.Application.Quit()


    def save(self, wb_name=None):
        wb = self.resolveWorkbook(wb_name)
        wb.Save()

    
    def saveAs(self, file_path):
        extension = os.path.splitext(file_path)[1]
        if extension == ".xls":
            self.runtime_object.ActiveWorkbook.SaveAs(file_path, constants.xlExcel8)
        else:
            self.runtime_object.ActiveWorkbook.SaveAs(file_path)
        

    def isWorkbookOpen(self, wb):
        wb_name = os.path.basename(wb)
        return wb_name in [w.Name for w in self.runtime_object.Workbooks]


    def openFile(self, file_path):
        try:
            if not self.isWorkbookOpen(file_path):
                wb = self.runtime_object.Workbooks.Open(Filename=file_path, UpdateLinks=False)
            else:
                wb = self.runtime_object.Workbooks(os.path.basename(file_path))
            self.setActiveWorkbook(file_path)
            return wb
        except:
            try:
                protected_window = self.runtime_object.ProtectedViewWindows.Open(file_path)
                wb = protected_window.Edit()
                return wb
            except Exception as e:
                print(f"Having trouble with opening the file: {e}")
                pass

            try:
                cmd = f"powershell -NoProfile -Command Unblock-File -Path {shlex.quote(file_path)}"
                subprocess.run(cmd, shell=True, check=False)
                wb = self.runtime_object.Workbooks.Open(file_path)
            except:
                return None

    def closeFile(self, file_path):
        if self.isWorkbookOpen(file_path):
            self.runtime_object.Workbooks(os.path.basename(file_path)).Close()


    def createFile(self, file_path):
        destination_wb = self.runtime_object.Workbooks.Add()
        destination_wb.SaveAs(file_path)


    def sheetExists(self, sheet_name, wb_name=None):
        wb = self.resolveWorkbook(wb_name)
        return sheet_name in [w.Name for w in wb.Sheets]


    def setR1C1ReferenceStyle(self):
        self.runtime_object.ReferenceStyle = constants.xlR1C1


    def setA1ReferenceStyle(self):
        self.runtime_object.ReferenceStyle = constants.xlA1


    def unMergeRange(self, range, ws_name=None):
        ws = self.resolveSheet(ws_name)
        ws.Range(range).UnMerge()
        

    def mergeRange(self, range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Range(range).Merge()
        

    def copySheetFromFile(self, source_path, destination_path, source_sheet_name=1, destination_sheet_name=1):
        source_wb = self.openFile(source_path)
        destination_wb = self.openFile(destination_path)

        source_ws = source_wb.Worksheets(source_sheet_name)
        source_ws.Copy(After=destination_wb.Worksheets(destination_wb.Worksheets.Count))

        destination_wb.Worksheets(destination_wb.Worksheets.Count).Name = destination_sheet_name
        self.setActiveWorkbook(os.path.basename(destination_path))


    def copyAllUsedCellValues(self, source_path, destination_path, source_sh=1, destination_sh=1, destination_range="A1"):
        source_wb = self.openFile(source_path)
        destination_wb = self.openFile(destination_path)

        source_ws = source_wb.Worksheets(source_sh)
        destination_ws = destination_wb.Worksheets(destination_sh)

        source_ws.UsedRange.Copy(destination_ws.Range(destination_range))
        self.setActiveWorkbook(destination_path)


    def copyColumnFromFile(self, source_path, source_column,  destination_path, destination_column, 
    destination_sheet=1, source_sheet=1, s_column_start=1, d_column_start=1):
        
        if(not os.path.isfile(destination_path)):
            self.createFile(destination_path)
            time.sleep(1)
        
        destination_wb = self.openFile(destination_path)
        destination_ws = destination_wb.Worksheets(destination_sheet)

        source_wb = self.openFile(source_path)
        source_ws = source_wb.Worksheets(source_sheet)

        total_rows = self.getTotalUsedRows(source_sheet, source_path)
        source_range = source_column + str(s_column_start) + ":" + source_column + str(total_rows)
        destination_range = destination_column + str(d_column_start) +":" + destination_column + str(total_rows)

        source_ws.Range(source_range).Copy(destination_ws.Range(destination_range))
        destination_ws.Columns(destination_column).AutoFit()

        self.setActiveWorkbook(os.path.basename(destination_path))


    def copyRangeFromFile(self, source_path, source_range,  destination_path, destination_range, 
    destination_sheet=1, source_sheet=1):

        if(not os.path.isfile(destination_path)):
            self.createFile(destination_path)
            time.sleep(1)

        destination_wb = self.openFile(destination_path)
        destination_ws = destination_wb.Worksheets(destination_sheet)

        source_wb = self.openFile(source_path)
        source_ws = source_wb.Worksheets(source_sheet)

        source_ws.Range(source_range).Copy(destination_ws.Range(destination_range))
        #destination_ws.Range(destination_range).AutoFit()
        self.setActiveWorkbook(os.path.basename(destination_path))


    def setCellValue(self, value, cell_location, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Cells(cell_location[0], cell_location[1]).Value = value


    def setRangeValue(self, value, range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Range(range).Value = value

        
    def simpleRoundFunction(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"
        for cell in ws.Range(range):
            formula =f"=ROUND({cell.Value}, 0)"
            cell.Formula = formula


    def setNumberFormat(self, format, range):
        ws = self.runtime_object.ActiveSheet
        ws.Range(range).NumberFormat = format


    def setFormula(self, formula, range, r1c1=False, ws_name=None, wb_name=None): 
        ws = self.resolveSheet(ws_name, wb_name)
        if r1c1:
            if self.runtime_object.ReferenceStyle != constants.xlR1C1 : 
                self.setR1C1ReferenceStyle()
            ws.Range(range).FormulaR1C1=formula
        else:
            ws.Range(range).Formula=formula
        if self.runtime_object.ReferenceStyle != constants.xlR1C1 : 
            self.setA1ReferenceStyle()

    def setFormulaToColumn(self, formula, column, start=2, r1c1=False, ws_name=None, wb_name=None):
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"
        self.setFormula(formula, range, r1c1, ws_name, wb_name)
        

    def setNumberFormatToColumn(self, format, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range= f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"        
        ws.Range(range).NumberFormat = format


    def copyCellFormat(self, source_cell_location, destination_cell_location):
        ws = self.runtime_object.ActiveSheet

        style = ws.Cells(source_cell_location[0], source_cell_location[1]).Style
        ws.Cells(destination_cell_location[0], destination_cell_location[1]).Style = style


    def autoFit(self, range):
        ws = self.runtime_object.ActiveSheet
        ws.Range(range).Columns.AutoFit()


    def getTotalRows(self):
        return self.getTotalUsedRows()
        #return self.runtime_object.ActiveSheet.UsedRange.Rows.Count

    
    def getTotalRowsOfWorkbook(self, wb_path, ws_name=1):
        wb = self.openFile(wb_path)
        return  wb.Worksheets(ws_name).UsedRange.Rows.Count


    def convert_xlsx_to_xls(self, xlsx_file_path):
        self.openFile(xlsx_file_path)
        new_path = xlsx_file_path[:-1]
        self.runtime_object.ActiveWorkbook.SaveAs(new_path, FileFormat=56)
        self.closeFile(xlsx_file_path)
        os.remove(xlsx_file_path)
        return new_path


    def copyCellStyle(self, source_cell, destination_cell):
        ws = self.runtime_object.ActiveSheet
        ws.Range(destination_cell).Style = ws.Range(source_cell).Style


    def simpleTrimLetters(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        for cell in ws.Range(range):
            value = cell.Value
            if value is not None:
                cell.Value = value.split(",")[0]


    def simpleConvertTimestampToDate(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        for cell in ws.Range(range):
            cell.Value = cell.Text


    def simpleUnique(self, sc_range, dt_range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        for cell in ws.Range(dt_range):
            cell.Formula = f'=UNIQUE({sc_range})'
        

    def simpleClean(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        for cell in ws.Range(range):
            formula =f"=CLEAN({cell.Value})"
            cell.Formula = formula


    def simpleTrim(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        for cell in ws.Range(range):
            formula =f"=TRIM({cell.Value})"
            cell.Formula = formula


    def trimFunction(self, column, value, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        ws.Range(range).Formula=f'=TRIM({value})'


    def simpleLeft(self, column, value=10, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"
        for cell in ws.Range(range):
            cell_value = cell.Value.replace(",", "") if isinstance(cell.Value, str) else cell.Value
            formula =f'=LEFT("{cell_value}", {value})'            
            cell.Formula = formula


    def simpleValue(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"

        for cell in ws.Range(range):
            formula =f"=VALUE({cell.Value})"
            cell.Formula = formula


    def simpleFilter(self, range, field, criteria, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Range(range).AutoFilter(Field=field, Criteria1=criteria)


    def simpleConvertTextToNumber(self, column, start=2, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        range = f"{column}{start}:{column}{self.getTotalUsedRows(ws_name, wb_name)}"        
        for cell in ws.Range(range):            
            if cell.Value == None:
                continue
            cell.Value = cell.Value * 1
            

    def turnOffAutofilter(self, ws_name=None, wb_name=None):
        self.resolveSheet(ws_name, wb_name).AutoFilterMode = False


    def read(self, range, file_path = None, ws_name = None, wb_name=None):
        if file_path:
            wb_name = file_path

        ws = self.resolveSheet(ws_name, wb_name)
        
        values = ws.Range(range).Value
        if not isinstance(values, tuple):
            return values

        return [list(value) for value in values]
        #return [ cell.Text for cell in ws.Range(range) ]


    def getColumnLetter(self, column_number):
        ws = self.runtime_object.ActiveSheet
        address = ws.Cells(1, column_number).Address
        return address.split("$")[1]


    def getHeaders(self, row_num=1, ws_name=None, as_dict=False, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        columns_count = ws.UsedRange.Columns.Count
        x_range = f"A{row_num}:{self.getColumnLetter(columns_count)}{row_num}"
        values = self.read(x_range, ws_name=ws_name, wb_name=wb_name)[0] 
        
        if not as_dict:
            return values

        clmn_letters = [self.getColumnLetter(i) for i in range(1, columns_count+1)]
        return dict(zip(values, clmn_letters))
        


    def readAll(self, file_path=None, ws_name=None, header_row=1, values_row=2):
        ws = self.resolveSheet(wb_name=file_path, ws_name=ws_name)
            
        columns_count = ws.UsedRange.Columns.Count
        rows_count = self.getTotalUsedRows()

        if (rows_count == 1 and columns_count == 1) or (rows_count > 1000000 and columns_count == 1):
            return {}
        
        headers = self.getHeaders(header_row, ws_name=ws_name, wb_name=file_path)
        value_range = f'A{values_row}:{self.getColumnLetter(columns_count)}{rows_count}'
        values = self.read(value_range, file_path, ws_name)
        return [OrderedDict(zip(headers, value)) for value in values]


    def appendData(self, data:list[dict], wb_name=None, ws_name=None, starting_column="A"):
        if not data:
            return
        
        ws = self.resolveSheet(ws_name, wb_name)
        first_empty_row = self.getTotalUsedRows(ws_name, wb_name) + 1
        last_column = self.getColumnLetter(len(list(data[0].keys())))

        last_row = first_empty_row + len(data) - 1
        if first_empty_row == 1:
            ws.Range(f"{starting_column}{first_empty_row}:{last_column}{first_empty_row}").Value = list(data[0].keys())
            last_row += 1
            first_empty_row += 1
        
        tmp_data = [list(row.values()) for row in data]        
        ws.Range(f"{starting_column}{first_empty_row}:{last_column}{last_row}").Value = tmp_data


    ## location = (row, column)
    def writeAll(self, dict_data, file_path=None, ws_name=None, header_location=(1,1), values_location=(2,1)):
        ws = self.resolveSheet(ws_name, file_path)
        
        if not dict_data:
            return

        headers = list(dict_data[0].keys())
        last_column = self.getColumnLetter(len(headers) + header_location[1] - 1)

        header_column = self.getColumnLetter(header_location[1])
        values_column = self.getColumnLetter(values_location[1])

        self.setRangeValue(headers, f"{header_column}{header_location[0]}:{last_column}{header_location[0]}", ws_name=ws_name, wb_name=file_path)
        for i in range(0, len(dict_data)):
            value_range = f"{values_column}{i+values_location[0]}:{last_column}{i+values_location[0]}"
            data = [str(x) for x in list(dict_data[i].values())]
            self.setRangeValue(data, value_range, ws_name=ws_name, wb_name=file_path)


    def writeDict(self, dict, ws_name = None, row_num=2, wb_name=None):
        headers = self.getHeaders(as_dict=True, ws_name=ws_name, wb_name=wb_name)
        for key in dict.keys():
            self.setRangeValue(dict[key], f"{headers[key]}{row_num}", ws_name=ws_name, wb_name=wb_name)


    def readAsDict(self, *headers, ws_name=None, row_num=2, header_row=1, wb_name=None):
        all_headers = self.getHeaders(as_dict=True, ws_name=ws_name, row_num=header_row, wb_name=wb_name)
        values = {}
        for header in headers:
            value = self.read(f"{all_headers[header]}{row_num}", ws_name=ws_name, wb_name=wb_name)
            values[header] = value

        return values

    def addSheet(self, sheet_name, wb_name=None):
        wb = self.resolveWorkbook(wb_name)

        ws = wb.Sheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
        ws.Name = sheet_name


    def write(self, data, column, start=2, ws_name=None, wb_name=None):
        for i in range(len(data)):
            rng = f'{column}{i+start}'
            self.setRangeValue(range=rng, value=data[i], ws_name=ws_name, wb_name=wb_name)


    def copyToClipboard(self, range):
        ws = self.runtime_object.ActiveSheet
        ws.Range(range).Copy()


    def pasteSpecial(self, range, option):
        ws = self.runtime_object.ActiveSheet
        ws.Range(range).PasteSpecial(Paste=option)


    def printOpenWorkbooks(self):
        for wb in self.runtime_object.Workbooks:
            print(wb.Name)


    def deleteUsedCells(self, sh_name=None, wb_name=None):
        ws = self.resolveSheet(sh_name, wb_name)
        ws.UsedRange.Delete()


    def deleteSheet(self, sh_name=1, wb_name=None):
        wb = self.resolveWorkbook(wb_name)

        wb.Worksheets(sh_name).Delete()


    def deleteColumns(self, *column_names):
        ws = self.runtime_object.ActiveSheet
        
        column_ranges = []
        for column in column_names:
            column_ranges.append(ws.Range(f'{column}:{column}'))
        self.runtime_object.Union(*column_ranges).EntireColumn.Delete()    



    def deleteRange(self, range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Range(range).Delete()


    def cutRange(self, dt_range, sc_range, sc_path=None, dt_path=None, sc_ws = 1, dt_ws = 1):
        if dt_path and sc_path:
            destination_ws = self.openFile(dt_path).destination_wb.Worksheets(dt_ws)
            source_ws = self.openFile(sc_path).source_wb.Worksheets(sc_ws)
        elif sc_path:
            source_ws = destination_ws = self.openFile(sc_path).Worksheets(sc_ws)
        else:
            source_ws = destination_ws = self.runtime_object.ActiveWorkbook.Worksheets(sc_ws)
        if type(dt_range) == str:
            dt_range = destination_ws.Range(dt_range)
        if type(sc_range) == str:
            sc_range = source_ws.Range(sc_range)
            
        sc_range.Cut(dt_range)


    def copyRange(self, dt_range, sc_range, sc_path=None, dt_path=None, sc_ws = 1, dt_ws = 1):
        if dt_path and sc_path:
            destination_ws = self.openFile(dt_path).destination_wb.Worksheets(dt_ws)
            source_ws = self.openFile(sc_path).source_wb.Worksheets(sc_ws)
        elif sc_path:
            source_ws = destination_ws = self.openFile(sc_path).Worksheets(sc_ws)
        else:
            source_ws = destination_ws = self.runtime_object.ActiveWorkbook.Worksheets(sc_ws)
        if type(dt_range) == str:
            dt_range = destination_ws.Range(dt_range)
        if type(sc_range) == str:
            sc_range = source_ws.Range(sc_range)
            
        sc_range.Copy(dt_range)  


    def setTextAsValue(self, range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        for cell in ws.Range(range):
            cell.Value = cell.Text


    def alignRows(self, last_column, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        used_range = ws.UsedRange
        used_columns = used_range.Columns.Count
        needed_columns = used_range.Columns(last_column).Column

        if  used_columns == needed_columns:
            return
                
        for column_index in reversed(range(needed_columns+1, used_columns+1)):
            while(True):
                protruding_cell = ws.Columns(column_index).End(constants.xlDown)
                if protruding_cell.Value is None:
                    break
                row = ws.Range(protruding_cell, protruding_cell.End(constants.xlToLeft))
                if row.Count != used_columns:
                    self.cutRange(ws.Cells(row.Row, row.Columns(1).Column-1), row)
                    continue
                for cell_column_index in range(1, used_columns):
                    cell = ws.Cells(row.Row, cell_column_index)
                    previous_cell = cell if cell_column_index == 1 else ws.Cells(row.Row, cell_column_index-1)
                    next_cell = ws.Cells(cell.Row, cell.Column +1)
                    if cell.Text == " ":
                        move_range = ws.Range(next_cell, next_cell.End(constants.xlToRight))
                        self.cutRange(cell, move_range)
                    elif cell.Text in previous_cell.Text and cell_column_index!=1:
                        cell.Value=" "
                        #break
                        #self.cutRange(cell, ws.Range(next_cell, next_cell.End(constants.xlToRight)))         
            

    def autoFitAll(self):
        self.runtime_object.ActiveSheet.Cells.EntireColumn.AutoFit()


    def joinColumns(self, *columns, delimiter='" "'):
        ws = self.runtime_object.ActiveSheet
        last_column = ws.Columns(ws.UsedRange.Columns.Count).Column
        formula="="
        for column in columns:
            index = ws.Columns(column).Column
            if column == columns[0]:
                formula = formula + f"RC[{index-last_column-1}]"
            else:
                formula = formula + f'&{delimiter}&RC[{index-last_column-1}]'
        self.setR1C1ReferenceStyle()
        ws.Columns(ws.UsedRange.Columns.Count +1).Formula = formula
        self.setA1ReferenceStyle()


    def copyFormats(self, sc_range, dest_range):
        self.copyToClipboard(sc_range)
        self.pasteSpecial(dest_range, constants.xlPasteFormats)


    def wrapText(self, range, wrap=True):
        self.runtime_object.ActiveSheet.Range(range).WrapText = wrap


    def append_row(self, row, offset=0, column=2):
        ws = self.runtime_object.ActiveSheet
        row_index = ws.Columns(column).End(constants.xlDown).Row + 1
       
        for i in range(1+offset,len(row)+1):
            self.setCellValue(row[i-1], (row_index,i))


    def runMacro(self, macro_name):
        self.runtime_object.Run(macro_name)


    ## return last row that has any value
    def getTotalUsedRows(self, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name=ws_name, wb_name=wb_name)
        max_count = 0
        for i in range(1, 3):
            column = self.getColumnLetter(i)
            count = ws.Range(f'{column}65536').End(constants.xlUp).Row
            if count != 1 and count > max_count:
                max_count = count
            if max_count == 0:
                if self.read(f'{column}1', ws_name=ws_name, wb_name=wb_name) is not None:
                    max_count = 1
                else:
                    max_count = 0
        
        return max_count


    def refreshPivotTable(self, pivot_name, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.PivotTables(pivot_name).PivotCache().Refresh()


    def refreshAll(self, wb_name=None):
        wb = self.resolveWorkbook(wb_name)
        wb.RefreshAll()


    def autoFillFormula(self, src_range, dest_range, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.Range(src_range).AutoFill(ws.Range(dest_range))

    
    def doubleClickPivotCell(self, row_name, column_name, pivot_name=1, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)

        pvt = ws.PivotTables(pivot_name)

        row_names = [c for c in [r for r in pvt.TableRange1.Columns][0].Cells]      
        column_names = [c for c in [r for r in pvt.TableRange1.Rows][1].Cells]
        
        colum_num = [c.Address.split("$")[1] for c in column_names if c.Value==column_name]
        row_num = [c.Address.split("$")[2] for c in row_names if c.Value==row_name]

        if not colum_num or not row_num:
            raise ValueError(f'There is no column "{column_name}" or row "{row_name}" in pivot table "{pivot_name}"!')

        colum_num = colum_num[0]
        row_num = row_num[0]
    
        rng = ws.Range(f"{colum_num}{row_num}")
        rng.Select()
        rng.ShowDetail = True
            
    ## dest = (row, column)
    def createPivotTable(self, source_data, table_destination=(1,1), pt_name="P", ws_name=None, wb_name=None, **table_properties):
        wb = self.resolveWorkbook(wb_name)
        ws = self.resolveSheet(ws_name, wb_name)
        
        cache = wb.PivotCaches().Create(SourceType=constants.xlDatabase, SourceData=source_data)
        pivot_table = cache.CreatePivotTable(TableDestination=ws.Cells(table_destination[0],table_destination[1]), TableName=pt_name)

        for key, value in table_properties.items():
            setattr(pivot_table, key, value)

        return pivot_table
        

    ## columns - column indexes
    def removeDuplicates(self, range, columns, headers=True, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        if headers:
            ws.Range(range).RemoveDuplicates(columns, constants.xlYes)
        else:
            ws.Range(range).RemoveDuplicates(columns, constants.xlNo)


    def deletePivotTable(self, pvt_name, ws_name=None, wb_name=None):
        ws = self.resolveSheet(ws_name, wb_name)
        ws.PivotTables(pvt_name).TableRange2.Clear()



def main():
    destination_path = r"C:\Users\robot1\Desktop\proba.xlsx"
    source_path = r"C:\Users\robot1\Downloads\Nalog_za_plaćanje_-_detaljno.xlsx"
    excel = PyExcel()
    
    excel.openFile(destination_path)
    #excel.copyColumnFromFile(source_path=source_path, source_column="B", source_sheet="Podaci", destination_path=destination_path, destination_column="F", destination_sheet=1)
    time.sleep(5)
    excel.quit()


if __name__=="__main__":
    main()
    