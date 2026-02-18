import pandas as pd
from time import time
from pathlib import Path
from zipfile import ZipFile
import hardcoded_config as hc
from datetime import datetime
from data_extractor import extract_data, result_complete
DAY, MONTH, YEAR = (datetime.now().day, datetime.now().month, datetime.now().year)

TICKET_NUMBER_STRING = "Ticket_Number"
SCENARIO_STRING = "Scenario (A or B)"
BAN_STRING = "BAN"
CONTRACT_DATE_STRING = "Contract_Date"
CUSTOMER_TYPE_STRING = "Customer_Type"
EMBG_EDB_STRING = "EMBG_EDB"
DOCUMENT_ENTRY_DATE_STRING = "Document_Entry_Date"
FILE_LOCATION_STRING = "File_Location"
STATUS_UPLOADED_STRING = "Status_Uploaded"
STATUS_CHECKED_STRING = "Status_Checked"
STATUS_RESOLVED_STRING = "Status_Resolved"
STATUS_FAIL_STRING = "Status_Fail"
STATUS_DELETED_FROM_FOLDER = "Status_Deleted_From_Folder"
STATUS_DELETED_FROM_ESIGN = "Status_Deleted_From_eSign"
ERROR_COMMENT_STRING = "Error_Comment"
CREATED_TIMESTAMP_STRING = "Created_Timestamp"
LAST_UPDATED_TIMESTAMP_STRING = "Last_Updated_Timestamp"

def create_backup_dir(root_dir : Path, date_tuple : tuple[int, int, int], level : int) -> Path:
    current_dir = root_dir
    if level > len(date_tuple):
        level = len(date_tuple)
    for i in range(level):
        current_dir = current_dir / f"{'0' if len(str(date_tuple[i])) == 1 else ''}{str(date_tuple[i])}"
        if not current_dir.exists() or not current_dir.is_dir():
            current_dir.mkdir(parents=True, exist_ok=True)
    return current_dir

def move_file(output_dir_path : Path, file_path : Path) -> None:
    file_name = file_path.name
    try:
        file_path.rename(output_dir_path / file_name)
    except FileExistsError:
        print(f"file {file_name} already exists")
    return

def move_files(output_dir_path : Path, input_files : list[Path]) -> Path:
    """
    Moves files to folder defined by 'output_dir_path' variable.
    Accepts list of file paths and transfers them to output_dir
    """
    for file_path in input_files:
        move_file(output_dir_path, file_path)
    return output_dir_path

def rmdir(target_dir : Path) -> None:
    directory = Path(target_dir)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()
    return

def clear_dir(target_dir : Path) -> None:
    for item in target_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            rmdir(item)
    return

def save_data(file_path : Path, file_no : int, results : list[dict]) -> dict:
    extracted_data, flow = extract_data(file_path, file_no)
    # print(f"{extracted_data=}")
    if not result_complete(extracted_data):
        print(f"UNABLE TO EXTRACT ALL RELEVANT DATA for file: {file_path.name}")
        return {}
    # processed_files.append(x.name)
    # extracted_data['flow'] = flow
    ban = extracted_data.get(hc.BAN_STRING)
    file_path = file_path.rename(file_path.parent / f"{ban}.pdf" )
    results.append(extracted_data)
    return extracted_data

def rename_all_zip_files(all_file_paths : list[Path], ban : str) -> None:
    if not ban:
        raise RuntimeError("UNABLE TO EXTRACT INFO FROM ZIP")
    for i in range(len(all_file_paths)):
        all_file_paths[i].rename(all_file_paths[i].parent / f"{ban}_{i + 1}.pdf")
    return

# def read_current_excel_content(excel_file_path : Path) -> pd.DataFrame:
#     df = pd.DataFrame()
#     with pd.ExcelFile(str(excel_file_path)) as xls_obj:
#             df = pd.read_excel(xls_obj, na_values=["None", "null", "NULL", ""], 
#                                nrows=10000, header=None, sheet_name=0)
#     df = df.dropna(thresh=1)
#     df.columns = df.iloc[0]
#     df = df[1:]
#     df = df.reset_index(drop=True)
#     print(f"{df=}")
#     return df

def append_data_to_excel(data : dict, excel_file_path : Path) -> None:
    # df = pd.concat([df, new_row], ignore_index=True)
    with pd.ExcelWriter(
        str(excel_file_path),
        engine="openpyxl",
        mode="a",
        if_sheet_exists="overlay"
        ) as writer:

            sheet = writer.sheets["Sheet1"]
            startrow = sheet.max_row  # find last used row
            data[TICKET_NUMBER_STRING] = startrow
            new_row = pd.DataFrame([data])

            headers = [cell.value.strip() for cell in sheet[1]]
            # print(f"{headers=}")
            new_row = new_row.reindex(columns=headers) #reorder data to match corresponding column

            new_row.to_excel(
                writer,
                sheet_name="Sheet1",
                index=False,
                header=False,
                startrow=startrow
            )
    return

def main():
    root_folder_path_obj = Path(__file__).parent / "INPUT/DEBUG/PRODUCTION_SIM"
    file_no = 0
    archive_dir_path = create_backup_dir(root_folder_path_obj / "BACKUP", (YEAR, MONTH, DAY), 3)
    filenet_temp_path = root_folder_path_obj / "FILENET_TEMP" 
    if not filenet_temp_path.exists() or not filenet_temp_path.is_dir():
        filenet_temp_path.mkdir(parents=True, exist_ok=True)
    results = []
    # df = read_current_excel_content(root_folder_path_obj / "../../EXCEL_TEMPLATE/Book1.xlsx")
    start = time()
    for x in root_folder_path_obj.iterdir():
        extracted = {}
        # flow = ''
        # print(f"{x.name=}")
        if x.is_file() and x.name.endswith("zip"):
            #ALL FILES WILL HAVE THE SAME BAN, IF DATA GOT EXTRACTED FROM SINGLE FILE
            #IT WILL BE APPLIABLE TO ALL THE REST OF THEM - NO NEED TO PROCESS THE REST
            zip_dir_path = x.parent / "ZIP_EXTRACTED"
            extracted = {}
            with ZipFile(x, 'r') as zip:
                zip.extractall(zip_dir_path)
            for file_path in zip_dir_path.iterdir():
                extracted = save_data(file_path, file_no, results)
                if extracted:
                    break
                file_no += 1
            rename_all_zip_files(list(zip_dir_path.iterdir()), extracted.get(hc.BAN_STRING, ""))
            move_files(filenet_temp_path, list(zip_dir_path.iterdir()))
            zip_dir_path.rmdir()
            x.unlink()
        elif x.is_file() and x.name.endswith("pdf"):
        # print(f"\n{str(x)=}\n")
            extracted = save_data(x, file_no, results)
            move_files(filenet_temp_path, [x.parent / f"{extracted.get(hc.BAN_STRING)}.pdf"])
            # move_file(output_dir_path, x)
            print(f"\nresult={extracted}\n")
            file_no += 1
        else:
            continue
        data = {
                TICKET_NUMBER_STRING: 0,
                BAN_STRING: extracted.get(hc.BAN_STRING),
                CONTRACT_DATE_STRING: extracted.get(hc.CONTRACT_DATE_STRING), 
                CUSTOMER_TYPE_STRING: "RESIDENT" if extracted.get(hc.RESIDENT_CUSTOMER_STRING) else "BUSINESS",
                EMBG_EDB_STRING: extracted.get(hc.EMBG_EDB_STRING),
                DOCUMENT_ENTRY_DATE_STRING: datetime.now().strftime('%m/%d/%Y'),
                FILE_LOCATION_STRING: "SOME_FOLDER",
                STATUS_UPLOADED_STRING: "YES",
                STATUS_CHECKED_STRING: "YES",
                STATUS_RESOLVED_STRING: "YES",
                STATUS_FAIL_STRING: "NO"
                }
        # print(f"{data=}")
        move_files(archive_dir_path, list(filenet_temp_path.iterdir()))
        clear_dir(filenet_temp_path)
        append_data_to_excel(data, root_folder_path_obj / "../../EXCEL_TEMPLATE/Book1.xlsx")
    end = time()
    print(f"EXECUTION LASTED: {end - start} sec")
    return

if __name__ == "__main__":
    main()