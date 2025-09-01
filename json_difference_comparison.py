

INPUT_DIR = ""
INPUT_FILE = ""
DIFFERENCE_DIR = ""
DIFFERENCE_FILE = ""

def step_into(value):
    """
    If value is dictionary, """
    if isinstance(value, dict):
        for key, value in value.items():
            step_into(value)

def compare_json_files(reference_value : dict|str|float|list, 
                       comparison_value : dict|str|float|list,
                       path : str, diffs : list[str]) -> None:
    #both values are dicts => go deeper in the structure
    if isinstance(reference_value, dict) and isinstance(comparison_value, dict):
        for ref_key, ref_value in reference_value.items():
            if ref_key not in comparison_value:
                print("append to diffs 1")
                diffs.append(path)
                return
            else:
                path += f"{"." if path != "" else ""}{ref_key}"
                compare_json_files(ref_value, comparison_value.get(ref_key), path, diffs)
                path = path.replace(ref_key, "")
    
    #neither value is dict => they should be compared
    elif not isinstance(reference_value, dict) and not isinstance(comparison_value, dict):
        if reference_value != comparison_value:
            diffs.append(path)
            print("append 2")
            return
        else:
            return
    #either reference_value or comparison value is dict, while the other is not
    else:
        diffs.append(path)
        print("append 3")
        return 

def main():
    reference_value = {'a': 2, 'b': { 'b1': 2.1 }, 'c' : { 'c1' : { 'c2' : 2.11 } } }
    comparison_value = {'a': 2, 'b': { 'b1': 2.2 }, 'c' : { 'c2' : { 'c2' : 2.711 } } }
    diffs = []
    path = ""
    compare_json_files(reference_value, comparison_value, path, diffs)
    if not diffs:
        print("NO differences")
    else:
        print("Files contain some differences")
    print(f"{diffs=}")
    return

if __name__ == '__main__':
    main()