import json
import os
import sys

REF_FILE = 'reference.json'
COMP_FILE = 'comparison.json'
DIFFERENCE_DIR = 'difference'
DIFFERENCE_FILE = 'difference.json'

ADD_MACRO = "ADDED to new file"
MISS_MACRO = "MISSING from new file"
DIFF_MACRO = "DIFFERENT from reference file"

sys.path.insert(1, r"C:\Users\Marko\Desktop\Neyho\Neyho_TEST")
if os.name == 'posix':  # (macOS, Linux)
    sys.path.insert(1, os.path.join("..", ".."))

    INPUT_DIR = os.path.join(os.path.expanduser("~"), 'comp_input')

elif os.name == 'nt':  # Windows
    #root directory
    sys.path.insert(1, r"C:\Users\Marko\Desktop\Neyho\Neyho_TEST")

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(SCRIPT_DIR, "comp_input")

def load_json_file(input_dir : str, input_file : str) -> dict:
    try:
        with open(os.path.join(input_dir, input_file), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        print(f"Failed to load {input_dir}/{input_file}")

def write_to_json_file(data: dict, directory: str, file_name: str) -> None:
    """
    Writes provided data to json file in location provided by relative_path (path is relative to bobo_db.py file location)
    """
    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    with open(os.path.join(directory, file_name), "w", encoding="utf-8") as f:
        f.write(json_str)

def compare_json_files(reference_value : dict|str|float|list, 
                       comparison_value : dict|str|float|list,
                       path : str, diffs : dict[str, list[str]]) -> None:
    # print(f"{reference_value=}\n{comparison_value=}")
    #both values are dicts => go deeper in the structure
    if isinstance(reference_value, dict) and isinstance(comparison_value, dict):
        all_keys = set(reference_value.keys()) |set(comparison_value.keys())
        for combined_key in all_keys:
            if combined_key == "extraction_timestamp":
                continue
            ref_value = reference_value.get(combined_key, None)
            comp_value = comparison_value.get(combined_key, None)

            #combined_key doesn't exist in reference_value => File that we are comparing
            #has some extra data relative to reference file
            if combined_key not in reference_value:
                diffs.get(ADD_MACRO).append(f"{path}{'.' if path else ''}{combined_key}")
            #combined_key doesn't exist in comparison_value => File that we are comparing
            #is missing some data relative to reference file
            if combined_key not in comparison_value:
                diffs.get(MISS_MACRO).append(f"{path}{'.' if path else ''}{combined_key}")

            # if ref_key not in comparison_value:
            #     # print(f"ref key: {ref_key}, comp_value: {comparison_value}")
            #     # print(f"HERE: {path}")
            #     diffs.append(path)
            #     return
            # else:
            if combined_key in reference_value and combined_key in comparison_value:
                # print("\nIN\n")
                new_path = f"{path}{'.' if path != "" else ""}{combined_key}"
                compare_json_files(ref_value, comp_value, new_path, diffs)
                # path = path.replace(ref_key, "")
    
    #neither value is dict => they should be compared
    elif not isinstance(reference_value, dict) and not isinstance(comparison_value, dict):
        if isinstance(reference_value, list) and isinstance(comparison_value, list):
            for i in range(len(reference_value)):
                # print(f"\n{reference_value=}\n")
                new_path = f"{path}{'.' if path != "" else ""}[{i + 1}]"
                compare_json_files(reference_value[i], comparison_value[i], new_path, diffs)
        else:
            if reference_value != comparison_value:
                diffs.get(DIFF_MACRO).append({path: {"original": reference_value, "new": comparison_value}})
                return
            else:
                return
    #either reference_value or comparison value is dict, while the other is not
    else:
        diffs.append(path)
        return 

def main():
    # reference_value = {'a': 2, 'b': { 'b1': 2.1 }, 'c' : { 'c1' : { 'c2' : 2.11 } }, 'l' : [{'a': 1}, {'b': 2}] }
    # comparison_value = {'a': 4, 'c' : { 'c2' : { 'c2' : 2.711 } }, 'b': { 'b1': 2.2, 'b2': 2.3 }, 'l' : [{'a': 1}, {'b': 3}] }
    print("=" * 100)
    reference_value = load_json_file(INPUT_DIR, REF_FILE)
    comparison_value = load_json_file(INPUT_DIR, COMP_FILE)
    diffs = {"total_runs": 0, "total_diffs": 0, ADD_MACRO: [], MISS_MACRO: [], DIFF_MACRO: []}
    path = ""
    compare_json_files(reference_value, comparison_value, path, diffs)
    diff_content = load_json_file(DIFFERENCE_DIR, DIFFERENCE_FILE)
    if not any((diffs.get(ADD_MACRO), diffs.get(MISS_MACRO), diffs.get(DIFF_MACRO))):
        print("NO differences")
        diffs['total_diffs'] = diff_content.get('total_diffs')
    else:
        print("Files contain some differences")
        diffs['total_diffs'] = diff_content.get('total_diffs') + 1
    diffs['total_runs'] = diff_content.get('total_runs') + 1
    write_to_json_file(diffs, DIFFERENCE_DIR, DIFFERENCE_FILE)
    
    return

if __name__ == '__main__':
    main()