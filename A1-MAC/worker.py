from pathlib import Path
from zipfile import ZipFile
import hardcoded_config as hc
from datetime import datetime
from data_extractor import extract_data, result_complete

DAY, MONTH, YEAR= (datetime.now().day, datetime.now().month, datetime.now().year)

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
    file_path.rename(output_dir_path / file_name)
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
    print(f"{extracted_data=}")
    if not result_complete(extracted_data):
        print(f"UNABLE TO EXTRACT ALL RELEVANT DATA for file: {file_path.name}")
        return {}
    # processed_files.append(x.name)
    extracted_data['flow'] = flow
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

def main():
    root_folder_path_obj = Path(__file__).parent / "INPUT/DEBUG/PRODUCTION_SIM"
    file_no = 0
    archive_dir_path = create_backup_dir(root_folder_path_obj / "BACKUP", (YEAR, MONTH, DAY), 3)
    filenet_temp_path = root_folder_path_obj / "FILENET_TEMP" 
    if not filenet_temp_path.exists() or not filenet_temp_path.is_dir():
        filenet_temp_path.mkdir(parents=True, exist_ok=True)
    results = []
    for x in root_folder_path_obj.iterdir():
        extracted = {}
        flow = ''
        print(f"{x.name=}")
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
        elif x.is_file() and x.name.endswith("pdf"):
        # print(f"\n{str(x)=}\n")
            save_data(x, file_no, results)
            move_files(filenet_temp_path, [x])
            # move_file(output_dir_path, x)
            # print(f"\n{extracted_data=}\n")
            file_no += 1
        move_files(archive_dir_path, list(filenet_temp_path.iterdir()))
        clear_dir(filenet_temp_path)
    return

if __name__ == "__main__":
    main()