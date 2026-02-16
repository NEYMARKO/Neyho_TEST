from pathlib import Path
from zipfile import ZipFile
import hardcoded_config as hc
from datetime import datetime
from data_extractor import extract_data, result_complete

DAY, MONTH, YEAR= (datetime.now().day, datetime.now().month, datetime.now().year)

def create_dir(root_dir : Path, date_tuple : tuple[int, int, int], level : int) -> Path:
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
    file_path.rename(output_dir_path / file_name)
    return

def save_data(file_path : Path, file_no : int, results : list[dict], zip_file_no : int = -1) -> dict:
    extracted_data = extract_data(file_path, file_no)
    print(f"{extracted_data=}")
    if not result_complete(extracted_data):
        print(f"UNABLE TO EXTRACT ALL RELEVANT DATA for file: {file_path.name}")
        return {}
    # processed_files.append(x.name)
    ban = extracted_data.get(hc.BAN_STRING)
    file_path = file_path.rename(file_path.parent / (f"{ban}.pdf" if zip_file_no == -1 else f"{ban}_{zip_file_no}.pdf"))
    results.append(extracted_data)
    return extracted_data

def main():
    root_folder_path_obj = Path(__file__).parent / "INPUT/DEBUG/PRODUCTION_SIM"
    file_no = 0
    output_dir_path = create_dir(root_folder_path_obj / "BACKUP", (YEAR, MONTH, DAY), 3)
    results = []
    for x in root_folder_path_obj.iterdir():
        processed_files = []
        print(f"{x.name=}")
        if x.is_file() and x.name.endswith("zip"):
            zip_dir_path = x.parent / "ZIP_EXTRACTED"
            zip_file_no = 1
            with ZipFile(x, 'r') as zip:
                zip.extractall(zip_dir_path)
            for file_path in zip_dir_path.iterdir():
                save_data(file_path, file_no, results, zip_file_no)
                file_no += 1
                zip_file_no += 1
        elif x.is_file() and x.name.endswith("pdf"):
        # print(f"\n{str(x)=}\n")
            save_data(x, file_no, results)
            move_file(output_dir_path, x)
            # print(f"\n{extracted_data=}\n")
            file_no += 1

    return

if __name__ == "__main__":
    main()