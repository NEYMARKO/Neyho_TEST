

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
        all_keys = set(reference_value.keys()) |set(comparison_value.keys())
        for ref_key in all_keys:
            ref_value = reference_value.get(ref_key)
            comp_value = comparison_value.get(ref_key)

            if not ref_value:
                diffs.append({"ADDED" : f"{path}{'->' if path else ''}{ref_key}"})
            if not comp_value:
                diffs.append({"MISSING" : f"{path}{'->' if path else ''}{ref_key}"})

            # if ref_key not in comparison_value:
            #     # print(f"ref key: {ref_key}, comp_value: {comparison_value}")
            #     # print(f"HERE: {path}")
            #     diffs.append(path)
            #     return
            # else:
            if ref_value and comp_value:
                new_path = f"{path}{"->" if path != "" else ""}{ref_key}"
                compare_json_files(ref_value, comparison_value.get(ref_key), new_path, diffs)
                # path = path.replace(ref_key, "")
    
    #neither value is dict => they should be compared
    elif not isinstance(reference_value, dict) and not isinstance(comparison_value, dict):
        if reference_value != comparison_value:
            diffs.append(path)
            return
        else:
            return
    #either reference_value or comparison value is dict, while the other is not
    else:
        diffs.append(path)
        return 

def main():
    reference_value = {'a': 2, 'b': { 'b1': 2.1 }, 'c' : { 'c1' : { 'c2' : 2.11 } } }
    comparison_value = {'a': 2, 'b': { 'b1': 2.2, 'b2': 2.3 }, 'c' : { 'c2' : { 'c2' : 2.711 } } }
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